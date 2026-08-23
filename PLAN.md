# FeynmanTutor(费曼导师)——项目计划书

> **定位**:基于费曼学习法的个性化学习 Agent 系统  
> **状态**:v2.0(2026-08-22 23:03,多用户兼容 + 语料策略 + 开工手册)  
> **配套文档**:docs/REFERENCE.md(参考项目库,抄什么看这个)  
> **一句话**:你当老师讲,Agent 追问找盲点;系统建学习画像、定专属路径,沙箱判题给硬反馈,前测/后测证明学习效果。

---

## 0. 开新窗口须知(先读这段)

- **我的需求(用户)**:要一个**写入简历的、真实落地的 AI Agent 项目**,不是玩具。业务场景:辅助学习编程与 AI 基础(我本人是 0 号用户,要学 Python/SQL/TypeScript/AI 基础)。必须有真实用户需求、真实效果评估、完整工程结构。**落地后可给同学用、可发网上给别人用(多用户)**。
- **我有什么**:两个已完成项目——CourseRAG(垂直 RAG,993 块课程语料,检索能力)+ deep-research-agent(LangGraph 三节点 Agent 编排,91 测试全绿)。都是真实跑通、有评测、有 Docker 的。FeynmanTutor 站在它们肩膀上,不重复造轮子。
- **注意什么**:
  1. 不重复造轮子——GitHub 有现成的直接抄(见 REFERENCE.md),不适配再改;
  2. 判题用确定性规则,LLM 只做讲解/诊断(防漂移);
  3. "先答后讲"是红线(费曼学习法核心),不可配置;
  4. 评估要硬:前测/后测正确率 + 对照实验,不编数据;
  5. 沙箱安全:超时+输出限制,学生代码可能死循环/删文件;
  6. **多用户设计**:状态库所有表带 `user_id`,从 P0 第一行代码就按多用户写(单人=一个 user,后续同学/网上用户=多 user,不返工);
  7. **语料策略**:学习包讲解材料从 CourseRAG 检索时**只检索 Python 相关 source**,CourseRAG 里数据结构/OS/数据库等与 Python 学习无关的语料不检索;缺的 Python 材料**爬合规真实数据**(CC 许可,见第 4.6 节)补充。
- **如何做**:见第 7/14/15/16 节(P0 先行 Python 单课程闭环,模块接口已定义,新窗口照写)。
- **我的想法**:见第 10 节(差异化判断)。

---

## 1. 项目概述

| 项    | 内容                                                                     |
| ---- | ---------------------------------------------------------------------- |
| 项目名  | **FeynmanTutor(费曼导师)**                                                 |
| 一句话  | 基于费曼学习法的个性化编程学习 Agent:你当老师讲,它追问找盲点;建学习画像、定专属路径、沙箱判题、前测后测评估             |
| 业务场景 | 教育·高校计算机专业学生学习编程/AI 基础(本人 0 号用户,可扩展同学/网上用户)                            |
| 技术栈  | Python / DeepSeek API(主力)/ CourseRAG(知识底座)/ SQLite(多用户)/ subprocess 沙箱 |
| 简历价值 | 多 Agent 教育系统(诊断/教学/测评,P1 加规划/推荐)+ 硬评估(前测后测)+ 多用户设计                     |

## 2. 为什么做(背景)

1. **教育场景需求真实**:Mr.-Ranedeer 29.6k★ 证明"个性化 AI 导师"是刚需,但纯 prompt 产品已 DISCONTINUED(无工程壁垒)——**工程化是我们的机会**;
2. **赛道没有爆款**:教育 agent 最高 star 的项目形态都不完整(有教学法无评估 / 有评估无教学法)——**三者组合(Feynman 教学法 + 沙箱硬反馈 + 前测后测硬评估)= 赛道唯一**;
3. **我本人就是目标用户**:正在学 Python/SQL/TS/AI 基础,需求真实;
4. **已有资产直接复用**:CourseRAG(993 块语料)+ deep-research(Agent 编排),不从零开始。

## 3. 需求定义(用户故事)

### 3.1 目标用户(多用户分层)

- **0 号用户(本人)**:嘉应学院计算机专业学生,学 Python/SQL/TS/AI 基础,期末复习/课程答疑/作业调研;
- **扩展用户(落地后)**:同班同学(试用反馈,不编数据)、网上学习者(发 GitHub/网页后自然用户)。

### 3.2 用户痛点

