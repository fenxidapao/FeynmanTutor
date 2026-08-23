# FeynmanTutor · 参考项目库(REFERENCE.md)

> 用途:开新窗口/遇到问题/没思路时查这个文档。
> 原则:**不重复造轮子**——GitHub 有现成的直接抄/参考,不适配再改。
> 更新:2026-08-23(新增 DeepTutor/Bloom 竞品调研 + SQL 判题参考 + 复习调度参考)

---

## 0. 一句话索引(先看这里)

| 我要解决什么 | 抄/参考谁 |
|---|---|
| 学习数据模型(state.json) | learn-anything |
| 费曼教学法(角色反转) | feynman-tutor、learn-faster-kit(FASTER 的 T) |
| 间隔重复调度 | anki-mcp-server、Anki 算法(已落地 scheduler.py) |
| 多 Agent 编排 | 已有 LangGraph + supervisor(自研已有) |
| 知识库检索 | 已有 CourseRAG(993 块) |
| 教学评估体系 | towardsai/ai-tutor-app(evals.md) |
| 个性化学习画像/路径 | lumen、用户提供的「个性化学习系统」描述 |
| **个性化 Agent 全景/可检查记忆** | **DeepTutor(HKUDS 20k★,2026-08-23 调研)** |
| **自适应 AI 导师/Web 形态** | **Bloom(238★,2026-08-23 调研)** |
| 爆款叙事/README 风格 | TradingAgents(角色分工+backtest)、MetaGPT |
| Agent 理论 | ai-agent-book(李博杰) |
| 评测/效果评估 | 前测/后测(教育标准方法,无竞品公开做过) |
| 多 Agent 效率评估 | 已落地 llm_logs 表 + `main.py --usage`(按环节 token/耗时) |
| 生产级 Agent 防御 | `E:\AI 应用开发\生产级agent防御要点.txt`——本项目取"可观测性",判题规则化已防漂移 |

---

## 1. 教育场景竞品(star 排序,重点参考)

### 1.1 learn-anything(411★)——【形态最佳,数据模型直接抄】
- 地址:https://github.com/ChenChenyaqi/learn-anything
- 是什么:苏格拉底教学 + TDD 练习 + 间隔重复 + 知识热力图 + Dashboard 的 CLI/Skill
- **抄什么**:
  - `state.json` 单文件数据模型(concepts: status/confidence/practice_count/explain_count/last_explained/last_practiced/next_review/details)
  - 四工作流:/learn(建主题) /learn-explain(讲解) /learn-practice(练习) /learn-review(复习)
  - 知识地图渲染(render.mjs → knowledge-map.md)
- **看什么**:openspec/specs/skill-workflows/spec.md(完整工作流规格)

### 1.2 learn-faster-kit(359★)——【方向最重合,理论背书】
- 地址:https://github.com/hluaguo/learn-faster-kit(注意 README 里 fork 源是 cheukyin175)
- 是什么:AI 学习教练,FASTER 框架(Forget/Act/State/Teach/Enter/Review)
- **抄什么**:FASTER 框架的 "T=Teach 教别人巩固"(费曼学习法的科学版)——给"先答后讲"双重理论背书
- 特色:个人化 syllabi + 间隔重复 + 4 种学习模式(Balanced/Exam-Prep/Theory/Practical)
- **它缺什么(我们的差异化)**:沙箱判题(硬反馈)、前测/后测硬评估

### 1.3 feynman-tutor(20★)——【费曼教学法最小实现】
- 地址:https://github.com/koukekoukej-glitch/feynman-tutor
- 是什么:基于费曼学习法的 Skill——用户当老师讲,AI 追问暴露盲点
- **抄什么**:角色反转的追问逻辑、认知边界定位(ZPD)、分级诊断反馈(🔴关键误解/🟡不完整/🟢可优化)

### 1.4 anki-mcp-server(452★)——【间隔重复现成方案】
- 地址:https://github.com/ankimcp/anki-mcp-server
- 是什么:让 AI 操作 Anki 间隔重复卡片
- **抄什么**:间隔重复的调度思路(get_due_cards/rate_card);不必自研调度算法,状态模型记 next_review 即可

