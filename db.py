"""状态库封装：SQLite，全部表带 user_id（多用户，PLAN 6.2）。

0 号用户 = 本人（'u0'）；后续同学/网上用户各自一个 user_id，数据结构天然支持，
从 P0 第一行代码就是多用户，不做返工。
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  name TEXT,
  created_at TEXT,
  group_name TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_points (
  user_id TEXT NOT NULL,
  kp_id TEXT NOT NULL,
  title TEXT NOT NULL,
  chapter TEXT NOT NULL,
  prerequisites TEXT DEFAULT '[]',
  mastery REAL DEFAULT 0.0,
  seen_count INTEGER DEFAULT 0,
  correct_count INTEGER DEFAULT 0,
  explain_count INTEGER DEFAULT 0,
  last_explained TEXT,
  last_practiced TEXT,
  next_review TEXT,
  status TEXT DEFAULT 'new',
  review_interval INTEGER DEFAULT 0,
  PRIMARY KEY (user_id, kp_id)
);

CREATE TABLE IF NOT EXISTS exercise_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  kp_id TEXT,
  ex_id TEXT,
  attempt INTEGER,
  correct INTEGER,
  user_answer TEXT,
  feedback TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS assessments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  chapter TEXT,
  kind TEXT,
  mode TEXT,
  score REAL,
  total INTEGER,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS profile (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  weak_points TEXT,
  learning_style TEXT,
  avg_correct REAL,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS llm_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  caller TEXT,                -- 调用环节：diagnostic/feynman/hint/planner/recommender/rag/assessor
  model TEXT,                 -- 实际模型名
  prompt_tokens INTEGER,      -- 输入 token
  completion_tokens INTEGER,  -- 输出 token
  total_tokens INTEGER,       -- 总 token
  latency_ms INTEGER,         -- 单次调用耗时（毫秒）
  attempts INTEGER,           -- 外层重试次数
  expanded INTEGER,           -- 是否发生推理预算扩容
  source TEXT,                -- api / ollama
  created_at TEXT
);
"""


def _conn(db_path: str | None = None) -> sqlite3.Connection:
    """新建连接。SQLite 默认已开启，加 row_factory 方便 dict 读取。"""
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    with _conn(db_path) as c:
        c.executescript(SCHEMA)
        # 迁移：老库缺列时补（IF NOT EXISTS 不会为已有表加列）
        ucols = {r[1] for r in c.execute("PRAGMA table_info(users)")}
        if "group_name" not in ucols:
            c.execute("ALTER TABLE users ADD COLUMN group_name TEXT DEFAULT NULL")
        kcols = {r[1] for r in c.execute("PRAGMA table_info(knowledge_points)")}
        if "review_interval" not in kcols:
            c.execute("ALTER TABLE knowledge_points ADD COLUMN review_interval INTEGER DEFAULT 0")


def get_user(user_id: str, name: str | None = None, db_path: str | None = None) -> dict:
    """用户存在则返回，不存在则创建。返回 {user_id, name, created_at, group_name}。

    传了 name 且用户已存在时更新 name（注册场景补全用户名）。
    """
    with _conn(db_path) as c:
        row = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            now = datetime.now().isoformat(timespec="seconds")
            c.execute(
                "INSERT INTO users (user_id, name, created_at) VALUES (?, ?, ?)",
                (user_id, name or user_id, now),
            )
            row = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        elif name and name != row["name"]:
            c.execute("UPDATE users SET name=? WHERE user_id=?", (name, user_id))
            row = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row)


def assign_group(user_id: str, group_name: str, db_path: str | None = None) -> dict:
    """把用户分到实验组（feynman / lecture）。返回更新后的用户。"""
    get_user(user_id, db_path=db_path)  # 确保存在
    with _conn(db_path) as c:
        c.execute("UPDATE users SET group_name=? WHERE user_id=?",
                  (group_name, user_id))
        row = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row)


