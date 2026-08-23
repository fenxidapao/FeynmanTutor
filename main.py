"""FeynmanTutor CLI 入口（PLAN 14.8）。

用法：
  python main.py --learn python --user u0            # 完整闭环（前测→诊断→教学→练习→后测→报告）
  python main.py --pretest python --user u0          # 只做前测
  python main.py --feynman python.list.slice --user u0  # 只练某知识点（费曼+练习）
  python main.py --report python --user u0           # 出效果报告
  python main.py --health                            # 环境自检（沙箱/LLM/状态库）
"""

import argparse
import random
import sys

import config
import db
import learning_pack
import model
import sandbox
from agents import assessor, diagnostic, feynman

BANNER = r"""
  ______ _                     __  __            ___
 |  ____(_)                   |  \/  |          / _ \
 | |__   _ _ __  _   ___  __  | \  / |_   _    | | | |_ __ ___ _ __  ___
 |  __| | | '_ \| | | \ \/ /  | |\/| | | | |   | |_| | '_ ` _ \ '_ \/ __|
 | |    | | | | | |_| |>  <   | |  | | |_| |    \___/| | | | | | | \__ \
 |_|    |_|_| |_|\__,_/_/\_\  |_|  |_|\__,_|     |___/|_| |_| |_|_|  |___/
   费曼导师 —— 你当老师讲，Agent 追问找盲点
"""


def ask_mcq(prompt: str) -> str:
    """CLI 交互：等待用户输入答案。"""
    return input(prompt)


def _show_pretest_result(rate: float) -> None:
    print(f"\n[前测] 正确率 {rate * 100:.0f}%（基线）")


def _learn_flow(user_id: str, course: str, mode: str, chapter: str | None) -> None:
    """完整闭环：前测 → 诊断 → 费曼教学(薄弱点) → 沙箱练习 → 后测 → 报告。"""
    print(f"\n===== 完整学习闭环（user={user_id}, mode={mode}, chapter={chapter or 'all'}）=====")

    # 1) 前测
    pre_rate = assessor.run_pretest(user_id, chapter, mode, course, ask_user=ask_mcq)
    _show_pretest_result(pre_rate)

    # 2) 诊断（读答题记录，画薄弱点画像）
    profile = diagnostic.diagnose(user_id)
    weak = db.parse_weak_ids(profile)
    weak_tags = ", ".join(weak)
    print(f"\n[诊断] 薄弱点: {weak_tags if weak else '（暂无足够数据，先学薄弱章节）'}")
    if weak:
        print(f"[诊断] 学习偏好: {profile.get('learning_style')} | 平均正确率: {profile.get('avg_correct'):.0%}")

    # 3) 教学：对薄弱点（或该章节全部知识点）逐个讲解 + 费曼追问
    graph = learning_pack.load_graph(course)
    kps = graph["knowledge_points"]
    if chapter:
        kps = [kp for kp in kps if kp["chapter"] == chapter]
    # 优先讲薄弱点，其余按顺序
    target_kps = [kp for kp in kps if kp["kp_id"] in weak] + \
                 [kp for kp in kps if kp["kp_id"] not in weak]
    if not target_kps:
        target_kps = kps

    for kp in target_kps:
        print(f"\n===== 知识点: {kp['title']} =====")
        if mode == "feynman":
            # 先答后讲：先让用户讲，Agent 追问，再给讲解（费曼核心）
            print("[费曼] 先由你来讲这个知识点（先答后讲）：")
            result = feynman.feynman_round(
                user_id, kp["kp_id"], course,
                ask_user=lambda p: input(f"\n[你] {p}"),
            )
            if result["gaps"]:
                print(f"[费曼] 发现的盲点: {', '.join(result['gaps'])}")
            print("\n[讲解] 下面是标准讲解：")
            print(feynman.explain_kp(user_id, kp["kp_id"], course))
        else:
            # 纯讲解模式（对照组）
            print(feynman.explain_kp(user_id, kp["kp_id"], course))

        # 4) 练习（该知识点 1-2 题，沙箱判题）
        _practice_kp(user_id, kp, course)

    # 5) 后测（不同题、同知识点、同难度）
    post_rate = assessor.run_posttest(user_id, chapter, mode, course, ask_user=ask_mcq)

    # 6) 报告
    print(assessor.render_report(assessor.report(user_id, chapter)))
    print(f"\n[完成] 前测 {pre_rate * 100:.0f}% → 后测 {post_rate * 100:.0f}%"
          f"（提升 {(post_rate - pre_rate) * 100:+.1f}pp）")