1. 课程知识点散落多门课笔记,检索靠 Ctrl+F;
2. 通用 AI 答的是泛化知识,不如自己的课程笔记准;
3. 学编程"看了会、做不对"——缺练习与即时反馈;
4. "以为自己会了"——缺主动回忆检验(费曼方法解决);
5. 缺个性化:大家都学同样的内容,不知道自己哪里薄弱。

### 3.3 核心需求(用户给的"个性化学习系统"描述,融合)

> 教育 Agent 最大的特点不是回答问题,而是根据每位学生的学习情况制定不同学习方案。  
> 系统分析学习行为/考试成绩/知识掌握程度 → 构建学习画像 → 结合教材/题库/课程知识库  
> → 制定专属学习路径;多个 Agent 分别承担**学习诊断、课程规划、习题推荐、阶段测评**,  
> 共同完成学习闭环;持续记录学习数据,不断调整学习计划(因材施教)。

**翻译成我们的功能**:

| 描述里的职责               | FeynmanTutor 的模块                  |
| -------------------- | --------------------------------- |
| 分析学习行为/成绩/掌握度 → 学习画像 | **诊断 Agent**(读答题记录/状态库,生成画像)      |
| 结合教材/题库/知识库 → 专属路径   | **规划 Agent**▲P1(画像 + 知识图谱 → 定制路径) |
| 个性化教学                | **费曼导师 Agent**(角色反转,先答后讲)         |
| 习题推荐                 | **推荐 Agent**▲P1(按薄弱点选题)           |
| 阶段测评                 | **测评 Agent**(前测/后测,量化进步)          |
| 持续记录、不断调整            | **状态库 + 调度器**(每次答题更新画像,路径动态调整)    |

## 4. 现有资产盘点(不重复造轮子)

| 资产                  | 位置                                             | 用途                                         | 复用方式                                |
| ------------------- | ---------------------------------------------- | ------------------------------------------ | ----------------------------------- |
| CourseRAG           | E:\WorkBuddy工作空间\2026-08-16-17-06-49\CourseRAG | 993 块课程语料检索(向量+BM25+RRF)                   | HTTP 调用 /retrieve,做讲解知识底座           |
| deep-research-agent | E:\AI 应用开发\agent                               | LangGraph 三节点编排 + 91 测试 + model.py(API 封装) | **model.py 思路直接抄**(重试/空输出兜底/402 预警) |
| 廖雪峰 Python 语料       | CourseRAG data/Python-廖雪峰教程-核心章节.md            | Python 讲解材料(CC BY-NC-SA 4.0)               | 经 /retrieve 检索(**限定该 source**)      |
| 本机环境                | DeepSeek API key + Ollama(qwen2.5:7b 备用)       | 讲解/诊断/追问 LLM                               | **API 主力,本地仅降级**                    |
| 竞品参考                | docs/REFERENCE.md                              | 抄什么/看什么                                    | 直接查                                 |

**架构决策**:FeynmanTutor 独立项目(E:\AI 应用开发\FeynmanTutor),通过 HTTP 调 CourseRAG,不共享代码——三个项目各司其职,简历分开写但可讲联动故事。

## 4.5 模型策略(2026-08-22 定稿)

| 决策        | 内容                                           | 理由                                                                   |
| --------- | -------------------------------------------- | -------------------------------------------------------------------- |
| **默认模型**  | **`deepseek-v4-flash`**(稳定版)                 | 已在 deep-research 全程验证;质量稳定,面试演示不翻车                                   |
| **候选模型**  | `deepseek-v4-flash-vision-exp`(实测可用)         | **仅 P1 可选**(如需看图/截图/画图解释);exp=实验版,有变更/下线风险,不进 P0 主流程                 |
| **降级**    | Ollama qwen2.5:7b                            | 仅"断网/欠费"兜底;**费曼追问环节不降级**(7B 会盲目附和讲错内容,降智不可接受)——API 挂时明确提示"离线模式不支持追问" |
| **配置**    | `model.py` 单一入口,环境变量切换                       | 不锁死;一行改模型                                                            |
| **容错**    | 重试 + 空输出兜底 + 402 余额预警                        | 抄 deep-research 已验证方案                                                |
| **模型名注意** | 账号模型是 `deepseek-v4-flash`(非默认 deepseek-chat) | deep-research 踩过坑,写对否则 404                                           |

**成本估算**:单次讲解/追问/诊断 500-2000 token;一天学 1 章节约 2 万 token ≈ 0.05-0.1 元;P0 全程(本人当用户跑 10 次)约 1-3 元。**全 API 成本可忽略,不用本地省这个钱。**

