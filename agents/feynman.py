"""费曼导师 Agent（PLAN 14.6，核心）：角色反转教学。

核心流程（先答后讲是红线，不可配置）：
  explain_kp()     讲解知识点（RAG 检索 → LLM 过滤 → notes 兜底；不含练习答案）
  feynman_round()  角色反转：用户当老师讲概念 → Agent 当学生追问 → 3 轮后总结盲点
  hint_only()      答错只给方向提示，不给答案

交互解耦：feynman_round 接受 ask_user 回调（返回用户输入的字符串），
CLI 层传入 input() 包装，测试层可传假输入。
"""

import json
from datetime import datetime
from typing import Callable

import db
import model
import rag

FEYNMAN_SYSTEM = """你是费曼学习法教练。核心规则：
1. 用户当老师讲解概念，你当学生提问——通过追问暴露用户的认知盲点；
2. 用户讲得对就肯定并深入问细节；讲错/含糊就指出并引导；
3. 每轮只问 1-2 个尖锐问题，问题要具体（举例、边界、易错点）；
4. 禁止直接给出完整答案，禁止替用户讲解。
"""

FOLLOWUP_PROMPT = """你是费曼学习法教练，正在听学生（老师）讲解知识点：{kp_title}。

已有对话：
{transcript}

现在轮到你提问/回应：
1. 若学生讲得对 → 肯定，然后问一个更深入的细节问题（边界情况/易错点/举例）；
2. 若学生讲错或含糊 → 直接指出哪里有问题，引导 TA 纠正；
3. 只输出你的话（1-2 句话），不要输出别的。
"""

GAP_PROMPT = """以下是学生（老师）讲解知识点 {kp_title} 的完整对话。请总结学生的认知盲点。

对话记录：
{transcript}

输出严格 JSON：{{"gaps": ["盲点1", "盲点2", ...]}}
最多 3 个，具体到概念细节。只总结真实出现的盲点，不要编造。"""

HINT_PROMPT = """学生做编程题答错了。题目：{prompt}
学生的错误答案：{answer}
判题反馈：{feedback}

你的任务：只给"方向性提示"帮助 TA 自己找到错误。
规则：
1. 提示必须具体到知识点层面（如"想想切片索引从几开始"），不能直接给出正确答案代码；
2. 不超过 2 句话；
3. 不要说"你错了"这类空话，直接指出该检查哪里。"""


def _load_graph(course: str) -> dict:
    import learning_pack
    return learning_pack.load_graph(course)


def _update_kp_after_explain(user_id: str, kp: dict, db_path: str | None) -> None:
    """讲解后更新 explain_count 与 last_explained。"""
    cur = db.get_kp(user_id, kp["kp_id"], db_path) or {}
    db.upsert_kp(user_id, {
        "kp_id": kp["kp_id"],
        "title": kp.get("title", kp["kp_id"]),
        "chapter": kp.get("chapter", ""),
        "prerequisites": json.dumps(kp.get("prerequisites", []), ensure_ascii=False),
        "explain_count": (cur.get("explain_count") or 0) + 1,
        "last_explained": datetime.now().isoformat(timespec="seconds"),
    }, db_path)


def explain_kp(user_id: str, kp_id: str, course: str = "python",
               db_path: str | None = None) -> str:
    """讲解知识点：RAG 检索（LLM 过滤）→ notes 兜底。返回讲解文本。"""
    graph = _load_graph(course)
    kp = graph["_by_id"][kp_id]

    ctx = rag.retrieve_tutor_context(kp_id, course)
    if not ctx["context"]:
        return "（抱歉，暂时没有该知识点的讲解材料，请换个知识点。）"

    if ctx["source"] == "rag":
        print(f"[i] 讲解材料来源: CourseRAG（引用: {', '.join(ctx['used_sources']) or '无'}）")
    else:
        print(f"[i] 讲解材料来源: 学习包 notes 兜底")

    _update_kp_after_explain(user_id, kp, db_path)
    return ctx["context"]