def _practice_kp(user_id: str, kp: dict, course: str) -> None:
    """练习一个知识点：取该 kp 的练习题，最多 3 题，答错给方向提示。"""
    exercises = learning_pack.exercises_by_kp(course).get(kp["kp_id"], [])
    if not exercises:
        return
    picked = exercises[:3]
    print(f"\n[练习] {kp['title']}（{len(picked)} 题，沙箱判题）")
    for ex in picked:
        print(f"\n--- 练习: {ex['prompt']} ---")
        attempts = 0
        while attempts < 3:
            attempts += 1
            if ex["type"] == "mcq":
                for idx, opt in enumerate(ex["check"]["options"]):
                    print(f"  [{idx}] {opt}")
            answer = input(f"你的答案（第 {attempts} 次）: ").strip()
            if not answer:
                continue
            ok, msg = _grade_with_log(user_id, ex, answer)
            print(("✅ " if ok else "❌ ") + msg)
            if ok:
                break
            if attempts < 3:
                if ex.get("explanation"):
                    print(f"📖 考点: {ex['explanation']}")
                hint = feynman.hint_only(ex, {"user_answer": answer, "feedback": msg})
                print(f"💡 提示: {hint}")
        else:
            print("[练习] 3 次未通过，讲解已给，建议先复习知识点再回来。")
        # 每题最多试 3 次，做下一题


def _grade_with_log(user_id: str, ex: dict, answer: str):
    import grader
    ok, msg = grader.grade(ex, answer)
    db.log_exercise(user_id, ex["ex_id"], ex.get("kp_id", ""), ok, answer, msg)
    return ok, msg


def cmd_pretest(args) -> None:
    rate = assessor.run_pretest(args.user, args.chapter, args.mode, args.course,
                                ask_user=ask_mcq)
    print(f"\n[前测] 正确率 {rate * 100:.0f}% (记录于 assessments 表)")


def cmd_feynman(args) -> None:
    """只练某个知识点：讲解 + 费曼追问 + 练习。"""
    graph = learning_pack.load_graph(args.course)
    kp = graph["_by_id"].get(args.feynman)
    if kp is None:
        print(f"[错误] 未知知识点: {args.feynman}，可用: {', '.join(graph['_by_id'].keys())}")
        sys.exit(1)
    print(f"\n===== 知识点 {kp['title']}（费曼式）=====")
    result = feynman.feynman_round(
        args.user, kp["kp_id"], args.course,
        ask_user=lambda p: input(f"\n[你] {p}"),
    )
    if result["gaps"]:
        print(f"\n[费曼] 盲点: {', '.join(result['gaps'])}")
    print("\n[讲解]")
    print(feynman.explain_kp(args.user, kp["kp_id"], args.course))
    _practice_kp(args.user, kp, args.course)


def cmd_report(args) -> None:
    print(assessor.render_report(assessor.report(args.user, args.chapter)))


def cmd_path(args) -> None:
    """学习路径（P1 规划 Agent）：画像×知识图谱→定制路径。"""
    from agents import planner
    plan = planner.plan_path(args.user, args.course)
    print(f"\n===== 学习路径（user={args.user}）=====")
    for i, kp_id in enumerate(plan["path"], 1):
        marker = "🎯" if kp_id in _weak_ids(args.user) else "  "
        print(f"  {i:2d}. {marker} {plan['titles'].get(kp_id, kp_id)}")
    print(f"\n[规划说明] {plan['rationale']}")


def _weak_ids(user_id: str) -> set[str]:
    profile = db.get_profile(user_id) or {}
    return set(db.parse_weak_ids(profile))


def cmd_recommend(args) -> None:
    """习题推荐（P1 推荐 Agent）：按薄弱点+错题选练习。"""
    from agents import recommender
    r = recommender.recommend(args.user, args.course, top_n=args.top_n)
    print(f"\n===== 推荐练习（user={args.user}）=====")
    if not r["recommendations"]:
        print("  暂无推荐（先做前测/练习生成画像）")
        return
    for i, rec in enumerate(r["recommendations"], 1):
        print(f"  {i}. [{rec['kp_id']}] {rec['ex_id']}")
        print(f"     理由: {rec['reason']}")


def cmd_register(args) -> None:
    """注册用户（P1+ 多用户）。"""
    user = db.get_user(args.user, name=args.name)
    print(f"用户 {user['user_id']} 已就绪（name={user['name']}，group={user['group_name']}）")


def cmd_group(args) -> None:
    """把用户分到实验组（P1+ 组间对照：feynman/lecture）。"""
    user = db.assign_group(args.user, args.group)
    print(f"用户 {user['user_id']} → 实验组 {user['group_name']}")


def cmd_users(_args) -> None:
    """列出全部用户与分组。"""
    print(f"\n===== 用户列表（{len(db.list_users())} 人）=====")
    for u in db.list_users():
        g = u["group_name"] or "未分组"
        print(f"  {u['user_id']:10s} {u['name'] or '':10s} 组: {g}")