## 4.6 语料策略(2026-08- 22 23:17 修订,实测验证)

**问题**:CourseRAG 的 993 块是混合语料(数据结构/OS/数据库/计网 + 廖雪峰 Python)。FeynmanTutor 学 Python 时,检索可能混入无关内容。

**实测发现(2026-08-22 23:17,本机 8000 端口验证)**:

- CourseRAG `/retrieve` 的 `RetrieveRequest` **只有 `question` + `mode`,不支持 `sources` 过滤参数**(新窗口 AI 实测确认);
- **更重要**:按文件名过滤会**误杀真材实料**——"我的学习笔记.md"文件名不带 python,但内容就是 Python(字典/列表/语法示例)。检索系统本身是"内容相关"而非"文件名相关",Python 问题实测命中 Python 内容块,混入的非 Python 块只是少数且排在后面。

**策略(修订后,不做 source 白名单)**:

1. **检索取 top-N 全量返回,由 LLM 内容过滤**:`retrieve_tutor_context(query)` 直接调 `/retrieve`,取 accurate 模式 top-5(必要时 top-8),**全给费曼导师 Agent**;提示词明确写"只基于与问题相关的上下文讲解,忽略无关内容"——LLM 有上下文相关性判断能力,这是 RAG 标准做法,不算"LLM 判题"(讲解是生成,不是判对错,无漂移问题);
2. **自建 notes 兜底**:学习包 `notes/` 放少量精编讲解(每知识点 2-3 句,人工写),检索结果为空/质量差时兜底,不依赖 CourseRAG;
3. **爬合规真实数据(补充)**:缺 Python 材料时,爬**有明确开放许可**的公开教程(参考已核实的廖雪峰 CC BY-NC-SA 4.0 流程):
   - **候选源**(开工时逐个核实许可再爬):廖雪峰其他章节、Python 官方文档中文版(Python Software Foundation License,开源可商用)、W3Schools 中文(需核实)、CC 许可的大学课程讲义(MIT OCW 中文翻译等);
   - **合规红线**:爬之前必须看到页面/仓库明确许可声明(CC/MIT/PSF 等),记录来源链接 + 许可到学习包 README;个人学习项目非商用,优先 CC BY-NC 类;
   - 爬取脚本仿 `build_python_corpus.py`(CourseRAG 里已有,可复现);
4. **不爬的**:有版权的教材扫描件、需要登录的付费内容、反爬强且许可不明的站点。

## 5. 多 Agent 架构

```
用户(本人/同学/网上用户,user_id 区分)
   │ 提问 / 做题 / 讲解
   ▼
┌─────────────────────────────────────────┐
│  FeynmanTutor 编排层(LangGraph 复用思路)  │
│                                         │
│  ① 诊断 Agent ★P0 ── 读该 user 的状态库   │
│      → 学习画像(薄弱点/掌握度)            │
│  ② 费曼导师 Agent ★P0 ── 角色反转教学     │
│      (你讲 → 它追问 → 找盲点,先答后讲)    │
│  ③ 测评 Agent ★P0 ── 前测/后测/效果报告   │
│  ─────────────────────────────────────   │
│  ④ 规划 Agent ▲P1 ── 画像×知识图谱→路径   │
│  ⑤ 推荐 Agent ▲P1 ── 按薄弱点选练习       │
└───────┬──────────────┬───────────────┘
        │ 工具调用        │ 工具调用
        ▼                ▼
┌──────────────┐   ┌──────────────────┐
│ 沙箱执行器    │   │ 知识检索          │
│ 跑学生代码    │   │ (HTTP→CourseRAG,  │
│ 判题(规则)   │   │  source 白名单)   │
└──────┬───────┘   └──────────────────┘
       ▼
┌──────────────────────────────┐
│ 状态库(SQLite,user_id 分区)   │
│ 学习画像/掌握度/错题/复习计划   │
│ → 效果评估数据源(前测后测)     │
└──────────────────────────────┘
```

**P0/P1 分工理由**:P0 数据量小(2 章节 12 点),"规划专属路径"和"推荐习题"没有足够画像支撑,做了是空转;先跑通"诊断→教学→测评"闭环拿到真实数据,P1 再让规划/推荐 Agent 有据可依。**避免为架构而架构。**

## 6. 数据模型(抄 learn-anything,融合画像,多用户)

### 6.1 学习包(每门课一个目录,共享,不分用户)