def list_users(db_path: str | None = None) -> list[dict]:
    """全部用户（含分组），供 P1+ 组间对照实验统计。"""
    with _conn(db_path) as c:
        rows = c.execute("SELECT * FROM users ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]


def upsert_kp(user_id: str, kp: dict, db_path: str | None = None) -> None:
    """更新知识点状态（不存在则插入）。kp 至少含 kp_id/title/chapter。"""
    fields = (
        "kp_id", "title", "chapter", "prerequisites", "mastery", "seen_count",
        "correct_count", "explain_count", "last_explained", "last_practiced",
        "next_review", "status",
    )
    with _conn(db_path) as c:
        row = c.execute(
            "SELECT * FROM knowledge_points WHERE user_id=? AND kp_id=?",
            (user_id, kp["kp_id"]),
        ).fetchone()
        if row is None:
            defaults = {
                "prerequisites": "[]", "mastery": 0.0, "seen_count": 0,
                "correct_count": 0, "explain_count": 0, "last_explained": None,
                "last_practiced": None, "next_review": None, "status": "new",
            }
            merged = {**defaults, **kp}
            cols = ("user_id",) + fields
            c.execute(
                f"INSERT INTO knowledge_points ({', '.join(cols)}) "
                f"VALUES ({', '.join('?' for _ in cols)})",
                (user_id, *(merged.get(f) for f in fields)),
            )
        else:
            updates = {f: kp[f] for f in fields if f in kp}
            if updates:
                sets = ", ".join(f"{k}=?" for k in updates)
                c.execute(
                    f"UPDATE knowledge_points SET {sets} WHERE user_id=? AND kp_id=?",
                    (*updates.values(), user_id, kp["kp_id"]),
                )


def log_exercise(user_id: str, ex_id: str, kp_id: str, correct: bool,
                 user_answer: str, feedback: str, attempt: int = 1,
                 db_path: str | None = None) -> None:
    """记答题日志，并同步更新 knowledge_points 掌握度（P3 修复：判题链路断点）。

    mastery = correct_count / seen_count（最近 50 条内该 kp 的正确率）；
    status: 无记录 new / mastery>=0.8 mastered / >0 learning / 全错 reviewing。
    """
    with _conn(db_path) as c:
        c.execute(
            "INSERT INTO exercise_logs (user_id, kp_id, ex_id, attempt, correct, "
            "user_answer, feedback, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, kp_id, ex_id, attempt, int(correct), user_answer, feedback,
             datetime.now().isoformat(timespec="seconds")),
        )
        _update_kp_mastery(c, user_id, kp_id, correct)


def _update_kp_mastery(c: sqlite3.Connection, user_id: str, kp_id: str,
                       correct: bool) -> None:
    """内部：更新 knowledge_points 的掌握度（log_exercise 后调用）。

    只统计最近 50 条答题（滑动窗口），防止远古数据拖累当前掌握度。
    status: 无记录 new / 最近 3 条全错 blocked / mastery>=0.8 mastered /
            >0 learning / 全错 reviewing（掌握门槛：卡住不放行）。
    """
    if not kp_id:
        return
    row = c.execute(
        "SELECT COUNT(*) n, SUM(correct) ok FROM ("
        "  SELECT correct FROM exercise_logs WHERE user_id=? AND kp_id=? "
        "  ORDER BY id DESC LIMIT 50)",
        (user_id, kp_id),
    ).fetchone()
    seen = row["n"] or 0
    ok = row["ok"] or 0
    mastery = round(ok / seen, 2) if seen else 0.0
    # 掌握门槛：最近 3 条答题全错 → blocked（卡住不放行，依赖它的 kp 暂缓）
    recent = [r["correct"] for r in c.execute(
        "SELECT correct FROM exercise_logs WHERE user_id=? AND kp_id=? "
        "ORDER BY id DESC LIMIT 3", (user_id, kp_id))]
    blocked = len(recent) >= 3 and all(x == 0 for x in recent)
    if blocked:
        status = "blocked"
    elif mastery >= 0.8:
        status = "mastered"
    elif mastery > 0:
        status = "learning"
    else:
        status = "reviewing"
    now = datetime.now().isoformat(timespec="seconds")
    c.execute(
        "UPDATE knowledge_points SET mastery=?, seen_count=?, correct_count=?, "
        "status=?, last_practiced=? WHERE user_id=? AND kp_id=?",
        (mastery, seen, ok, status, now, user_id, kp_id),
    )
    # 该 kp 还没初始化过（无 title 等元数据）→ 由 upsert_kp 补全；这里仅更新计数
    if c.execute("SELECT 1 FROM knowledge_points WHERE user_id=? AND kp_id=?",
                 (user_id, kp_id)).fetchone() is None:
        c.execute(
            "INSERT OR IGNORE INTO knowledge_points (user_id, kp_id, title, chapter, "
            "mastery, seen_count, correct_count, status, last_practiced) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, kp_id, kp_id, "", mastery, seen, ok, status, now),
        )


def record_assessment(user_id: str, chapter: str, kind: str, mode: str,
                      score: float, total: int, db_path: str | None = None) -> None:
    with _conn(db_path) as c:
        c.execute(
            "INSERT INTO assessments (user_id, chapter, kind, mode, score, total, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (user_id, chapter, kind, mode, score, total,
             datetime.now().isoformat(timespec="seconds")),
        )


def get_kp(user_id: str, kp_id: str, db_path: str | None = None) -> dict | None:
    with _conn(db_path) as c:
        row = c.execute(
            "SELECT * FROM knowledge_points WHERE user_id=? AND kp_id=?",
            (user_id, kp_id),
        ).fetchone()
        return dict(row) if row else None


