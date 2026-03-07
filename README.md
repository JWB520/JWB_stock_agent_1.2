# A股涨停板与游资逻辑复盘智能体

基于 DeepSeek + AkShare 的 A 股游资打板复盘智能体。通过 Function Calling 自动拉取涨停池、龙虎榜、市场情绪等数据，以顶级游资视角输出结构化复盘研报。

## 核心特性

- **Function Calling 循环**：自动编排多轮工具调用，熔断上限 5 次，防止无限循环
- **Token 压缩**：数据经 `data_cleaner` 按 schema 筛列 → 排序 → 压缩为 Markdown 表格，减少 80%+ Token 消耗
- **SQLite 缓存**：工具结果 TTL=8h 本地缓存，节假日/停牌返回 `no_data` 而非报错
- **多轮记忆**：Function Calling 中间消息（工具调用请求 + 结果）全部写入滑动窗口记忆，保证上下文连贯
- **人机协同**：Rich 终端交互，支持修改分析日期、校对研报、保存 Markdown 文件

## 项目结构

```
a-share-agent/
├── agent/
│   ├── core.py          # 主控智能体：Function Calling 循环 + 熔断 + 异常自愈
│   ├── memory.py        # 短期对话记忆（deque 滑动窗口，maxlen=20）
│   ├── prompts.py       # System Prompt（游资角色 + 四维分析框架）
│   ├── main.py          # Rich 终端交互入口，支持保存/修改研报
│   ├── router.py        # 指令路由：解析 → 分发子任务
│   └── workers/
│       ├── data_agent.py   # 数据拉取 + 清洗
│       └── write_agent.py  # Jinja2 模板组装研报 + LLM 填充
├── tools/
│   └── akshare_tools.py # AkShare 封装 + SQLite 缓存 + Function Calling Schema
├── utils/
│   ├── data_cleaner.py  # 按 schema 筛列 + 涨停池连板降序 + Markdown 压缩
│   └── logger.py        # INFO/DEBUG/ERROR 分级，终端 + 按天滚动文件
├── tests/
│   └── test_tools.py
├── logs/                # 运行日志 + SQLite 缓存（自动生成）
├── output/              # 研报 Markdown 输出
├── pyproject.toml
├── Dockerfile
└── .env.example
```

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

`.env` 字段说明：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 必填 |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |

### 2. 本地运行（PDM）

```bash
pdm install
pdm run python -m agent.main
```

### 3. Docker 运行

```bash
docker build -t a-share-agent .
docker run -it --env-file .env a-share-agent
```

### 4. 运行测试

```bash
pdm run pytest tests/ -v
```

## 架构说明

### 数据流转链路

```
LLM 发起 Tool Call
    → akshare_tools._safe_call()
        → AkShare 原始宽表 DataFrame
        → data_cleaner.clean(df, schema)   # 筛列 + 填充空值
        → data_cleaner.to_markdown(df, schema)  # 涨停池按连板降序 + 截断 50 行
    → Markdown 字符串写入 Tool Message
    → LLM 基于压缩数据生成分析
```

### 模块职责

| 模块 | 职责 |
|------|------|
| `agent/core.py` | Function Calling 循环，`max_iterations=5` 熔断，JSON 解析异常自愈，Token 消耗日志 |
| `agent/memory.py` | `deque(maxlen=20)` 滑动窗口，`append_raw()` 支持持久化中间消息对象 |
| `agent/prompts.py` | 游资角色 System Prompt，四维分析框架（情绪锚定/高标逻辑/龙虎榜解剖/次日推演） |
| `agent/main.py` | Rich 终端 UI，日期修改、研报校对、Markdown 保存至 `output/` |
| `tools/akshare_tools.py` | 4 个 Tool 封装，`closing()` 管理 SQLite 连接，`_norm_date()` 兼容 `YYYY-MM-DD` |
| `utils/data_cleaner.py` | `clean(schema)` 筛列，`to_markdown(schema, max_rows=50)` 压缩输出 |
| `utils/logger.py` | 工具耗时、LLM Token 消耗、错误堆栈，按天滚动写入 `logs/agent.log` |

### 可用工具（Function Calling）

| 工具名 | 数据源 | Schema | 说明 |
|--------|--------|--------|------|
| `get_limit_up_pool` | `stock_zt_pool_em` | `limit_up` | 涨停股池，按连续涨停降序 |
| `get_dragon_tiger_list` | `stock_lhb_detail_em` | `dragon_tiger` | 龙虎榜游资席位 |
| `get_market_sentiment` | `stock_zt_pool_strong_em` | — | 强势股/连板统计 |
| `get_stock_news` | `stock_news_em` | — | 个股新闻，用于题材归因 |

## 示例指令

```
复盘今天的涨停板，找出主线题材和最高连板股
分析 20240315 的龙虎榜，判断游资动向
帮我看看 000977 最近的新闻，判断题材持续性
```
