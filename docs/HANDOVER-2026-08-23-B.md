# FeynmanTutor · 交接文档 B（2026-08-23 下午-傍晚）

> 用途：本窗口（14:00-18:00）产出记录。开工先读 HANDOVER-2026-08-23.md（总交接），本文件是增量。
> 状态：B1-B5 完成（报告柱状图 / 可检查记忆 / 掌握门槛 / explanation / 章节过滤）+ 可观测性日志 + GitHub 发布，66 测试全绿。
> 数据：u0 重测完成（ch1 lecture 80%→100%，ch2 feynman 100%→100%），但**对照结论不成立**（见下）。

---

## 0. 一句话现状

**本窗口：B 阶段（叙事强化）5 项全部落地 + LLM 可观测性日志 + GitHub 发布，测试 62→66。** 用户决策：保留 FeynmanTutor，按计划书完善；**项目定位是"真正完整落地的项目"而非简历玩具**；多人对照数据等拉人（能拉 5 人以上，C 阶段列入主线）。

---

## 1. 重要事实（下一窗口必读）

### 1.1 重测数据结论：费曼 vs 讲解对照不成立
- ch1(lecture)：前测 80%(4/5) → 后测 100%(5/5)，+20pp
- ch2(feynman)：前测 100%(5/5) → 后测 100%(5/5)，+0pp
- **原因**：用户本人是 CS 学生，ch2 列表/字典前测就满分，天花板效应；加上 ch1/ch2 难度不对等 + 顺序偏差，三重污染。
- **结论**：不要再做单人重测（本人对 Python 基础太熟，重测一百遍都是 100%）。"费曼优于讲解"必须靠**多人随机分组**（C 阶段，拉不熟 Python 的同学，前测 40-60% 才有提升空间）。
- 这份数据作为"系统跑通 + 数据链路干净"的工程证据有效，作为教学法效果证据**无效**，简历别这么写。

### 1.2 环境坑（踩过，别再踩）
- **Anaconda site-packages 里有个第三方 `tests` 包**，遮蔽项目 tests/ 目录 → 已给 `tests/__init__.py` 解决。**以后所有 pytest 用 `/d/anacoda3/python.exe -m pytest tests/ -q`**（managed python 无 pytest/uvicorn/fastapi）。
- uvicorn 在 Anaconda：`/d/anacoda3/python.exe -m uvicorn web.app:app --host 127.0.0.1 --port 8001`
- 旧 Web 服务会占 8001 端口跑旧代码 → 改代码后必须 `Stop-Process` 重启（HANDOVER 4.8 同款坑，本窗口又踩一次）。
- CourseRAG 本窗口没起（8000 端口拒绝连接），讲解走 notes 兜底，不影响主流程和对照实验（ch1/ch2 同降级）。

---

## 2. 本窗口完成（B 阶段，按 ROI 顺序）

| 项 | 内容 | 验证 |
|---|---|---|
| **B1 报告对比柱状图** | `assessor.report()` 新增 `by_chapter`（每章最近一次前后测）；Web 报告页加 Chart.js 柱状图（X 章节、Y 正确率、前测灰/后测绿双柱） | API 返回 by_chapter；JS 语法 OK；页面含 reportChart |
| **B2 可检查记忆** | `profile.weak_points` 升级为 `[{kp_id, reason, evidence:[ex_id]}]`；`db.parse_weak_ids()` / `parse_weak_details()` 兼容旧格式；diagnostic 的 LLM prompt + 统计兜底都带证据链；report 返回 `weak_details`，CLI 报告打印"证据: 题目id" | 17 测试过；旧字符串格式自动兼容 |
| **B3 掌握门槛** | `_update_kp_mastery`：最近 3 条全错 → status=`blocked`；planner 把 blocked 及其递归依赖者排最后；recommender 跳过 blocked 及其依赖；新增 4 个测试 | test_p1 7→11 全过 |
| **B4 explanation 补全** | Python 包 40 题补 `explanation`（对齐 SQL 包）；`scripts/backfill_explanation.py` 可复跑；CLI 答错打印"📖 考点"，Web `/api/grade` 返回 explanation，前端答错展示 | 40/40 有 explanation；py.ch2.d.2 截断已单独修复 |
| **B5 薄弱点章节过滤** | `report(chapter=chN)` 时按 knowledge-graph 章节过滤薄弱点（原来 ch1/ch2 显示同一批全局薄弱点） | ch1 显示 ch1 的 kp，ch2 显示空（合理） |

### 傍晚追加（17:00-18:00）

| 项 | 内容 | 验证 |
|---|---|---|
| **前端 weak_points 渲染修复** | B2 改对象数组后，Web 诊断页/报告页显示 `[object Object]`——加 `weakId()` 兼容解析，诊断页顺带展示证据链（reason + evidence） | JS 语法 OK；/api/diagnose 返回带证据链 |
| **GitHub 发布** | 仓库 `fenxidapao/FeynmanTutor`（SSH 推送，main 分支）；新建 `.gitignore`（排除 .env/state.db/pyc）+ `.gitattributes`（LF 统一） | 77 文件，无敏感信息，本地 HEAD==远程（1bd096f→bba3f28） |
| **LLM 可观测性日志** | `model.py`：`_post_chat` 返回 (text, usage, latency)，chat 支持 `caller` + `LOG_HOOK`；`db.py`：新增 `llm_logs` 表 + `log_llm_call` + `llm_stats`；各 Agent 调用点标 caller；CLI `--usage` 命令；Web 启动时注册 hook | 实测 Web 一次诊断 = 7 调用 / 12,346 token / 76s（diagnostic 最重） |
| **生产级防御评估** | 对照"生产级 Agent 防御要点"评估：判题规则化已防"一本正经犯错"；model 重试/兜底/402/扩容=降级原型；已补可观测性（LLM 日志）。**不做**语义缓存/预算熔断/Schema 强约束（过度工程，简历够用） | 66 测试全绿 |
> **v2.1 修订注记（2026-08-23 夜间）**：本行"预算熔断=过度工程"已**部分作废**——每用户每日配额升级为必做（C1），语义缓存/Schema 强约束维持不做但理由改为"单机教学场景收益低"。修订明细见 PLAN.md 17.1。