def list_kps(user_id: str, db_path: str | None = None) -> list[dict]:
    with _conn(db_path) as c:
        rows = c.execute(
            "SELECT * FROM knowledge_points WHERE user_id=? ORDER BY chapter, kp_id",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_profile(user_id: str, db_path: str | None = None) -> dict | None:
    with _conn(db_path) as c:
        row = c.execute(
            "SELECT * FROM profile WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def parse_weak_ids(profile: dict | None) -> list[str]:
    """从 profile 提取薄弱点 kp_id 列表。

    兼容两种存储格式：
    - 旧格式：["kp_id", ...]（字符串列表）
    - 新格式：[{"kp_id": "...", "reason": "...", "evidence": ["ex_id", ...]}, ...]
    """
    if not profile:
        return []
    raw = profile.get("weak_points")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return []
    if not isinstance(raw, list):
        return []
    ids = []
    for item in raw:
        if isinstance(item, str):
            ids.append(item)
        elif isinstance(item, dict) and item.get("kp_id"):
            ids.append(item["kp_id"])
    return ids


def parse_weak_details(profile: dict | None) -> list[dict]:
    """从 profile 提取薄弱点完整结构（含 reason/evidence），兼容旧格式自动补 reason。"""
    if not profile:
        return []
    raw = profile.get("weak_points")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return []
    if not isinstance(raw, list):
        return []
    details = []
    for item in raw:
        if isinstance(item, str):
            details.append({"kp_id": item, "reason": "", "evidence": []})
        elif isinstance(item, dict) and item.get("kp_id"):
            details.append(item)
    return details


def save_profile(user_id: str, profile: dict, db_path: str | None = None) -> None:
    with _conn(db_path) as c:
        c.execute(
            "INSERT INTO profile (user_id, weak_points, learning_style, avg_correct, updated_at) "
            "VALUES (?,?,?,?,?)",
            (user_id, json.dumps(profile.get("weak_points", []), ensure_ascii=False),
             profile.get("learning_style", ""), profile.get("avg_correct", 0.0),
             datetime.now().isoformat(timespec="seconds")),
        )


def get_assessments(user_id: str, chapter: str | None = None,
                    db_path: str | None = None) -> list[dict]:
    with _conn(db_path) as c:
        if chapter:
            rows = c.execute(
                "SELECT * FROM assessments WHERE user_id=? AND chapter=? ORDER BY id",
                (user_id, chapter),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM assessments WHERE user_id=? ORDER BY id", (user_id,)
            ).fetchall()
        return [dict(r) for r in rows]


def get_exercise_logs(user_id: str, kp_id: str | None = None,
                      db_path: str | None = None) -> list[dict]:
    with _conn(db_path) as c:
        if kp_id:
            rows = c.execute(
                "SELECT * FROM exercise_logs WHERE user_id=? AND kp_id=? ORDER BY id",
                (user_id, kp_id),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM exercise_logs WHERE user_id=? ORDER BY id", (user_id,)
            ).fetchall()
        return [dict(r) for r in rows]


def review_due(user_id: str, db_path: str | None = None) -> list[dict]:
    """到期复习的知识点（next_review 非空且 <= 今天）。P2 复习闭环用，接口先备好。"""
    now = datetime.now().date().isoformat()
    with _conn(db_path) as c:
        rows = c.execute(
            "SELECT * FROM knowledge_points WHERE user_id=? AND next_review IS NOT NULL "
            "AND next_review <= ?",
            (user_id, now),
        ).fetchall()
        return [dict(r) for r in rows]


def schedule_next_review(user_id: str, kp_id: str, days: int,
                         db_path: str | None = None) -> None:
    """SM-2 简化版：间隔天数后复习。P0 先记字段，P2 做闭环。"""
    next_review = (datetime.now() + timedelta(days=days)).date().isoformat()
    upsert_kp(user_id, {"kp_id": kp_id, "next_review": next_review}, db_path)


def log_llm_call(caller: str, model: str, prompt_tokens: int,
                 completion_tokens: int, total_tokens: int, latency_ms: int,
                 attempts: int = 1, expanded: bool = False,
                 source: str = "api", db_path: str | None = None) -> None:
    """记录一次 LLM 调用（可观测性：token 用量 + 耗时，PLAN 8 多 Agent 效率评估）。"""
    with _conn(db_path) as c:
        c.execute(
            "INSERT INTO llm_logs (caller, model, prompt_tokens, completion_tokens, "
            "total_tokens, latency_ms, attempts, expanded, source, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (caller, model, prompt_tokens, completion_tokens, total_tokens,
             latency_ms, attempts, int(expanded), source,
             datetime.now().isoformat(timespec="seconds")),
        )


def llm_stats(db_path: str | None = None) -> dict:
    """LLM 调用统计（按环节聚合）：次数 / token / 耗时，供报告与面试数据。"""
    with _conn(db_path) as c:
        rows = c.execute(
            "SELECT caller, COUNT(*) calls, SUM(total_tokens) tokens, "
            "SUM(latency_ms) latency_ms, SUM(expanded) expanded "
            "FROM llm_logs GROUP BY caller ORDER BY tokens DESC",
        ).fetchall()
        total = c.execute(
            "SELECT COUNT(*) calls, COALESCE(SUM(total_tokens),0) tokens, "
            "COALESCE(SUM(latency_ms),0) latency_ms FROM llm_logs",
        ).fetchone()
    return {
        "by_caller": [dict(r) for r in rows],
        "total": {"calls": total["calls"], "tokens": total["tokens"],
                  "latency_ms": total["latency_ms"]},
    }