### 1.5 towardsai/ai-tutor-app(25★)——【评估体系最值得学】
- 地址:https://github.com/towardsai/ai-tutor-app
- 是什么:Agentic RAG tutor(LangGraph + ChromaDB + BM25 + RRF,和 CourseRAG 同款架构)
- **抄什么**:evals.md 评估体系——battery(测试集)/run(一次执行)/trace bundle(轨迹)/grade(评分),13 种策略对照实验
- **注意**:它花了约 $590 评估费,我们前测/后测本地免费,更划算

### 1.6 lumen(82★)——【可审计设计】
- 地址:https://github.com/ahmedEid1/lumen
- 是什么:一句话生成课程 + 课程级 RAG tutor,多智能体无 LangChain
- **抄什么**:"可审计 agent 决策"(为什么选这个课/知识点对用户可见)——信任设计

### 1.7 Mr.-Ranedeer-AI-Tutor(29.6k★)——【教训:纯 prompt 会死】
- 地址:https://github.com/JushBJJ/Mr.-Ranedeer-AI-Tutor
- **看什么**:29.6k★ 证明教育需求真实,但 DISCONTINUED——纯提示词无工程壁垒
- 教训:我们的工程化(沙箱+数据模型+评估)才是壁垒

### 1.8 PageLM(1.9k★)——【教育平台形态天花板】
- 地址:https://github.com/CaviraOSS/PageLM
- 是什么:NotebookLM 开源版(TS/React),学习资料→交互式学习体验
- 参考:Web 形态(P3 再做),无 agent 教学内核

### 1.9 education-agent-skills(658★)
- 地址:https://github.com/GarethManning/education-agent-skills
- 是什么:20 个教学领域 165 个循证教学 skill(CC BY-SA 4.0)
- 参考:教学法有理论体系;只是 skill 不是系统

### 1.10 PocketFlow-Tutorial-Codebase-Knowledge(12.6k★)
- 地址:https://github.com/The-Pocket/PocketFlow-Tutorial-Codebase-Knowledge
- 是什么:爬 GitHub 仓库→生成新手教程,上过 HN 首页
- 教训:场景极窄但极具体也能火;100 行 LLM 框架(PocketFlow)值得看

### 1.11 DeepTutor(20k★,2026-08-23 调研)——【赛道证明 + 差异化参照】
- 地址:https://github.com/HKUDS/DeepTutor
- 是什么:港大 HKUDS 的 Agent-native 通用学习工作空间——Chat/Quiz/Research/Solve/Mastery Path 全跑同一 agent loop,可检查记忆(L1/L2/L3 + Memory Graph),多 RAG 引擎(含自家 LightRAG),可咨询 Claude Code/Codex 等外部 agent。arXiv 论文,111 天 20k★。
- **学什么(可落地)**:
  1. **可检查记忆**:画像论断带证据链(哪些题判定薄弱)→ 我们的 profile.weak_points 应存 [{kp_id, reason, evidence}]
  2. **掌握门槛(Mastery gate)**:未达标不放行 → 练习 3 次未过标记 blocked,依赖它的 kp 暂缓推荐
  3. **测验题保存学生答案+参考答案+解释** → 已落地:SQL 学习包每题带 explanation 字段
- **不学什么**:统一 agent loop(架构比拼赢不了)、外部 agent 咨询(炫耀性)、Next.js 重前端
- **关键判断**:它没有前测/后测、没有沙箱判题——**反向验证我们的差异化(费曼+沙箱+硬评估)成立**

### 1.12 Bloom(238★,2026-08-23 调研)——【直接对标,Web 形态参考】
- 地址:https://github.com/Li-Evan/Bloom
- 是什么:基于 Bloom 2-Sigma 理论的 AI 家教——结构化大纲→逐课→标注反馈→自适应下一课;React+FastAPI 双模式(Web+CLI),个人中心含学习日历+贡献热力图
- **学什么**:贡献热力图(时间×知识点色块)是标志性 UI;官网 2-Sigma 数据可视化叙事(li-evan.github.io/Bloom)
- **不学什么**:React 重前端(我们已选原生,够用)
- **注意**:README demo.gif 已删,无在线 demo,实际界面需本地启动看

---

## 2. 爆款参照(非教育,学"怎么讲故事")