**测试：66 passed**（62 + B3 新增 4；test_p1 原 7 + 新 4 = 11）。

---

## 3. 未完成清单（对照 PLAN.md 第 15 节待办）

| 优先级 | 未完成项 | 说明 |
|---|---|---|
| **主线** | **C 阶段多人对照** | 见 3.1——前端按 group_name 自动定 mode（app.js:89 硬编码 feynman），拉同学 n≥10 出组间对比数据 |
| 低 | 贡献热力图（1.5） | 观感项，GitHub commit graph 风格，优先级最低可砍 |
| 低 | TS 学习包 | node 子进程沙箱新机制，用户未学 TS，性价比最低 |
| 按需 | 爬合规语料扩充 | 廖雪峰更多章节 / Python 官方文档中文版（PSF），PLAN 4.6 合规红线 |
| 按需 | 部署 | CloudStudio 只支持静态站；FastAPI 需 Render/Railway，无简历增量先不做 |
> **v2.1 修订注记（2026-08-23 夜间）**：本行"无简历增量先不做"已**作废**——部署是 C 阶段落地前提，改走 Docker + SQLite 卷挂载（本机已有 Docker 29.7.2），方案见 PLAN.md 第 19 节。
| 按需 | vision-exp 评估 | exp 模型有下线风险，仅需看图时启用 |

### 3.1 最高优先级：C 阶段多人对照（拉人）
- 用户确认能拉 5 人以上 → Web 用户注册 + 随机分组（`users.group_name` 已支持 feynman/lecture）。
- **流程**：注册 → 自动分组 → 每组跑完整闭环（前测→诊断→教学→练习→后测）→ `--report` 出组间对比。
- **注意**：Web 前端 `app.js:89` 提交题组时**硬编码 `mode: "feynman"`**——多人实验若 lecture 组走 Web，需要前端加模式选择或后端按 group_name 自动决定 mode。这是 C 阶段第一个要改的点。
- 样本 n≥10 才有统计意义；新手前测低才有"40%→80%"故事。

### 3.2 可选（按需）
- **B 剩余**：贡献热力图（1.5，观感项，优先级最低，可砍）。
- TS 学习包 / 爬合规语料 / 部署：仍按原判断（TS 性价比最低，部署无增量）。

### 3.3 简历叙事（如实版）
> "FeynmanTutor——基于费曼学习法的个性化编程学习 Agent：多 Agent 协作（诊断/费曼教学/测评/规划/推荐）、沙箱+规则判题（Python+SQL 双机制）、SM-2 间隔复习、前测/后测硬评估、多用户设计、Web Dashboard（报告对比图+热力图）、LLM 调用可观测性（按环节 token/耗时），66 测试全绿。单人前后测验证数据链路（80%→100%）；多人随机分组对照实验进行中。"

---

## 4. 本窗口文件变更清单

- `agents/assessor.py`：+by_chapter、+weak_details、薄弱点按章节过滤
- `agents/diagnostic.py`：weak_points 带证据链（LLM prompt + 统计兜底）
- `agents/planner.py`：+blocked 暂缓逻辑；_rationale 支持 blocked 文案
- `agents/recommender.py`：+blocked 跳过
- `db.py`：+parse_weak_ids / parse_weak_details；_update_kp_mastery 加 blocked
- `main.py`：_weak_ids 用新解析；练习答错打印考点；诊断打印 kp_id
- `web/app.py`：/api/grade 返回 explanation
- `web/static/index.html`：+reportChartBox
- `web/static/app.js`：+renderReportChart；练习答错展示考点
- `learning_packs/python/exercises.jsonl`：40 题 +explanation
- `scripts/backfill_explanation.py`：新增（可复跑）
- `tests/__init__.py`：新增（修 Anaconda tests 包遮蔽）
- `tests/test_p1.py`：+4 掌握门槛测试
- `tests/test_flow.py`：断言适配新 weak_points 结构

### 傍晚文件变更（17:00-18:00）

- `model.py`：_post_chat 返回三元组 (text, usage, latency)；chat/chat_with_fallback 加 caller + LOG_HOOK + set_log_hook；_fire_hook 容错
- `db.py`：新增 llm_logs 表 + log_llm_call + llm_stats；参数名 model_name→model（对齐 hook）
- `agents/{diagnostic,feynman,planner,recommender}.py` + `rag.py`：调用点传 caller（diagnostic/feynman_followup/feynman_gaps/hint/planner/recommender/rag_filter）
- `main.py`：注册 log hook；新增 `--usage` 命令 + cmd_usage；health 传 caller
- `web/app.py`：启动时 db.init_db() + set_log_hook
- `web/static/app.js`：+weakId() 兼容解析；诊断页展示证据链；报告页薄弱点渲染修复
- `.gitignore` + `.gitattributes`：新增（GitHub 发布，排除 .env/state.db/pyc）
- `tests/test_model.py`：fake_post 适配三元组返回

**Git 状态**：初始提交 1bd096f + 可观测性提交 bba3f28，均已推送远程 main。后续提交命令：`git add -A && git commit -m "..." && git push origin main`（SSH 免密）。
