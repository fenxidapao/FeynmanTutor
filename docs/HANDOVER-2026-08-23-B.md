# FeynmanTutor · 交接文档 B（2026-08-23 下午）

> 用途：本窗口（14:00-15:00）产出记录。开工先读 HANDOVER-2026-08-23.md（总交接），本文件是增量。
> 状态：B1-B4 完成（报告柱状图 / 可检查记忆 / 掌握门槛 / explanation），66 测试全绿。
> 数据：u0 重测完成（ch1 lecture 80%→100%，ch2 feynman 100%→100%），但**对照结论不成立**（见下）。

---

## 0. 一句话现状

**本窗口：B 阶段（叙事强化）4 项全部落地，测试 62→66。** 用户决策：保留 FeynmanTutor，按计划书完善，多人对照数据等拉人（能拉 5 人以上，C 阶段列入主线）。

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

**测试：66 passed**（62 + B3 新增 4；test_p1 原 7 + 新 4 = 11）。

---

## 3. 遗留与建议（下一窗口）

### 3.1 最高优先级：C 阶段多人对照（拉人）
- 用户确认能拉 5 人以上 → Web 用户注册 + 随机分组（`users.group_name` 已支持 feynman/lecture）。
- **流程**：注册 → 自动分组 → 每组跑完整闭环（前测→诊断→教学→练习→后测）→ `--report` 出组间对比。
- **注意**：Web 前端 `app.js:89` 提交题组时**硬编码 `mode: "feynman"`**——多人实验若 lecture 组走 Web，需要前端加模式选择或后端按 group_name 自动决定 mode。这是 C 阶段第一个要改的点。
- 样本 n≥10 才有统计意义；新手前测低才有"40%→80%"故事。

### 3.2 可选（按需）
- **B 剩余**：贡献热力图（1.5，观感项，优先级最低，可砍）。
- TS 学习包 / 爬合规语料 / 部署：仍按原判断（TS 性价比最低，部署无增量）。

### 3.3 简历叙事（如实版）
> "FeynmanTutor——基于费曼学习法的个性化编程学习 Agent：多 Agent 协作（诊断/费曼教学/测评/规划/推荐）、沙箱+规则判题（Python+SQL 双机制）、SM-2 间隔复习、前测/后测硬评估、多用户设计、Web Dashboard（报告对比图+热力图），66 测试全绿。单人前后测验证数据链路（80%→100%）；多人随机分组对照实验进行中。"

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
