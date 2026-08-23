"""LLM 封装：DeepSeek API 调用（抄 deep-research model.py 思路，减薄为纯 HTTP）。

. 思路照抄：重试 3 次 + 空输出兜底 + 402 余额预警
. 实现减薄：标准库 urllib 直连 OpenAI 兼容 /chat/completions，零第三方依赖
. 费曼追问环节必须走 API（7B 会盲目附和讲错内容），见 feynman.py 调用约束

用法：
    from model import chat, chat_with_fallback
    text = chat([{"role": "user", "content": "你好"}])
"""

import json
import time
import urllib.error
import urllib.request

import config

MAX_RETRIES = 3
TIMEOUT = 60  # 单次请求超时（秒）
MAX_BUDGET = 8000  # 推理预算扩容上限（max_tokens 不会超过它）


class ModelError(Exception):
    """LLM 调用失败（网络/401/429/402/空输出等）。调用方决定是否降级。"""


class ReasoningBudgetError(ModelError):
    """推理模型把 max_tokens 预算用在了思维链（reasoning_content）上，content 为空。

    deepseek-v4-flash 是推理模型：max_tokens 是"推理+回答"的总预算。
    遇到此类错误应自动扩容重试（见 chat 内 MAX_BUDGET_SCALE）。
    """

    def __init__(self, message: str, max_tokens: int):
        super().__init__(message)
        self.max_tokens = max_tokens


def _post_chat(messages: list[dict], temperature: float, max_tokens: int,
               base_url: str, api_key: str, model: str) -> str:
    """调用一次 /chat/completions，返回纯文本内容。异常由上层处理。"""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    choice = body["choices"][0]["message"]
    content = choice.get("content", "")
    if isinstance(content, list):  # 某些模型的 content 是分段数组
        content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
    text = (content or "").strip()
    if not text:
        # deepseek-v4-flash 是推理模型：先输出 reasoning_content 再输出 content。
        # 若 max_tokens 太小，推理阶段就把预算用光，content 为空。
        reasoning = choice.get("reasoning_content")
        if reasoning:
            raise ReasoningBudgetError(
                f"模型只输出了推理内容（max_tokens={max_tokens} 可能太小，"
                f"推理阶段已用尽预算），未产出正式回答",
                max_tokens=max_tokens)
    return text


def _warn_balance(http_code: int, body_text: str) -> None:
    """402 = 余额不足，明确预警（deep-research 已验证的坑）。"""
    if http_code == 402:
        print("[!] 警告：DeepSeek API 返回 402，余额可能不足，请充值后重试。")
    elif http_code in (401, 403):
        print(f"[!] 警告：API 鉴权失败（HTTP {http_code}），请检查 DEEPSEEK_API_KEY。")
    else:
        print(f"[!] LLM 请求失败：HTTP {http_code} -> {body_text[:200]}")


def _request_once(messages, temperature, max_tokens, *, allow_local: bool) -> str:
    """先试 API；allow_local 时失败降级 Ollama。单次尝试（不做重试）。"""
    # 1) 主力：DeepSeek API
    try:
        return _post_chat(
            messages, temperature, max_tokens,
            base_url=config.DEEPSEEK_BASE_URL,
            api_key=config.DEEPSEEK_API_KEY,
            model=config.DEEPSEEK_MODEL,
        )
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        _warn_balance(e.code, body_text)
    except urllib.error.URLError as e:
        print(f"[!] 网络错误：{e.reason}")
    except ReasoningBudgetError:
        raise  # 让 chat() 捕获并扩容重试
    except Exception as e:  # 解析失败/超时等
        print(f"[!] API 调用异常：{type(e).__name__}: {e}")

    # 2) 降级：Ollama 7B（仅 allow_local=True）
    if allow_local:
        try:
            print("[i] 降级到本地 Ollama qwen2.5:7b ...")
            return _post_chat(
                messages, temperature, max_tokens,
                base_url=config.OLLAMA_BASE_URL + "/v1",
                api_key="ollama",
                model=config.OLLAMA_MODEL,
            )
        except Exception as e:
            print(f"[!] Ollama 降级也失败：{e}")
    return ""


def _budget_retry_once(messages, temperature, max_tokens, *, allow_local):
    """带推理预算扩容的单次尝试：预算不足时 max_tokens 翻倍重试（最多扩到 MAX_BUDGET）。

    返回 (text, expanded)。非预算错误不在这里处理（交给上层重试）。
    """
    current = max_tokens
    while True:
        try:
            text = _request_once(messages, temperature, current, allow_local=allow_local)
            return text, (current != max_tokens)
        except ReasoningBudgetError as e:
            if current >= MAX_BUDGET:
                print(f"[!] 推理预算已达上限 {MAX_BUDGET}，仍无正式回答")
                return "", True
            current = min(current * 2, MAX_BUDGET)
            print(f"[i] 推理预算不足（max_tokens={e.max_tokens}），扩容到 {current} 重试...")


def chat(messages: list[dict], temperature: float = 0.3, max_tokens: int = 2000) -> str:
    """DeepSeek API：重试 3 次 + 推理预算自动扩容 + 空输出兜底 + 402 预警。

    失败（重试耗尽或空输出）抛 ModelError，调用方决定降级或中止。
    用于诊断/讲解/测评等允许降级的环节。
    """
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            text, _ = _budget_retry_once(messages, temperature, max_tokens, allow_local=False)
        except Exception as e:
            last_err = e
            text = ""
        if text:
            return text
        if attempt < MAX_RETRIES:
            time.sleep(1.5 * attempt)
    raise ModelError(f"LLM 调用失败（重试 {MAX_RETRIES} 次后无有效输出）：{last_err}")


def chat_with_fallback(messages: list[dict], temperature: float = 0.3,
                       max_tokens: int = 2000, allow_local: bool = False) -> str:
    """默认全走 API；allow_local=True 且 API 失败时降级 Ollama 7B。

    费曼追问环节必须传 allow_local=False（7B 会盲目附和，降智不可接受），
    API 挂时 feynman.py 应明确提示"离线模式不支持追问"而不是降级。
    """
    text, _ = _budget_retry_once(messages, temperature, max_tokens, allow_local=allow_local)
    if text:
        return text
    # 重试（API 失败但降级成功也算成功；两者都失败才抛错）
    for attempt in range(1, MAX_RETRIES):
        time.sleep(1.5 * attempt)
        text, _ = _budget_retry_once(messages, temperature, max_tokens, allow_local=allow_local)
        if text:
            return text
    raise ModelError("LLM 调用失败（API 与本地降级均无有效输出）")