def generate_followup(kp: dict, transcript: list[dict]) -> str:
    """基于已有对话生成教练的下一轮提问。"""
    lines = "\n".join(f"{'学生' if t['role'] == 'user' else '教练'}: {t['content']}"
                      for t in transcript)
    raw = model.chat(
        [{"role": "system", "content": FEYNMAN_SYSTEM},
         {"role": "user", "content": FOLLOWUP_PROMPT.format(
             kp_title=kp.get("title", kp["kp_id"]), transcript=lines or "（刚开始）")}],
        temperature=0.4, max_tokens=500, caller="feynman_followup",
    )
    return raw.strip() or "你能再举个具体的例子说明吗？"


def summarize_gaps(kp: dict, transcript: list[dict]) -> list[str]:
    """3 轮后总结盲点。"""
    if not transcript:
        return []
    lines = "\n".join(f"{'学生' if t['role'] == 'user' else '教练'}: {t['content']}"
                      for t in transcript)
    try:
        raw = model.chat(
            [{"role": "system", "content": "你只输出合法 JSON。"},
             {"role": "user", "content": GAP_PROMPT.format(
                 kp_title=kp.get("title", kp["kp_id"]), transcript=lines)}],
            temperature=0.2, max_tokens=800, caller="feynman_gaps",
        )
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start:end + 1])
        return [str(x) for x in data.get("gaps", [])][:3]
    except (json.JSONDecodeError, ValueError, model.ModelError):
        return ["（盲点总结失败，请人工查看对话记录）"]


def feynman_round(user_id: str, kp_id: str, course: str = "python",
                  max_rounds: int = 3,
                  ask_user: Callable[[str], str] = input,
                  db_path: str | None = None) -> dict:
    """完整费曼回合：用户讲 → 教练追问，最多 max_rounds 轮 → 总结盲点。

    强制走 API（model.chat 默认不降级）：费曼追问环节 7B 会盲目附和讲错内容，
    API 挂时明确提示"离线模式不支持追问"，而不是降级。

    返回 {'transcript': [...], 'gaps': [...]}。
    """
    graph = _load_graph(course)
    kp = graph["_by_id"][kp_id]
    transcript: list[dict] = []

    try:
        for _ in range(max_rounds):
            # 用户当老师讲（第一轮先讲，之后回答追问）
            turn_prompt = "轮到你了：请用你自己的话讲解这个知识点" \
                          "（可以举例子，讲完回车）。" if not transcript \
                          else "请回答教练的追问："
            user_talk = ask_user(turn_prompt).strip()
            if not user_talk:
                print("（跳过本轮）")
                break
            transcript.append({"role": "user", "content": user_talk})

            # 教练追问（最后总结前不再追问）
            if len(transcript) // 2 < max_rounds - 1:
                coach = generate_followup(kp, transcript)
                print(f"\n[教练] {coach}")
                transcript.append({"role": "assistant", "content": coach})
    except model.ModelError as e:
        print(f"\n[!] 费曼追问不可用（API 故障）：{e}")
        print("    离线模式不支持追问（本地 7B 会盲目附和讲错内容），本次跳过追问。")
        return {"transcript": transcript, "gaps": ["API 不可用，未完成追问"]}

    # 总结盲点
    gaps = summarize_gaps(kp, transcript)
    if transcript:
        _update_kp_after_explain(user_id, kp, db_path)
    return {"transcript": transcript, "gaps": gaps}


def hint_only(exercise: dict, result: dict) -> str:
    """答错时只给方向提示，不给答案。"""
    prompt = exercise.get("prompt", "")
    answer = str(result.get("user_answer", ""))[:200]
    feedback = result.get("feedback", "")
    try:
        raw = model.chat(
            [{"role": "system", "content": "你是耐心的编程助教，只给方向提示不给答案。"},
             {"role": "user", "content": HINT_PROMPT.format(
                 prompt=prompt, answer=answer, feedback=feedback)}],
            temperature=0.3, max_tokens=300, caller="hint",
        )
        return raw.strip() or "再想想，检查一下你的思路。"
    except model.ModelError:
        return "（提示服务暂不可用）再读一遍题目，检查边界情况。"
