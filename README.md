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
连接 AkShare 工具链，通过 Function Calling 循环（最大迭代 **30 次**）精准提取数据。内置**智能分流纪律**：检测到持仓股名称时自动切换为个股深度调研模式（news + kline + fundamentals），仅在明确要求大盘复盘时才查龙虎榜/涨停池。内置**日期回溯机制**：遇到周末/节假日自动往前推日期重试，直到拿到真实盘面数据。

### 🧠 分析师 (Logic Engine) · `agent/workers/analyst.py`
纯逻辑大脑，`tools=[]` 硬性禁止工具调用。内置**动态分析纪律**：优先读取用户操盘指令，持仓预案模式下全力推演个股策略（高开/低开/均线防守），大盘复盘模式下输出情绪周期与龙虎榜拆解。当传入 K 线/财务数据时，自动追加**量价配合分析**与**股性基因诊断**板块。强制 CoT 深度展开，每股推演不少于 800 字。

### ⚖️ 风控总监 (Risk Judge) · `agent/workers/judge.py`
引入 Actor-Critic 对抗博弈机制。逐条针对分析师长篇底稿进行字斟句酌的反驳，挖出流动性陷阱、恶庄席位历史劣迹、宏观情绪退潮时的连环踩踏风险，篇幅不受限制。

### ✍️ 主编 (Lead Editor) · `agent/workers/editor.py`
无损排版：原样保留分析师底稿与风控点评的全部内容，套用 Markdown 多级标题模板，附加免责声明，输出最终研报。

---

## 数据流转

```
TaskContext (agent/schema.py)
├── user_instruction   ← 用户原始指令
├── raw_data           ← Scout 写入（工具调用原始 JSON）
├── analysis_draft     ← Analyst 写入（深度分析底稿）
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
│   ├── main.py              # 终端交互入口
│   └── workers/
│       ├── scout.py         # 情报官：Function Calling 数据抓取 + 智能分流
│       ├── analyst.py       # 分析师：动态全栈推演，禁止工具调用
│       ├── judge.py         # 风控总监：深度扒皮，鞭辟入里
│       └── editor.py        # 主编：无损排版 + 免责声明
├── tools/
│   └── akshare_tools.py     # AkShare 封装 + SQLite 缓存 + FC Schema
│                            # 工具：涨停池/龙虎榜/个股新闻/K线/基本面
├── utils/
│   ├── data_cleaner.py      # 按 schema 筛列 + Markdown 压缩
│   └── logger.py            # 分级日志，按天滚动写入
├── tests/
│   └── test_tools.py
├── logs/                    # 运行日志 + SQLite 缓存（自动生成，已 gitignore）
├── output/                  # 研报 Markdown 输出（已 gitignore）
├── pyproject.toml
├── Dockerfile
├── .env.example
└── .env                     # 本地密钥（已 gitignore，切勿上传）
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

## 可用工具 (Function Calling)

| 工具名 | 数据源 | 说明 |
|--------|--------|------|
| `get_limit_up_pool` | `stock_zt_pool_em` | 涨停股池，按连续涨停降序 |
| `get_dragon_tiger_list` | `stock_lhb_detail_em` | 龙虎榜游资席位 |
| `get_market_sentiment` | `stock_zt_pool_strong_em` | 强势股/连板统计 |
| `get_stock_news` | `stock_news_em` | 个股新闻，用于题材归因 |
| `get_stock_kline` | `stock_zh_a_hist` | 个股近期K线与量价数据 |
| `get_stock_fundamentals` | `stock_individual_info_em` | 总市值、流通市值、总股本等基本面 |

---

## ⚠️ 免责声明 (Disclaimer)

**本系统输出仅供代码学习与 AI 逻辑推演，绝不构成任何投资建议，股市有风险，打板需谨慎。**