def cmd_review(args) -> None:
    """间隔复习（P2）：到期的知识点逐个复习，判题后更新 SM-2 间隔。"""
    from agents import scheduler
    due = scheduler.due_kps(args.user, args.course)
    if not due:
        print("没有到期复习的知识点，去学新内容吧。")
        return
    print(f"\n===== 间隔复习（{len(due)} 个知识点到期）=====")
    res = scheduler.run_review_session(args.user, args.course,
                                       ask_user=lambda p: input(p))
    print(f"\n[复习完成] 本轮 {res['reviewed']} 个知识点，"
          f"通过 {res['correct']} 个，需重练 {res['wrong']} 个")
    # 显示下轮提醒
    if res.get("results"):
        soonest = min(r["next_days"] for r in res["results"])
        print(f"下次复习最早在 {soonest} 天后，建议到时再跑 --review。")


def cmd_health(_args) -> None:
    """环境自检：状态库 / LLM / 沙箱 / 学习包 / RAG。"""
    ok_all = True

    def check(name: str, fn) -> None:
        nonlocal ok_all
        try:
            fn()
            print(f"[OK] {name}")
        except Exception as e:
            ok_all = False
            print(f"[FAIL] {name}: {e}")

    check("状态库可写", lambda: (db.init_db(), db.get_user("__health__")))
    # 注意：deepseek-v4-flash 是推理模型，max_tokens 太小会只输出 reasoning_content
    check("LLM 可用", lambda: model.chat([{"role": "user", "content": "回复OK两个字"}], max_tokens=200))
    check("沙箱可跑", sandbox.check_infrastructure)
    check("学习包完整", lambda: (
        len(learning_pack.load_exercises()) == 40,
        len(learning_pack.load_pretest()) == 10,
        len(learning_pack.load_posttest()) == 10,
    ))
    try:
        import rag
        rag._retrieve_raw("python 列表切片")
        print("[OK] CourseRAG 可检索")
    except Exception as e:
        ok_all = False
        print(f"[FAIL] CourseRAG: {e}")
    print(f"\n自检{'全部通过 ✅' if ok_all else '存在失败项 ❌'}")
    sys.exit(0 if ok_all else 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="FeynmanTutor", description="费曼导师——个性化学习 Agent")
    parser.add_argument("--learn", action="store_true", help="完整闭环（前测→诊断→教学→练习→后测→报告）")
    parser.add_argument("--pretest", action="store_true", help="只做前测")
    parser.add_argument("--feynman", metavar="KP_ID", help="只练某知识点（费曼+练习）")
    parser.add_argument("--report", action="store_true", help="出效果报告")
    parser.add_argument("--path", action="store_true", help="学习路径（P1 规划 Agent）")
    parser.add_argument("--recommend", action="store_true", help="习题推荐（P1 推荐 Agent）")
    parser.add_argument("--top-n", type=int, default=5, help="推荐题数（默认 5）")
    parser.add_argument("--register", action="store_true", help="注册用户（P1+ 多用户）")
    parser.add_argument("--group", choices=["feynman", "lecture"],
                        help="把用户分到实验组（P1+ 组间对照）")
    parser.add_argument("--users", action="store_true", help="列出全部用户与分组")
    parser.add_argument("--review", action="store_true", help="间隔复习（P2：到期知识点复习）")
    parser.add_argument("--health", action="store_true", help="环境自检")
    parser.add_argument("course", nargs="?", default="python", help="学习包（默认 python）")
    parser.add_argument("--user", default="u0", help="用户 id（默认 u0=本人）")
    parser.add_argument("--name", default=None, help="注册时的用户名")
    parser.add_argument("--mode", default="feynman", choices=["feynman", "lecture"],
                        help="教学模式：feynman=费曼式（实验组）/ lecture=纯讲解（对照组）")
    parser.add_argument("--chapter", default=None, choices=["ch1", "ch2"],
                        help="只学某章节（对照实验用）")
    args = parser.parse_args(argv)

    print(BANNER)
    db.init_db()
    # register 命令由 cmd_register 全权处理（带 name 创建），其余命令先确保用户存在
    if not args.register:
        db.get_user(args.user)

    if args.health:
        cmd_health(args)
    elif args.learn:
        _learn_flow(args.user, args.course, args.mode, args.chapter)
    elif args.pretest:
        cmd_pretest(args)
    elif args.feynman:
        cmd_feynman(args)
    elif args.report:
        cmd_report(args)
    elif args.path:
        cmd_path(args)
    elif args.recommend:
        cmd_recommend(args)
    elif args.register:
        cmd_register(args)
    elif args.group:
        cmd_group(args)
    elif args.users:
        cmd_users(args)
    elif args.review:
        cmd_review(args)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