| 项目 | star | 学什么 |
|---|---|---|
| TauricResearch/TradingAgents | 99k★ | **角色分工(4 分析师)+ backtest 硬评估 + 论文背书**——爆款公式范本 |
| bytedance/deer-flow | 80k★ | 子代理+记忆+沙箱编排(字节) |
| FoundationAgents/MetaGPT | 70k★ | "AI 软件公司"角色协作叙事 |
| OpenBMB/ChatDev | 34k★ | LLM 多智能体协作开发 |
| HKUDS/nanobot | 47k★ | 轻量个人 agent 框架 |
| zhayujie/CowAgent | 46k★ | 超强 AI 助手(中文) |
| obra/superpowers | 276k★ | agent 技能框架(不抄,只看趋势) |

---

## 3. 技术栈参考(不重复造轮子)

| 需求 | 现成方案 | 决策 |
|---|---|---|
| Agent 编排 | 已有 LangGraph(自研三节点)+ smolagents | 复用,不换 |
| 知识库 RAG | 已有 CourseRAG(993 块,向量+BM25+RRF) | 复用/HTTP 调用,**调用侧 LLM 相关性过滤**(见下方改动说明) |
| 沙箱执行 | Python subprocess(自研,已有设计) | P0 自研简单版 |
| 判题 | 纯规则(自研) | P0 自研(output/code/mcq) |
| **SQL 判题(P2)** | **sqlite3 内存库(自研 sql_grader.py)** | 结果集比对 + 写操作表状态比对,已落地 |
| 间隔重复 | Anki 算法参考(ankimcp) | 已落地 scheduler.py(SM-2 简化:答对翻倍 1→2→4→8→16→30,答错重置 1 天) |
| 学习状态 | learn-anything state.json 模型 | 直接抄(加 user_id 多用户) |
| 评估 | ai-tutor-app evals 体系 + 前测/后测 + 多用户对照 | 融合 |
| 数据 | 已有 CourseRAG 993 块 + 廖雪峰语料 | 复用,**调用侧过滤** |
| LLM | deepseek-v4-flash(稳定版,API 主力) | 抄 deep-research model.py 思路(重试/兜底/402 + 推理预算自动扩容) |

> **改动说明（2026-08-22，检索策略）**：原计划 PLAN 4.6 为"调用侧 source 白名单过滤，
> 实测 CourseRAG `/retrieve` 接口**不支持 sources 参数**（`api_schemas.py` 的 RetrieveRequest
> 仅 question/mode 两个字段，传参被静默忽略）。经用户拍板改为：**检索 top-N 全量返回 →
> LLM 按内容相关性过滤 → notes 兜底**。零侵入 CourseRAG（三项目独立原则），不依赖 source 文件名；
> 代价是多一次 LLM 调用（P0 规模成本可忽略）。详见 `rag.py` 与 `learning_packs/python/README.md`。

## 3.5 合规爬取参考(补充语料时用)

| 源 | 许可 | 状态 |
|---|---|---|
| 廖雪峰 Python 教程 | CC BY-NC-SA 4.0(已核实) | ✅ 已入库 CourseRAG |
| Python 官方文档中文版 | PSF License(开源可商用) | 候选,开工核实 |
| MIT OCW 中文翻译 | CC BY-NC-SA | 候选,开工核实 |
| W3Schools/菜鸟教程 | 需核实 | 核实后定 |

**合规红线**:爬之前必须看到明确许可声明,记录来源+许可到学习包 README;个人项目非商用,优先 CC BY-NC 类。

---

## 4. 理论参考

- **费曼学习法**:https://fs.blog/feynman-technique/(权威解释)
- **FASTER 框架**(learn-faster-kit):Forget/Act/State/Teach/Enter/Review
- **AI Agent 理论**:ai-agent-book(李博杰,《深入理解 AI Agent》)https://github.com/bojieli/ai-agent-book(40k★)
- **间隔重复/遗忘曲线**:SM-2 算法(Anki 用)

---

## 5. 使用规则

1. 新窗口先读本文件 + PLAN.md;
2. 遇到"XXX 怎么做" → 先查本文件有没有参考,有就抄,没有才自研;
3. 抄的时候保留原项目思路,不适配才改,改的要在文档注明原因;
4. 每个被参考的项目,README/代码里保留出处链接(合规 + 可追溯)。
