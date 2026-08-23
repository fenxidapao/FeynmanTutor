"""FeynmanTutor 配置：环境变量统一入口。

. 变量来源：项目根目录 .env（已从 deep-research 复制 DEEPSEEK_* 三行）
. 模型策略（PLAN 4.5）：默认 deepseek-v4-flash（稳定版），Ollama 7B 仅降级
"""

import os
from pathlib import Path

# 项目根目录（config.py 所在目录）
ROOT = Path(__file__).resolve().parent

# ---------- LLM（DeepSeek API 主力） ----------
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

# ---------- Ollama 降级（仅断网/欠费兜底，费曼追问环节强制禁用） ----------
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

# ---------- CourseRAG（知识底座，HTTP 调用） ----------
RAG_BASE_URL = os.environ.get("RAG_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
RAG_RETRIEVE_TOP_N = int(os.environ.get("RAG_RETRIEVE_TOP_N", "8"))  # 全量取回，交给 LLM 相关性过滤

# ---------- 状态库 ----------
DB_PATH = os.environ.get("DB_PATH", str(ROOT / "state.db"))

# ---------- 沙箱 ----------
SANDBOX_TIMEOUT = int(os.environ.get("SANDBOX_TIMEOUT", "5"))      # 秒
SANDBOX_MAX_OUTPUT = int(os.environ.get("SANDBOX_MAX_OUTPUT", "65536"))  # 字节

# ---------- C 阶段实验（PLAN 18.3） ----------
# EXPERIMENT_AUTH=1 时：业务端点强制 session 鉴权 + mode 按 group_name 强制 + 配额生效
# 默认 0（兼容本机演示/既有测试）；C 阶段部署时置 1
EXPERIMENT_AUTH = os.environ.get("EXPERIMENT_AUTH", "0") == "1"
# 每日每用户 LLM 调用上限（一次完整闭环约 12-15 次，重学多遍 50 次合理）
DAILY_LLM_LIMIT_PER_USER = int(os.environ.get("DAILY_LLM_LIMIT_PER_USER", "50"))
# 全站每日 LLM 调用总量上限（全局熔断，防单用户/异常刷爆 key）
GLOBAL_DAILY_LLM_LIMIT = int(os.environ.get("GLOBAL_DAILY_LLM_LIMIT", "300"))


def load_dotenv(path: str | None = None) -> None:
    """极简 .env 加载：只读 KEY=VALUE 行，不覆盖已存在的环境变量。"""
    p = Path(path) if path else ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


# 模块加载时自动读 .env（保证 import config 即可用）
load_dotenv()