```
learning-packs/python/
  knowledge-graph.json   # 知识点依赖图(含 source 白名单字段)
  exercises.jsonl        # 题目(含测试用例/期望输出/前置知识点/题型)
  pretest.jsonl          # 前测题(学章节前)
  posttest.jsonl         # 后测题(学章节后,**不同题**、同知识点、同难度)
  notes/                 # 精编讲解兜底(md,每知识点 2-3 句,检索不到时用)
  README.md              # 数据来源 + 许可声明(合规)
```

### 6.2 状态库(SQLite,画像数据源,全部带 user_id)

```sql
CREATE TABLE users (                    -- 多用户(0 号=本人,后续同学/网上用户)
  user_id TEXT PRIMARY KEY,             -- 'u0' / 任意 id
  name TEXT, created_at TEXT
);

CREATE TABLE knowledge_points (         -- 每个用户的掌握度
  user_id TEXT NOT NULL,
  kp_id TEXT NOT NULL,                  -- 'python.list.slice'
  title TEXT NOT NULL,
  chapter TEXT NOT NULL,
  prerequisites TEXT DEFAULT '[]',      -- JSON 前置
  mastery REAL DEFAULT 0.0,             -- 掌握度 0~1
  seen_count INTEGER DEFAULT 0,
  correct_count INTEGER DEFAULT 0,
  explain_count INTEGER DEFAULT 0,      -- 费曼:讲过几次
  last_explained TEXT,
  last_practiced TEXT,
  next_review TEXT,                     -- 间隔复习时间
  status TEXT DEFAULT 'new',            -- new/learning/reviewing/mastered
  PRIMARY KEY (user_id, kp_id)
);

CREATE TABLE exercise_logs (            -- 答题记录 → 画像/评估
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  kp_id TEXT, ex_id TEXT, attempt INTEGER,
  correct INTEGER, user_answer TEXT, feedback TEXT, created_at TEXT
);

CREATE TABLE assessments (              -- 前测/后测 → 效果评估
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  chapter TEXT, kind TEXT,              -- pretest/posttest
  mode TEXT,                            -- 'lecture'纯讲解 / 'feynman'费曼式(对照用)
  score REAL, total INTEGER, created_at TEXT
);

CREATE TABLE profile (                  -- 学习画像(诊断 Agent 输出)
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  weak_points TEXT,                     -- JSON:薄弱知识点
  learning_style TEXT,                  -- 偏好(简答/代码/类比)
  avg_correct REAL, updated_at TEXT
);
```

## 7. P0 范围(最小闭环,先跑通)

**目标**:能回答"我学了 Python 列表,效果如何?"——完整闭环 + 硬评估。

| 项          | 内容                                                                     |
| ---------- | ---------------------------------------------------------------------- |
| 课程         | Python 单课程,2 章节(变量/数据类型 + 列表/字典),约 12 知识点 40 题                         |
| **题目**     | 练习 40 题(**全部可规则判**:输出比对/测试用例/选择题)+ 前测 10 题 + **后测 10 题(不同题、同知识点、同难度)** |
| 核心流程       | 前测 → 诊断(画像) → 费曼教学(讲解+追问) → 沙箱练习 → 判题 → 后测 → 效果报告                      |
| Agent(3 个) | 诊断 Agent + 费曼导师 Agent + 测评 Agent(规划/推荐 P1)                             |
| 多用户        | 状态库全带 user_id,CLI 可 `--user` 指定(默认 u0)                                 |
| 交付         | CLI 可完整跑一遍:`python main.py --learn python --user u0`                   |
| 评估产出       | 前测正确率 vs 后测正确率(不同题),输出对比报告                                             |

**验收标准**:

```
$ python main.py --learn python --user u0
→ 前测 10 题(记录正确率,如 40%;题目与后测不同)
→ 诊断:薄弱点 = [变量类型, 列表切片]
→ 费曼教学:讲"列表切片"(HTTP→CourseRAG 检索,限定 Python source + notes 兜底;不直接给练习答案)
→ 练习 3 题(沙箱跑代码,规则判题,答错只提示方向)
→ 后测 10 题(不同题同难度,正确率如 80%)
→ 报告:前测 40% → 后测 80%,提升 +40pp;薄弱点已覆盖
```

**P0 题目规则(关键约束)**:40 题全部设计成可规则判题型,不引入 LLM 判题(防漂移);解释型/主观题 P1 再加(需注明 LLM 判题漂移风险)。

## 8. 效果评估设计(简历最硬的部分)

