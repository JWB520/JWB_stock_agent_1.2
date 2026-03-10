# A-Share Multi-Agent System 🚀
### 红岭路一号游资投研组

> 基于 DeepSeek + AkShare 的全自动 A 股短线复盘多智能体系统。五个专职 Agent 流水线协作，从原始指令到带风控点评的结构化研报，一气呵成。

---

## 核心架构 (Workflow)

```
用户指令
    │
    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Orchestrator  (agent/orchestrator.py)                               │
│                                                                      │
│  🗣️ Translator ──► 🕵️ Scout ──► 🧠 Analyst ──► ⚖️ Judge ──► ✍️ Editor │
└──────────────────────────────────────────────────────────────────────┘
    │
    ▼
  📄 final_report (Markdown 研报)
```

### 🗣️ 翻译官 (Instruction Translator) · `agent/workers/translator.py`
流水线第一关。将用户口语化、模糊的指令（如"看看赛力斯"）扩写并解析为标准 JSON 结构化指令，包含 `target_assets`（目标标的）、`analysis_focus`（分析侧重点）、`required_data`（需调用的数据工具）、`intent_summary`（意图摘要）四个字段，向下游精准投喂。内置 JSON 解析失败的降级兜底，确保流水线不中断。

### 🕵️ 情报官 (Data Scout) · `agent/workers/scout.py`
连接 AkShare 工具链，通过 Function Calling 循环（最大迭代 **30 次**）精准提取数据。内置**智能分流纪律**：检测到持仓股名称时自动切换为个股深度调研模式（news + kline + fundamentals），仅在明确要求大盘复盘时才查龙虎榜/涨停池。内置**日期回溯机制**：遇到周末/节假日自动往前推日期重试。**工具调用失败时强制写入 `{"error": "...真实数据为空"}` 到 `raw_data`，严禁静默跳过。**

### 🧠 分析师 (Logic Engine) · `agent/workers/analyst.py`
纯逻辑大脑，`tools=[]` 硬性禁止工具调用。内置**反幻觉铁律**：只能基于传入的 `raw_data` 推演，缺数据必须声明"无法评估"，每个引用数字必须有原始出处，严禁捏造任何数值、日期或走势。持仓预案模式下全力推演个股策略，大盘复盘模式下输出情绪周期与龙虎榜拆解。强制 CoT 深度展开，每股推演不少于 800 字。

### ⚖️ 风控总监 (Risk Judge) · `agent/workers/judge.py`
双重职责：**① 数据一致性稽查**——逐一比对分析师引用的每个数值与 `raw_data` 原始数据，捏造数据标注 `❌ 幻觉警报` 并要求结论作废；**② 风控逻辑反驳**——挖出流动性陷阱、恶庄席位历史劣迹、宏观情绪退潮时的连环踩踏风险，篇幅不受限制。

### ✍️ 主编 (Lead Editor) · `agent/workers/editor.py`
无损排版：原样保留分析师底稿与风控点评的全部内容，套用 Markdown 多级标题模板，附加免责声明，输出最终研报。

---

## 数据流转

```
TaskContext (agent/schema.py)
├── user_instruction        ← 用户原始指令
├── structured_instruction  ← Translator 写入（结构化 JSON 指令）
├── raw_data                ← Scout 写入（工具调用原始 JSON，失败时含 error 字段）
├── analysis_draft          ← Analyst 写入（深度分析底稿）
├── critique                ← Judge 写入（数据稽查 + 推演亮点 + 致命盲区）
└── final_report            ← Editor 写入（最终 Markdown 研报）
```

---

## 项目结构

```
a-share-agent/
├── agent/
│   ├── orchestrator.py      # 主编排器：调度五段式流水线
│   ├── schema.py            # TaskContext：Agent 间共享上下文
│   ├── memory.py            # 短期对话记忆（deque 滑动窗口）
│   ├── main.py              # 终端交互入口
│   └── workers/
│       ├── translator.py    # 翻译官：口语指令 → 结构化 JSON
│       ├── scout.py         # 情报官：Function Calling 数据抓取 + 错误显式上报
│       ├── analyst.py       # 分析师：反幻觉铁律 + 动态全栈推演
│       ├── judge.py         # 风控总监：数据一致性稽查 + 深度扒皮
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
