"""6 步闭环 E2E 冒烟（PLAN 18.5 D2）：Playwright 真实浏览器 + mock LLM 服务器。

流程：注册 → 前测 → 诊断 → 费曼(3 轮) → 后测 → 报告。
前提：8002 未运行则自动拉起 scripts/e2e_server.py（需已装 playwright + chromium）。

用法：/d/anacoda3/python.exe scripts/e2e_flow.py
"""

import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8002"
SERVER = None


def _ensure_server():
    global SERVER
    try:
        urllib.request.urlopen(BASE + "/health", timeout=2)
        return  # 已在跑
    except Exception:
        pass
    SERVER = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts" / "e2e_server.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        try:
            urllib.request.urlopen(BASE + "/health", timeout=1)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("e2e_server 启动失败")


def _answer_quiz(page, box_sel, kind):
    """答完整套题（每题选第一个选项）。"""
    page.wait_for_selector(f"{box_sel} .q")
    n = len(page.query_selector_all(f"{box_sel} .q"))
    for i in range(n):
        page.check(f"{box_sel} input[name=q{i}][value=0]")
    page.click(f"{box_sel} button.primary")
    page.wait_for_selector(f"{box_sel} .feedback")
    return n


def run():
    _ensure_server()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        uid = f"u_e2e_{uuid.uuid4().hex[:6]}"

        # 1 注册
        page.goto(BASE + "/")
        page.fill("#userId", uid)
        page.fill("#userPwd", "pass123")
        page.click("#btnRegister")
        page.wait_for_selector("#loginHint")
        hint = page.inner_text("#loginHint")
        assert "已登录" in hint and "实验组" in hint, f"登录提示异常: {hint}"

        # 2 前测（10 题）
        n_pre = _answer_quiz(page, "#pretestBox", "pretest")

        # 3 诊断
        page.click("#btnDiagnose")
        page.wait_for_selector("#diagnoseBox .stats")
        diag = page.inner_text("#diagnoseBox")
        assert "薄弱知识点" in diag, "诊断未渲染画像"

        # 4 费曼（3 轮追问 → 盲点总结 → 讲解 → 练习按钮）
        page.select_option("#kpSelect", "python.list.slice")
        page.click("#btnStartKp")
        for rnd in range(3):
            page.fill("#feynmanInput", f"切片就是 a[1:3] 取第1到3个元素（第{rnd + 1}轮）")
            page.click("#feynmanSend")
            page.wait_for_timeout(400)
        page.wait_for_selector("#feynmanChat .gap", timeout=15000)
        assert "盲点" in page.inner_text("#feynmanChat")
        page.wait_for_selector("#explainText", timeout=15000)  # 标准讲解
        page.click("text=开始练习")
        page.wait_for_selector("#practiceBox")

        # 5 后测
        page.click('button[data-step="posttest"]')
        _answer_quiz(page, "#posttestBox", "posttest")

        # 6 报告
        page.click('button[data-step="report"]')
        page.wait_for_selector("#reportBox .stats")
        rep = page.inner_text("#reportBox")
        assert "前测正确率" in rep and "后测正确率" in rep and "提升" in rep
        page.wait_for_selector("#reportChartBox:visible", timeout=5000)

        browser.close()
        print(f"[E2E OK] {uid} 6 步闭环通过（前测 {n_pre} 题）")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    finally:
        if SERVER:
            SERVER.terminate()
