"""知识检索封装：HTTP 调 CourseRAG + LLM 内容相关性过滤 + notes 兜底。

检索策略（2026-08-22 定稿，改动说明见 learning_packs/python/README.md）：
  CourseRAG /retrieve 不支持 sources 参数（api_schemas.py 仅 question/mode），
  故：检索 top-N 全量返回 → LLM 按"内容是否与知识点相关"过滤 → 空则 notes 兜底。
  零侵入 CourseRAG（三项目独立原则），不依赖 source 文件名。

对外接口：
  retrieve_tutor_context(kp) -> {"context": str, "source": "rag"|"notes", "used_docs": [...]}
"""

import json
import urllib.error
import urllib.request

import config
import learning_pack
import model

# 讲解与"相关性过滤"合并为一次 LLM 调用：让它只基于相关片段讲解，并声明引用了哪些
FILTER_PROMPT = """你是编程教学助手。下面是检索到的课程片段（可能包含无关内容）。
用户要学知识点：{kp_title}（{kp_id}）

规则：
1. 只使用与知识点直接相关的片段来组织讲解，忽略无关片段；
2. 输出格式（严格 JSON）：
   {{"used": [片段编号列表，如 [0,2]], "explanation": "基于相关片段的讲解（类比+要点+示例），300字以内"}}
3. 如果所有片段都不相关，输出 {{"used": [], "explanation": ""}}，不要硬编。

片段列表：
{docs}
"""


class RAGError(Exception):
    """CourseRAG 不可用。"""


def _retrieve_raw(question: str, top_n: int | None = None) -> list[dict]:
    """调 CourseRAG /retrieve，返回 docs 列表（带 source/content 字段）。"""
    top_n = top_n or config.RAG_RETRIEVE_TOP_N
    payload = json.dumps({"question": question, "mode": "fast", "top_k": top_n}).encode("utf-8")
    req = urllib.request.Request(
        config.RAG_BASE_URL + "/retrieve",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        raise RAGError(f"CourseRAG 不可用: {e}") from e
    return body.get("docs", [])


def _llm_filter(kp: dict, docs: list[dict]) -> tuple[list[int], str]:
    """LLM 按内容相关性过滤 + 组织讲解。返回 (used_indexes, explanation)。"""
    doc_text = "\n".join(
        f"[{i}] (来源:{d.get('source', '?')})\n{d.get('content', '')[:800]}"
        for i, d in enumerate(docs)
    )
    prompt = FILTER_PROMPT.format(
        kp_title=kp.get("title", kp["kp_id"]),
        kp_id=kp["kp_id"],
        docs=doc_text,
    )
    raw = model.chat(
        [{"role": "system", "content": "你只输出合法 JSON，不加任何解释。"},
         {"role": "user", "content": prompt}],
        temperature=0.2, max_tokens=1600, caller="rag_filter",
    )
    # 容错：提取 JSON 子串（模型可能带 ```json 围栏）
    try:
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start:end + 1])
        used = [int(x) for x in data.get("used", [])]
        explanation = data.get("explanation", "").strip()
        return used, explanation
    except (json.JSONDecodeError, ValueError):
        return [], ""


def retrieve_tutor_context(kp_id: str, course: str = "python") -> dict:
    """讲解材料：RAG 检索 → LLM 过滤 → notes 兜底。

    返回 {"context": 讲解材料文本, "source": "rag"|"notes", "used_sources": [...]}
    """
    graph = learning_pack.load_graph(course)
    kp = graph["_by_id"].get(kp_id)
    if kp is None:
        raise learning_pack.LearningPackError(f"未知知识点: {kp_id}")

    # 1) RAG 检索
    try:
        docs = _retrieve_raw(kp.get("title", kp_id))
    except RAGError as e:
        print(f"[i] {e} → 使用 notes 兜底")
        docs = []

    if docs:
        used, explanation = _llm_filter(kp, docs)
        if used:
            used_sources = sorted({docs[i].get("source", "?") for i in used})
            return {
                "context": explanation,
                "source": "rag",
                "used_sources": used_sources,
            }

    # 2) notes 兜底
    notes = learning_pack.notes_for(course, kp_id)
    if notes:
        return {"context": notes, "source": "notes", "used_sources": ["notes/"]}

    return {"context": "", "source": "none", "used_sources": []}
