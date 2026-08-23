"""FeynmanTutor Web 服务（P3）：FastAPI 后端。

设计原则：
1. 复用现有 db / agents / learning_pack / sandbox / grader，不重复实现；
2. 费曼追问改成无状态轮次 API：前端保存 transcript，每轮调 /api/feynman/turn
   拿教练追问，3 轮后调 /api/feynman/summarize 总结盲点（不阻塞、可重试）；
3. 判题仍走规则（grader），LLM 只做讲解/追问/诊断（防漂移，PLAN 10.3）；
4. 多用户：所有 API 带 user_id，前端可选用户。

启动：uvicorn web.app:app --reload --port 8001
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

import db  # noqa: E402
import grader  # noqa: E402
import learning_pack  # noqa: E402
import sandbox  # noqa: E402
from agents import assessor, diagnostic, feynman, planner, recommender  # noqa: E402

app = FastAPI(title="FeynmanTutor", description="基于费曼学习法的个性化学习 Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent / "static"


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


# ==================== 用户 ====================

@app.get("/api/users")
def api_users():
    return db.list_users()


@app.post("/api/users")
def api_register(user_id: str = Query(...), name: str = Query("")):
    return db.get_user(user_id, name=name or None)


@app.get("/api/users/{user_id}")
def api_user(user_id: str):
    return db.get_user(user_id)


# ==================== 学习包 ====================

@app.get("/api/learning-pack/{course}")
def api_learning_pack(course: str):
    graph = learning_pack.load_graph(course)
    return {
        "course": course,
        "title": graph["title"],
        "chapters": graph["chapters"],
        "knowledge_points": [
            {k: v for k, v in kp.items() if k != "notes_file"}
            for kp in graph["knowledge_points"]
        ],
    }


# ==================== 前测/后测 ====================

@app.get("/api/quiz/{course}/{kind}")
def api_quiz(course: str, kind: str, chapter: str | None = None,
             user_id: str = Query("u0")):
    """取一套题（不含答案）。kind: pretest/posttest。"""
    if kind == "pretest":
        qs = learning_pack.load_pretest(course)
    elif kind == "posttest":
        qs = learning_pack.load_posttest(course)
    else:
        raise HTTPException(400, "kind 必须是 pretest/posttest")
    if chapter:
        qs = [q for q in qs if q.get("chapter") == chapter]
    return _strip_answers(qs)


def _strip_answers(qs: list[dict]) -> list[dict]:
    """去掉答案字段（mcq 的 answer、output/code 的 check 细节），防作弊。"""
    out = []
    for q in qs:
        q2 = {k: v for k, v in q.items() if k not in ("check",)}
        if q["type"] == "mcq":
            q2["options"] = q["check"]["options"]
        out.append(q2)
    return out


@app.post("/api/quiz/{course}/{kind}/submit")
def api_quiz_submit(course: str, kind: str,
                    payload: dict):
    """提交一套题。payload: {user_id, chapter?, mode?, answers: {ex_id: answer}}"""
    user_id = payload["user_id"]
    answers = payload["answers"]
    chapter = payload.get("chapter")
    mode = payload.get("mode", "feynman")
    if kind == "pretest":
        qs = learning_pack.load_pretest(course)
    else:
        qs = learning_pack.load_posttest(course)
    if chapter:
        qs = [q for q in qs if q.get("chapter") == chapter]

    correct = 0
    details = []
    for q in qs:
        ans = answers.get(q["ex_id"], "")
        ok, msg = grader.grade(q, ans)
        if ok:
            correct += 1
        db.log_exercise(user_id, q["ex_id"], q.get("kp_id", ""), ok, ans, msg)
        details.append({"ex_id": q["ex_id"], "correct": ok, "feedback": msg})

    score = correct / len(qs) if qs else 0.0
    db.record_assessment(user_id, chapter or "all", kind, mode, score, len(qs))
    return {"score": score, "correct": correct, "total": len(qs), "details": details}


# ==================== 练习判题 ====================

@app.get("/api/exercises/{course}")
def api_exercises(course: str, kp_id: str | None = None):
    """取练习题（不含答案）。"""
    exs = learning_pack.load_exercises(course)
    if kp_id:
        exs = [e for e in exs if e.get("kp_id") == kp_id]
    out = []
    for e in exs[:10]:
        e2 = {k: v for k, v in e.items() if k != "check"}
        if e["type"] == "mcq":
            e2["options"] = e["check"]["options"]
        out.append(e2)
    return out


@app.post("/api/grade")
def api_grade(payload: dict):
    """判一道题。payload: {user_id, ex_id, answer}"""
    user_id = payload["user_id"]
    ex_id = payload["ex_id"]
    answer = payload.get("answer", "")
    ex = _find_exercise(ex_id)
    if ex is None:
        raise HTTPException(404, f"题目不存在: {ex_id}")
    ok, msg = grader.grade(ex, answer)
    db.log_exercise(user_id, ex_id, ex.get("kp_id", ""), ok, answer, msg)
    return {"correct": ok, "feedback": msg, "ex_id": ex_id,
            "explanation": ex.get("explanation", "")}


def _find_exercise(ex_id: str) -> dict | None:
    for ex in learning_pack.load_exercises():
        if ex["ex_id"] == ex_id:
            return ex
    for q in learning_pack.load_pretest() + learning_pack.load_posttest():
        if q["ex_id"] == ex_id:
            return q
    return None


# ==================== 讲解 / 费曼追问 ====================

@app.get("/api/explain/{course}/{kp_id}")
def api_explain(course: str, kp_id: str, user_id: str = Query("u0")):
    """讲解知识点（RAG 检索 → LLM 过滤 → notes 兜底）。"""
    try:
        text = feynman.explain_kp(user_id, kp_id, course)
    except KeyError:
        raise HTTPException(404, f"未知知识点: {kp_id}")
    return {"kp_id": kp_id, "explanation": text}


@app.post("/api/feynman/turn")
def api_feynman_turn(payload: dict):
    """费曼追问一轮。payload: {course, kp_id, transcript: [{role, content}...]}"""
    course = payload["course"]
    kp_id = payload["kp_id"]
    transcript = payload.get("transcript", [])
    graph = learning_pack.load_graph(course)
    kp = graph["_by_id"].get(kp_id)
    if kp is None:
        raise HTTPException(404, f"未知知识点: {kp_id}")
    reply = feynman.generate_followup(kp, transcript)
    return {"coach": reply, "transcript": transcript}


@app.post("/api/feynman/summarize")
def api_feynman_summarize(payload: dict):
    """费曼结束，总结盲点。payload: {course, kp_id, transcript, user_id}"""
    course = payload["course"]
    kp_id = payload["kp_id"]
    transcript = payload.get("transcript", [])
    user_id = payload.get("user_id", "u0")
    graph = learning_pack.load_graph(course)
    kp = graph["_by_id"].get(kp_id)
    if kp is None:
        raise HTTPException(404, f"未知知识点: {kp_id}")
    gaps = feynman.summarize_gaps(kp, transcript)
    # 记录讲解次数（费曼环节算讲解一次）
    if transcript:
        feynman._update_kp_after_explain(user_id, kp, None)
    return {"gaps": gaps}


# ==================== 诊断 / 路径 / 推荐 ====================

@app.post("/api/diagnose/{user_id}")
def api_diagnose(user_id: str):
    profile = diagnostic.diagnose(user_id)
    return profile


@app.get("/api/path/{course}/{user_id}")
def api_path(course: str, user_id: str):
    plan = planner.plan_path(user_id, course)
    return plan


@app.get("/api/recommend/{course}/{user_id}")
def api_recommend(course: str, user_id: str, top_n: int = 5):
    return recommender.recommend(user_id, course, top_n=top_n)


# ==================== 报告 / 画像 ====================

@app.get("/api/report/{course}/{user_id}")
def api_report(course: str, user_id: str):
    r = assessor.report(user_id, None)
    return r


@app.get("/api/heatmap/{user_id}")
def api_heatmap(user_id: str):
    """热力图数据：12 知识点掌握度（0~1）+ 状态。"""
    graph = learning_pack.load_graph()
    kps = db.list_kps(user_id)
    by_id = {k["kp_id"]: k for k in kps}
    cells = []
    for kp in graph["knowledge_points"]:
        st = by_id.get(kp["kp_id"], {})
        mastery = st.get("mastery", 0) or 0
        cells.append({
            "kp_id": kp["kp_id"],
            "title": kp["title"],
            "chapter": kp["chapter"],
            "mastery": round(mastery, 2),
            "status": st.get("status", "new"),
            "seen": st.get("seen_count", 0),
            "correct": st.get("correct_count", 0),
            "explain": st.get("explain_count", 0),
        })
    return {"cells": cells}


# 静态资源（前端）
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
