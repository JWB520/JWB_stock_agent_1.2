"""情报官：唯一拥有工具调用权限的 Agent，负责数据抓取。"""
import json
import os

from openai import OpenAI
from dotenv import load_dotenv

from agent.schema import TaskContext
from tools.akshare_tools import TOOL_MAP, TOOLS

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

_SYSTEM = """你是一名A股数据情报官。根据用户指令，调用工具获取所需数据，拿到足够数据后立即停止工具调用。

【智能分流纪律（极度重要）】
1. 意图识别：如果用户指令中包含明确的【持仓股票名称】（如东方电气、华宝油气等），说明用户需要个股盘前预案！
2. 动作分支：此时你**绝对不要**去调用 `get_dragon_tiger_list` 或涨停池去查大盘！你必须直接调用 `get_stock_news` 或相关的个股工具，精准获取这几只持仓股的情报，拿到后立刻结束循环。
3. 只有当用户明确要求"复盘大盘/情绪/高标"时，才允许去查龙虎榜和涨停池。
4. 按需深度调研：当用户询问【具体的持仓个股】或要求【盘前预案/深度分析】时，你不仅要调用 `get_stock_news`，还必须**视情况主动调用** `get_stock_kline`（了解近期量价配合与股性）和 `get_stock_fundamentals`（了解盘子大小和基本面）。
5. 极简原则：如果用户只是问"今天大盘怎样"或"最高连板是谁"，绝对不要调用 K 线和财务工具！

【智能日期回溯机制（极度重要）】
1. 你的任务是必须拿到真实的盘面数据！如果在调用工具时，返回结果包含 'no_data' 或 '无数据'，说明你查询的这一天是周末或法定节假日（A股休市）。
2. 此时，**绝对不允许**你直接停止工作或向用户报告查无数据！
3. 你必须根据系统注入的当前时间，自行在脑海中将日期往前推导 1 到 3 天（例如：周日就推到周五，节假日就继续往前推），并使用新的日期**再次调用工具**。
4. 你有最多 30 次调用工具的机会，不断往前试探，直到工具成功返回包含真实股票名称的 JSON/Markdown 数据为止！只有成功拿到数据后，你才能结束思考并将数据写入 raw_data。
5. 你现在拥有充足的算力与调用次数。面对多只股票的深度调研任务，不要急于返回！你必须把每一只股票的新闻（news）、K线（kline）、基本面（fundamentals）全部查得清清楚楚。哪怕需要调用 15 次工具，也必须确保情报绝对完整后，再结束循环。"""


def run(ctx: TaskContext, model: str = "deepseek-chat") -> None:
    curr_time = __import__("datetime").datetime.now().strftime("%Y年%m月%d日，星期%w")
    messages = [
        {"role": "system", "content": f"【系统时间注入：今天是 {curr_time}】\n" + _SYSTEM},
        {"role": "user", "content": ctx.user_instruction},
    ]

    for _ in range(30):
        resp = _client.chat.completions.create(
            model=model, messages=messages, tools=TOOLS, tool_choice="auto"
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            break

        messages.append(msg)
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            result = TOOL_MAP[tc.function.name](**args) if tc.function.name in TOOL_MAP else "{}"
            ctx.raw_data[tc.function.name] = result
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
