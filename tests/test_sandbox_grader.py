"""sandbox.py + grader.py 单元测试（PLAN 15.3）。"""

import sandbox
import grader


# ---------- sandbox ----------

def test_normal_execution():
    r = sandbox.run_python('print("Hello")')
    assert r["ok"] is True
    assert r["stdout"].strip() == "Hello"
    assert r["exit_code"] == 0
    assert r["timed_out"] is False


def test_syntax_error():
    r = sandbox.run_python('print(')
    assert r["ok"] is False
    assert "SyntaxError" in r["stderr"]


def test_infinite_loop_timeout():
    r = sandbox.run_python("while True: pass", timeout=2)
    assert r["timed_out"] is True
    assert r["ok"] is False


def test_output_truncation():
    r = sandbox.run_python('print("x" * 100000)', max_output=100)
    assert len(r["stdout"]) <= 100


def test_empty_code_rejected():
    r = sandbox.run_python("   ")
    assert r["ok"] is False


# ---------- grader: mcq ----------

MCQ = {"type": "mcq", "check": {"options": ["a", "b", "c"], "answer": 1}}


def test_mcq_correct():
    ok, msg = grader.grade(MCQ, "1")
    assert ok is True


def test_mcq_wrong():
    ok, msg = grader.grade(MCQ, "0")
    assert ok is False


def test_mcq_invalid_input():
    ok, _ = grader.grade(MCQ, "abc")
    assert ok is False
    ok, _ = grader.grade(MCQ, "9")
    assert ok is False


# ---------- grader: output ----------

OUTPUT = {"type": "output", "check": {"expect_stdout": "3.5\n3"}}


def test_output_correct():
    ok, _ = grader.grade(OUTPUT, "print(7/2)\nprint(7//2)")
    assert ok is True


def test_output_wrong_value():
    ok, _ = grader.grade(OUTPUT, "print(1)")
    assert ok is False


def test_output_windows_newline_normalized():
    # 真实场景：学生代码用 \n 换行，Windows 子进程 stdout 会把 \n 转成 \r\n
    # （sandbox 解码后拿到 "3.5\\r\\n3\\r\\n"），grader 需归一化后再比对
    ok, _ = grader.grade(OUTPUT, 'print("3.5\\n3")')
    assert ok is True


# ---------- grader: code ----------

CODE = {"type": "code", "check": {"tests": ["assert z == 8"]}}


def test_code_passes():
    ok, msg = grader.grade(CODE, "x = 5\ny = 3\nz = x + y")
    assert ok is True
    assert "断言" in msg


def test_code_fails():
    ok, _ = grader.grade(CODE, "x = 5\ny = 3\nz = 10")
    assert ok is False


def test_code_with_student_bug():
    # 学生代码本身报错 → 判错
    ok, _ = grader.grade(CODE, "undefined_var + 1")
    assert ok is False