| 评估项                | 方法                                                        | 数据源                 | 面试价值                                   |
| ------------------ | --------------------------------------------------------- | ------------------- | -------------------------------------- |
| **学习效果(主)**        | 前测/后测正确率对比(**不同题、同知识点同难度**)                               | assessments 表       | "Python 列表章节:前测 40%→后测 80%"            |
| **费曼教学价值**         | **单人两轮对照(P0)**:章节 A 纯讲解学(无追问),章节 B 费曼式学(先答后讲),分别前后测,对比提升差 | 章节 A/B 数据(mode 字段)  | "费曼式比纯讲解提升多 +Xpp"(单人可完成)               |
| **诊断价值**           | 同上:章节 B 带诊断 vs 章节 A 不带,对比                                 | 同上                  | "诊断让薄弱点提升 +Xpp"                        |
| **间隔复习有效性**        | 复习 vs 不复习,7 天后正确率                                         | exercise_logs       | "7 天后复习组正确率高 X%"                       |
| **多 Agent 效率**     | 各环节耗时/token 消耗                                            | 日志                  | 工程数据                                   |
| **多用户对照(P1+,落地后)** | 同学/网上用户注册,随机分组(费曼组 vs 讲解组),组间对比                           | users + assessments | "n 名真实用户,费曼组提升显著高于对照组"——**有真实样本的对照实验** |

**对照实验设计(关键)**:

- **P0(单人)**:同一人、不同章节做对照——章节 A 用"纯讲解"模式(mode=lecture),章节 B 用"费曼+诊断"模式(mode=feynman),各做前后测;对比两章节提升差 = Agent 教学法增量价值;
- **注意**:两章节难度要接近(选同等级知识点),否则提升差被难度差污染——P0 选"变量/数据类型"和"列表/字典";
- **P1+(多用户)**:发同学/网上后,users 表天然支持随机分组,做组间对照(n≥10 时统计有意义)——**这是单人对照的升级路径,数据结构已预留**;
- **红线**:所有数字来自真实运行,不编;对照组用真实数据,可复现(脚本记录)。

## 9. 路线图

| 阶段     | 内容                                                                           | 产出                                               | 估时    |
| ------ | ---------------------------------------------------------------------------- | ------------------------------------------------ | ----- |
| **P0** | Python 学习包(40 规则题 + 前后测各 10)+ 状态库(多用户)+ 沙箱判题 + **3 Agent(诊断/费曼教学/测评)** + CLI | `main.py --learn python --user u0` 全闭环 + 前后测对比报告 | 3-5 天 |
| **P1** | 规划 Agent + 推荐 Agent + 费曼 vs 讲解单人对照实验 + vision-exp 可选评估 + **多用户注册/分组**        | 对照数据 + 画像→路径 + 可分享给同学                            | 3-4 天 |
| **P2** | 间隔复习闭环 + 扩展 SQL/TS 学习包 + 爬合规补充语料                                             | 多课程 + 复习数据                                       | 1 周   |
| **P3** | Web Dashboard(画像可视化/热力图)+ 部署(可公开访问)+ 文档/README/测试补全                          | 可展示产品 + 简历定稿 + 真实用户                              | 1 周   |

## 10. 我的想法(差异化判断,重要)

1. **为什么是"费曼 + 多 Agent"而不是单一问答**:单问答(RAG tutor)没有差异化(ai-tutor-app 证明只有 25★);多 Agent 个性化系统(用户描述的方向)是教育行业热点,但没人做出完整开源实现——我们做出来就是第一梯队;
2. **为什么前测/后测是杀手锏**:教育 agent 没有竞品公开过学习效果数据(learn-anything/learn-faster-kit 只有"进度"没有"效果")——我们能拿出"前测 40%→后测 80%"这种教育标准评估,面试无法质疑;
3. **为什么判题用规则**:LLM 判题会漂移(同一答案两次结果不同),学习工具不可接受;规则判题 + LLM 解释,是"工程正确"的体现;
4. **为什么独立项目**:三个项目(CourseRAG/deep-research/FeynmanTutor)各自独立、简历分开写、可讲联动故事——不互相污染;
5. **为什么 P0 只做 3 个 Agent**:数据量小,规划/推荐没有画像支撑是空转;先跑通闭环拿真实数据,P1 再上(P0 克制是原则,不是能力不足);
6. **为什么一上来就多用户**:单人改多用户是出了名的返工重灾区(所有 SQL 加 user_id);P0 就从第一行代码按多用户写,落地分享零成本;
7. **成本**:全 API(deepseek-v4-flash)为主,P0 全程约 1-3 元,可忽略;不用本地省这个钱(本地 7B 会降智,尤其费曼追问环节)。

