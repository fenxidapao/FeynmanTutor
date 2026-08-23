# FeynmanTutor（费曼导师）

基于费曼学习法的个性化学习 Agent 系统：你当老师讲，Agent 追问找盲点；系统建学习画像、
沙箱判题给硬反馈，前测/后测证明学习效果。多课程支持：**Python**（沙箱判题）+ **SQL**（sqlite3 判题）。

[![GitHub](https://img.shields.io/badge/GitHub-fenxidapao%2FFeynmanTutor-blue)](https://github.com/fenxidapao/FeynmanTutor)

> 项目计划书见 [PLAN.md](PLAN.md)，参考项目库见 [docs/REFERENCE.md](docs/REFERENCE.md)，交接文档见 [docs/HANDOVER-2026-08-23.md](docs/HANDOVER-2026-08-23.md)

## 快速开始

```bash
# 1. 环境：.env 需含 DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL
#    （从 deep-research 复制：cp ../agent/.env .env 后只保留 DEEPSEEK_* 三行）

# 2. 自检（状态库/LLM/沙箱/学习包/CourseRAG）
python main.py --health

# 3. 完整学习闭环（前测→诊断→费曼教学→沙箱练习→后测→效果报告）
python main.py --learn python --user u0

# 4. 其他命令
python main.py --pretest python --user u0            # 只做前测
python main.py --feynman python.list.slice --user u0 # 只练某知识点（费曼+练习）
python main.py --report python --user u0             # 出效果报告

# 5. P1：学习路径 / 习题推荐 / 多用户
python main.py --path python --user u0               # 学习路径（画像×知识图谱→定制路径）
python main.py --recommend python --user u0 --top-n 5 # 习题推荐（按薄弱点+错题选题）
python main.py --register python --user u_alice --name 同学A   # 注册用户
python main.py --group feynman --user u_alice        # 分到实验组（feynman/lecture）
python main.py --users python                        # 列出用户与分组

# 6. P3：Web Dashboard（FastAPI + 原生前端 + Chart.js 热力图）
uvicorn web.app:app --host 127.0.0.1 --port 8001 --reload
# 浏览器打开 http://127.0.0.1:8001/ 即可学习

# 7. P2：间隔复习（SM-2 简化算法：答对间隔翻倍 1→2→4→8→16→30 天，答错重置 1 天）
python main.py --review python --user u0              # 复习所有到期知识点

# 8. P2：SQL 课程（sqlite3 内存库判题，students/classes 预置表）
python main.py --learn sql --user u0                  # SQL 完整闭环
python main.py --feynman sql.where --user u0          # 只练 SQL 某知识点

# 9. 可观测性：LLM 调用统计（PLAN 8 多 Agent 效率评估：按环节 token/耗时）
python main.py --usage
```

## 对照实验（P1 验证教学法价值）

```bash
# 章节 A（对照组，纯讲解）
python main.py --learn python --user u0 --mode lecture --chapter ch1
# 章节 B（实验组，费曼式：先答后讲）
python main.py --learn python --user u0 --mode feynman --chapter ch2
```

同一人、不同章节、同难度知识点，对比两章节前后测提升差 = 教学法增量价值（PLAN 8）。

## 项目结构

```
main.py                  # CLI 入口
config.py / model.py     # 配置 + LLM 封装（deepseek-v4-flash，重试/兜底/402 预警）
db.py                    # SQLite 状态库（全部表带 user_id，多用户）
sandbox.py / grader.py   # 沙箱执行器 + 规则判题器（不调 LLM，防漂移）
sql_grader.py             # SQL 判题引擎（P2：sqlite3 内存库，students/classes 预置表）
rag.py                   # CourseRAG 检索封装（top-N 全量 → LLM 相关性过滤 → notes 兜底）
model.py                 # LLM 封装 + 可观测性 hook（每次调用记 token/耗时到 llm_logs 表）
agents/
  diagnostic.py          # 诊断 Agent：答题记录 → 学习画像
  feynman.py             # 费曼导师 Agent：角色反转教学（先答后讲）
  assessor.py            # 测评 Agent：前测/后测/效果报告
  planner.py             # 规划 Agent（P1）：画像×知识图谱→学习路径
  recommender.py         # 推荐 Agent（P1）：按薄弱点+错题选练习
  scheduler.py           # 复习调度器（P2）：SM-2 简化间隔算法
learning_packs/python/   # Python 学习包（12 知识点 + 40 规则题 + 前后测各 10）
learning_packs/sql/      # SQL 学习包（P2：12 知识点 + 40 规则题 + 前后测各 10，sqlite3 判题）
web/                     # P3 Web Dashboard（FastAPI + 原生前端 + Chart.js 热力图）
tests/                   # 单元测试 + 学习包质量自检
```

## 评估数据（真实运行，不编造）

每次运行自动写入 `state.db` 的 `assessments` 表：
`python main.py --report python --user u0` 输出前测 vs 后测正确率对比报告。
每次 LLM 调用自动写入 `llm_logs` 表（token/耗时按环节聚合）：`python main.py --usage` 查看。

## 数据与许可

- 练习题/前后测/notes：原创，无版权问题
- 讲解材料：经 CourseRAG `/retrieve` 检索廖雪峰 Python 教程（CC BY-NC-SA 4.0，已核实），
  仅作知识底座不复制原文；检索不到时用学习包 notes 兜底
- 详见 `learning_packs/python/README.md`

## 技术栈

Python 3 / DeepSeek API（deepseek-v4-flash）/ CourseRAG（HTTP）/ SQLite / subprocess 沙箱。
零第三方运行时依赖（标准库 urllib 直连 API），pytest 仅测试用。
