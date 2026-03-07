# A-Share Multi-Agent System 🚀
### 红岭路一号游资投研组

> 基于 DeepSeek + AkShare 的全自动 A 股短线复盘多智能体系统。四个专职 Agent 流水线协作，从原始数据到带风控点评的结构化研报，一气呵成。

---

## 核心架构 (Workflow)

```
用户指令
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Orchestrator  (agent/orchestrator.py)              │
│                                                     │
│  🕵️  Scout ──► 🧠 Analyst ──► ⚖️ Judge ──► ✍️ Editor │
└─────────────────────────────────────────────────────┘
    │
    ▼
  📄 final_report (Markdown 研报)
```

### 🕵️ 情报官 (Data Scout) · `agent/workers/scout.py`
连接 AkShare 工具链，通过 Function Calling 循环（最大迭代 5 次）精准提取涨停池、龙虎榜、市场情绪数据，经 Pandas 数据降维清洗后写入 `TaskContext.raw_data`。拿到足够数据立即熔断，不做无效调用。

### 🧠 分析师 (Logic Engine) · `agent/workers/analyst.py`
纯逻辑大脑，`tools=[]` 硬性禁止工具调用。基于情报官提供的底层数据，以顶级游资视角推演市场情绪周期、核心阵眼逻辑，并对龙虎榜资金意图进行不少于 300 字的深度拆解。

### ⚖️ 风控总监 (Risk Judge) · `agent/workers/judge.py`
引入 Actor-Critic 对抗博弈机制。冷酷审阅分析师底稿，重点针对 A 股短线打板、游资接力、事件驱动策略中的致命漏洞进行无情挑刺——揭示退潮风险、恶庄席位隐患、强凑逻辑等盲区，结果写入 `TaskContext.critique`。

### ✍️ 主编 (Lead Editor) · `agent/workers/editor.py`
内容拼装与 Markdown 专业排版。将分析师底稿与风控总监点评合并，套用标准模板，附加免责声明，输出最终研报至 `TaskContext.final_report`。

---

## 数据流转

```
TaskContext (agent/schema.py)
├── user_instruction   ← 用户原始指令
├── raw_data           ← Scout 写入（工具调用原始 JSON）
├── analysis_draft     ← Analyst 写入（三章节深度分析）
├── critique           ← Judge 写入（推演亮点 + 致命盲区）
└── final_report       ← Editor 写入（最终 Markdown 研报）
```

---

## 项目结构

```
a-share-agent/
├── agent/
│   ├── orchestrator.py      # 主编排器：调度四段式流水线
│   ├── schema.py            # TaskContext：Agent 间共享上下文
│   ├── memory.py            # 短期对话记忆（deque 滑动窗口）
│   ├── prompts.py           # System Prompt
│   ├── main.py              # 终端交互入口
│   ├── core_v1_backup.py    # 旧版单体 Agent 备份
│   └── workers/
│       ├── scout.py         # 情报官：Function Calling 数据抓取
│       ├── analyst.py       # 分析师：纯推理，禁止工具调用
│       ├── judge.py         # 风控总监：对抗审阅，挑出致命盲区
│       └── editor.py        # 主编：排版 + 风控点评 + 免责声明
├── tools/
│   └── akshare_tools.py     # AkShare 封装 + SQLite 缓存 + FC Schema
├── utils/
│   ├── data_cleaner.py      # 按 schema 筛列 + Markdown 压缩
│   └── logger.py            # 分级日志，按天滚动写入
├── tests/
│   └── test_tools.py
├── logs/                    # 运行日志 + SQLite 缓存（自动生成）
├── output/                  # 研报 Markdown 输出
├── pyproject.toml
├── Dockerfile
├── .env.example
└── .env
```

---

## 快速开始 (Quick Start)

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY
```

### 2. 安装依赖（PDM）

```bash
pdm install
```

### 3. 启动系统

```bash
python -m agent.main
```

### 4. 运行测试

```bash
pdm run pytest tests/ -v
```

### Docker

```bash
docker build -t a-share-agent .
docker run -it --env-file .env a-share-agent
```

---

## 交互演示 (Demo)

**用户输入：**
```
分析昨日高标股
```

**系统输出研报结构：**
```markdown
# 📊 A股深度复盘研报 · 2026年03月07日

> ⚠️ 免责声明：本报告由AI多智能体系统自动生成，仅供学习研究参考，不构成任何投资建议。

---

## 一、市场情绪定性
昨日市场整体情绪偏亢奋，涨停家数 87 只，连板率 34%...

## 二、核心阵眼逻辑
主线题材聚焦 AI 算力方向，龙头 XXX 实现 3 连板...

## 三、龙虎榜资金拆解
龙虎榜数据显示，宁波游资席位合计净买入 2.3 亿，
其中"宁波解放南路"单席位买入 8700 万，结合其历史
打板风格判断为趋势追击型资金，非出货行为...（300字+）

---

## 🚨 风控总监点评

### 【推演亮点】
- 情绪定性与连板率数据高度吻合，逻辑自洽

### 【致命盲区/风险】
- 忽视了龙虎榜中"东方财富证券拉萨团结路"席位的历史出货记录
- 当前情绪处于高位第3天，历史回测显示此阶段做多胜率骤降至 38%

---
*由 A股多智能体研究组（情报官→分析师→风控总监→主编）联合出品*
```

---

## 可用工具 (Function Calling)

| 工具名 | 数据源 | 说明 |
|--------|--------|------|
| `get_limit_up_pool` | `stock_zt_pool_em` | 涨停股池，按连续涨停降序 |
| `get_dragon_tiger_list` | `stock_lhb_detail_em` | 龙虎榜游资席位 |
| `get_market_sentiment` | `stock_zt_pool_strong_em` | 强势股/连板统计 |
| `get_stock_news` | `stock_news_em` | 个股新闻，用于题材归因 |

---

## ⚠️ 免责声明 (Disclaimer)

**本系统输出仅供代码学习与 AI 逻辑推演，绝不构成任何投资建议，股市有风险，打板需谨慎。**