## 11. 风险与对策

| 风险                 | 对策                                                          |
| ------------------ | ----------------------------------------------------------- |
| 学习包建设是大头,题目质量决定效果  | LLM 生成 + 人工过一遍;P0 只做 2 章节验证                                 |
| 沙箱安全(死循环/删文件)      | 超时 5s + 输出 64KB + 子进程隔离 + 临时目录                              |
| 教学法有效性存疑           | P1 对照实验(费曼 vs 讲解)用数据说话,不好就改                                 |
| 3 个项目联动复杂度         | HTTP 解耦,不共享代码;P0 检索带 source 白名单                             |
| CourseRAG 语料混入无关内容 | source 白名单(第 4.6 节)+ notes 兜底                               |
| 爬数据合规              | 只爬有明确开放许可的源,记录许可到 README;违规不爬                               |
| 时间不够(学生)           | P0 严格 2 章节闭环,跑通即算完成,不贪多                                     |
| API 不稳定(实验版/限流/欠费) | P0 用稳定版 deepseek-v4-flash;重试+空输出兜底+402 预警;本地 7B 仅降级,费曼追问不降级 |
| 前测/后测失真(记住答案)      | 前后测**不同题、同知识点、同难度**(P0 验收硬约束)                               |
| 多用户安全(网上用户)        | P0 无鉴权(P3 部署时加);多用户只是数据隔离,不暴露他人数据                           |

## 12. 开源 PR 计划(网友建议,纳入)

> 网友:去 GitHub 找真实 issue 修 bug 提 PR,被合并的 PR 比闭门造车更有含金量。

- **已选目标**:smolagents(深度使用过,踩坑经验真实)——补 CodeAgent 超时参数文档(官方 docs 零覆盖,真实痛点);
- 行动计划:docs/SMOLAGENTS_PR_PLAN.md(在 deep-research 项目里,已写);
- 时间盒 2-3 周,合并与否都如实写简历;
- **注意**:自建项目是主线,PR 是加分项,不要本末倒置。

## 13. 面试叙事(简历怎么写)

> **一句话**:「FeynmanTutor——基于费曼学习法的个性化学习 Agent 系统:诊断学习画像、费曼式教学(先答后讲)、沙箱判题,前测/后测证明学习效果(Python 章节前测 40%→后测 80%);多用户设计,可分享给同学/网上学习者。」
>
> **讲什么**:
>
> 1. 多 Agent 分工(诊断/教学/测评,P1 规划/推荐)——借鉴 TradingAgents 角色化;
> 2. 费曼学习法(先答后讲)——有理论背书(费曼 + FASTER 框架);
> 3. 硬评估(前测/后测 + 对照实验)——教育标准方法,竞品没有公开数据;
> 4. 工程化(规则判题防漂移/沙箱安全/SQLite 多用户画像/可复现评估);
> 5. 联动故事(CourseRAG 知识底座 + deep-research 编排思路 + FeynmanTutor 教学);
> 6. 真实用户路径(本人 0 号 → 同学 → 网上,数据真实不编)。

---

## 14. 模块接口设计(新窗口照这个写代码)

```
E:\AI 应用开发\FeynmanTutor\
├── main.py                  # CLI 入口
├── config.py                # 环境变量: DEEPSEEK_API_KEY/BASE_URL/MODEL, RAG_BASE_URL, DB_PATH
├── model.py                 # LLM 封装(抄 deep-research 思路)
├── db.py                    # SQLite 封装
├── sandbox.py               # 沙箱执行器
├── grader.py                # 规则判题器
├── agents/
│   ├── __init__.py
│   ├── diagnostic.py        # 诊断 Agent(画像)
│   ├── feynman.py           # 费曼导师 Agent(角色反转教学)
│   └── assessor.py          # 测评 Agent(前测/后测/报告)
├── learning_packs/
│   └── python/
│       ├── knowledge-graph.json
│       ├── exercises.jsonl
│       ├── pretest.jsonl
│       ├── posttest.jsonl
│       ├── notes/
│       └── README.md        # 数据来源+许可
└── tests/
```

### 14.1 model.py(抄 deep-research 的 model.py 思路)

