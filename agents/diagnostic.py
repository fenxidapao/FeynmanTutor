"""诊断 Agent（PLAN 14.5）：读用户答题记录 → LLM 生成学习画像。

画像内容：weak_points（薄弱知识点）/ learning_style（偏好）/ avg_correct（平均正确率）。
LLM 输出 JSON，解析失败兜底为纯统计（按正确率排序取最低）。
"""

import json

import db
import model

DIAGNOSE_PROMPT = """你是学习诊断专家。根据学生的学习数据生成学习画像。

学生答题记录（JSON 列表，每项包含 kp_id、ex_id、correct(0/1)、feedback 等字段）：
{logs}

历史画像（可能为空）：
{old_profile}

输出严格 JSON（不要多余文字）：
{{
  "weak_points": [
    {{"kp_id": "知识点id", "reason": "为什么判定薄弱（一句话，引用数据）", "evidence": ["做错的题目ex_id", ...]}}
  ],
  "learning_style": "简答|代码|类比",
  "avg_correct": 0.6
}}
weak_points 最多 5 个，按薄弱程度排序；evidence 只列真实做错的题目 id，不要编造。
只依据给定数据，不要编造。"""


def _stats_fallback(logs: list[dict]) -> dict:
    """纯统计兜底：按正确率排序取最差的作为薄弱点，带证据链。"""
    by_kp: dict[str, list[dict]] = {}
    for log in logs:
        by_kp.setdefault(log.get("kp_id", "?"), []).append(log)
    stats = []
    for kp, ls in by_kp.items():
        rate = sum(1 for l in ls if l.get("correct")) / len(ls)
        if rate < 0.8:
            evidence = [l.get("ex_id") for l in ls if not l.get("correct")]
            stats.append({"kp_id": kp, "reason": f"正确率 {rate:.0%}，错 {len(evidence)} 题",
                          "evidence": evidence[:5], "rate": rate, "n": len(ls)})
    stats.sort(key=lambda x: (x["rate"], -x["n"]))  # 正确率低优先，其次做过多的
    weak = [{"kp_id": s["kp_id"], "reason": s["reason"], "evidence": s["evidence"]}
            for s in stats[:5]]
    corrects = [1 if l.get("correct") else 0 for l in logs]
    avg = sum(corrects) / len(corrects) if corrects else 0.0
    return {"weak_points": weak, "learning_style": "简答",
            "avg_correct": round(avg, 2), "fallback": True}


def diagnose(user_id: str, db_path: str | None = None) -> dict:
    """读 exercise_logs/assessments → LLM 画像；失败兜底纯统计。

    返回 {"weak_points": [{"kp_id","reason","evidence"}, ...], "learning_style": "...",
          "avg_correct": 0.6, "fallback": bool}
    """
    logs = db.get_exercise_logs(user_id, db_path=db_path)
    old = db.get_profile(user_id, db_path=db_path)

    if not logs:
        return {"weak_points": [], "learning_style": "", "avg_correct": 0.0, "fallback": False}

    # 结构化日志摘要（去冗余字段，含 ex_id 供证据链引用）
    summary = json.dumps(
        [{"kp_id": l.get("kp_id"), "ex_id": l.get("ex_id"), "correct": l.get("correct"),
          "feedback": (l.get("feedback") or "")[:80]} for l in logs[-50:]],
        ensure_ascii=False,
    )
    old_summary = json.dumps({
        "weak_points": db.parse_weak_details(old),
        "learning_style": old["learning_style"] if old else "",
    }, ensure_ascii=False) if old else ""

    try:
        raw = model.chat(
            [{"role": "system", "content": "你只输出合法 JSON。"},
             {"role": "user", "content": DIAGNOSE_PROMPT.format(logs=summary, old_profile=old_summary)}],
            temperature=0.2, max_tokens=1200,
        )
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start:end + 1])
        weak = []
        for x in data.get("weak_points", [])[:5]:
            if isinstance(x, str):
                weak.append({"kp_id": x, "reason": "", "evidence": []})
            elif isinstance(x, dict) and x.get("kp_id"):
                weak.append({"kp_id": str(x["kp_id"]),
                             "reason": str(x.get("reason", "")),
                             "evidence": [str(e) for e in (x.get("evidence") or [])][:5]})
        profile = {
            "weak_points": weak,
            "learning_style": str(data.get("learning_style", "简答")),
            "avg_correct": round(float(data.get("avg_correct", 0.0)), 2),
            "fallback": False,
        }
    except (json.JSONDecodeError, ValueError, model.ModelError) as e:
        print(f"[i] LLM 诊断失败，使用统计兜底: {type(e).__name__}")
        profile = _stats_fallback(logs)

    db.save_profile(user_id, profile, db_path)
    return profile