```python
def chat(messages: list[dict], temperature=0.3, max_tokens=2000) -> str:
    """DeepSeek API 调用:重试 3 次 + 空输出兜底 + 402 余额预警。
    模型: config.DEEPSEEK_MODEL('deepseek-v4-flash')。
    返回纯文本;失败抛 ModelError(调用方决定降级)。"""

def chat_with_fallback(messages, allow_local=False) -> str:
    """默认全走 API;allow_local=True 且 API 失败时降级 Ollama 7B。
    费曼追问环节调用时传 allow_local=False(强制 API,7B 会降智)。"""
```

### 14.2 db.py

```python
def init_db(db_path: str) -> None:        # 建表(第 6.2 节)
def get_user(user_id: str) -> dict:       # 用户存在?没有则建
def upsert_kp(user_id, kp: dict) -> None: # 更新知识点状态
def log_exercise(user_id, ex_id, kp_id, correct, answer, feedback) -> None:
def record_assessment(user_id, chapter, kind, mode, score, total) -> None:
def get_profile(user_id) -> dict:         # 读画像
def save_profile(user_id, profile: dict) -> None:
```

### 14.3 sandbox.py

```python
def run_python(code: str, timeout=5, max_output=65536) -> dict:
    """subprocess 跑学生代码:超时 5s、stdout/stderr 各限 64KB、
    工作目录为临时目录(无写权限)、Windows CREATE_NO_WINDOW。
    返回 {'ok':bool,'stdout':str,'stderr':str,'exit_code':int,'timed_out':bool}"""
```

### 14.4 grader.py

```python
def grade(exercise: dict, result: dict) -> tuple[bool, str]:
    """按 exercise['type'] 分支:
    'output'  : result.stdout.strip() == exercise['check']['expect_stdout'].strip()
    'code'    : 跑附加测试(如 len()/断言),见 check['tests']
    'mcq'     : 学生选择索引 == check['answer']
    返回 (是否通过, 简短结果)。纯规则,不调 LLM。"""
```

### 14.5 agents/diagnostic.py(诊断 Agent)

```python
def diagnose(user_id, db) -> dict:
    """读 exercise_logs/assessments → 用 LLM 生成画像:
    {'weak_points': [...], 'learning_style': '...', 'avg_correct': 0.6}
    LLM 输出 JSON,解析失败兜底为纯统计(正确率排序取最低)。"""
```

### 14.6 agents/feynman.py(费曼导师 Agent,核心)

```python
def explain_kp(user_id, kp, db) -> str:
    """讲解:HTTP→CourseRAG /retrieve(query, mode=accurate) 取 top-5~8 全量返回;
    提示词要求 LLM 只基于相关内容讲解(忽略无关上下文);notes 兜底。
    禁止包含练习答案。"""

def feynman_round(user_id, kp, db, max_rounds=3) -> dict:
    """角色反转:用户讲概念 → Agent 追问找盲点(chat_with_fallback, 强制 API)。
    3 轮后总结薄弱点,更新 explain_count。
    返回 {'transcript': [...], 'gaps': [...]}。"""

def hint_only(exercise, result) -> str:
    """答错时只给方向提示(如'想想切片索引从几开始?'),不给答案。
    3 次尝试后允许放弃讲解。"""
```

### 14.7 agents/assessor.py(测评 Agent)

```python
def run_pretest(user_id, chapter, mode, db) -> float:   # 前测,返回正确率
def run_posttest(user_id, chapter, mode, db) -> float:  # 后测(不同题同难度)
def report(user_id, chapter, db) -> dict:
    """效果报告: pretest vs posttest 正确率、提升 pp、薄弱点覆盖情况。"""
```

### 14.8 main.py(CLI)

```
python main.py --learn python --user u0          # 完整闭环
python main.py --pretest python --user u0        # 只做前测
python main.py --feynman python.list.slice --user u0  # 只练某知识点
python main.py --report python --user u0         # 出效果报告
```

## 15. 待办(新窗口开工顺序)

- [x] `config.py` + `db.py`(第 6.2 节表,全带 user_id)+ `model.py`(抄 deep-research,deepseek-v4-flash,重试/兜底/402);
- [x] 建 Python 学习包:knowledge-graph.json(12 点,含 source 白名单)+ 40 规则题 + 前测 10 + **后测 10 不同题同难度**——最花时间,先做;
- [x] `sandbox.py` + `grader.py`(先于 Agent,保证硬反馈),pytest 覆盖(死循环/超时/输出比对);
- [x] `agents/`:诊断 → 费曼导师(讲解/追问/提示) → 测评(前后测/报告);
- [x] `main.py` CLI 串起"前测→诊断→费曼教学→练习→判题→后测→报告"(28 测试全绿,含 mock LLM 闭环集成测试 + 推理预算扩容);
- [~] 跑真实数据:本人当用户,章节 A(mode=lecture)vs 章节 B(mode=feynman)对照,记录前后测;
  - 2026-08-23 下午已重测:ch1(lecture)80%→100%,ch2(feynman)100%→100%——**对照不成立**(本人前测天花板),改走 C 阶段多人随机分组,见 HANDOVER-2026-08-23-B.md
- [x] 测试补全 + README + 数据许可声明(README/许可已写,测试 62 全绿);
- [x] P1:规划/推荐 Agent + 多用户注册分组 + vision-exp 可选(35 测试全绿;vision-exp 按需再加);
- [x] P3:Web Dashboard(FastAPI+原生前端+Chart.js 热力图)已完成,62 测试全绿;部署后议;
- [x] P2:间隔复习闭环(SM-2 简化,--review)+ SQL 学习包(12 知识点/40 规则题/前后测各 10,sqlite3 判题器)已完成,62 测试全绿;TS 学习包/爬语料待做(按需)。
- [x] **B 阶段(2026-08-23 下午)**:报告前后测对比柱状图 + 可检查记忆(weak_points 带证据链) + 掌握门槛(blocked) + Python 包 40 题补 explanation + 薄弱点按章节过滤——66 测试全绿,详见 HANDOVER-2026-08-23-B.md
- [x] **可观测性(2026-08-23 傍晚)**:LLM 调用日志(llm_logs 表 + `--usage` 命令,按环节聚合 token/耗时)——PLAN 8"多 Agent 效率"评估项落地;GitHub 发布(fenxidapao/FeynmanTutor);前端 weak_points 渲染修复——66 测试全绿,详见 HANDOVER-2026-08-23-B.md
- [ ] **C 阶段(下一窗口主线)**:Web 多人对照实验——前端按 group_name 自动定 mode(当前 app.js 硬编码 feynman),拉不熟 Python 的同学 n≥10,组间对比出"费曼 vs 讲解"数据
- [ ] **低优先(按需)**:贡献热力图(1.5,观感项) / TS 学习包(node 沙箱,性价比最低) / 爬合规语料(廖雪峰更多章节、Python 官方文档中文版 PSF) / 部署(Render/Railway,无简历增量先不做) / vision-exp(按需)

### 交接文档(2026-08-23 新增,新窗口必读)
- **docs/HANDOVER-2026-08-23.md**:完整交接——保留建议/可选项/已完成/踩坑/方向性建议/开工清单
- **docs/HANDOVER-2026-08-23-B.md**:本窗口(B 阶段+可观测性+GitHub)增量交接,含未完成清单
- 关键新决策:多课程选 SQL(判题机制差异化);DeepTutor 20k★ 调研(可检查记忆/掌握门槛/测验 explanation 三借鉴点);u0 数据已清空待重测
- 完整踩坑与决策流水:工作空间 .workbuddy/memory/2026-08-22.md、2026-08-23.md

## 16. 开工第一条命令(确认环境)

```bash
# 0. 环境注意(2026-08-23 踩坑):pytest/uvicorn/fastapi 只在 Anaconda;managed python 没有
#    pytest: /d/anacoda3/python.exe -m pytest tests/ -q   (项目 tests/ 有 __init__.py,防 site-packages 遮蔽)

# 1. 确认 DeepSeek key 可读(从 deep-research 复制 .env 或新建)
cp E:/AI 应用开发/agent/.env E:/AI 应用开发/FeynmanTutor/.env   # 只取 DEEPSEEK_* 三行

# 2. 确认 CourseRAG 服务在跑(讲解检索依赖它;没起则 notes 兜底,不影响主流程)
curl http://127.0.0.1:8000/health   # 若没起: cd CourseRAG && docker compose up -d

# 3. (2026-08-23 已建好) Web 服务与测试:
/d/anacoda3/python.exe -m uvicorn web.app:app --host 127.0.0.1 --port 8001   # Web Dashboard(浏览器打开 http://127.0.0.1:8001/)
/d/anacoda3/python.exe -m pytest tests/ -q                                   # 66 测试全绿
python main.py --learn sql --user u0                          # SQL 课程闭环(Python 同理)
python main.py --review python --user u0                      # 间隔复习
python main.py --usage                                        # LLM 调用统计(token/耗时,可观测性)

# 4. Git 提交(SSH 免密):git add -A && git commit -m "..." && git push origin main
```
