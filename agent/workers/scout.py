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

【智能日期回溯机制（极度重要）】
1. 你的任务是必须拿到真实的盘面数据！如果在调用工具时，返回结果包含 'no_data' 或 '当日无交易数据'，说明你查询的这一天是周末或法定节假日（A股休市）。
2. 此时，**绝对不允许**你直接停止工作或向用户报告查无数据！
3. 你必须根据系统注入的当前时间，自行在脑海中将日期往前推导 1 到 3 天（例如：周日就推到周五，节假日就继续往前推），并使用新的日期**再次调用工具**。
4. 你有最多 5 次调用工具的机会，不断往前试探，直到工具成功返回包含真实股票名称的 JSON/Markdown 数据为止！只有成功拿到数据后，你才能结束思考并将数据写入 raw_data。"""


def run(ctx: TaskContext, model: str = "deepseek-chat") -> None:
    curr_time = __import__("datetime").datetime.now().strftime("%Y年%m月%d日，星期%w")
    messages = [
        {"role": "system", "content": f"【系统时间注入：今天是 {curr_time}】\n" + _SYSTEM},
        {"role": "user", "content": ctx.user_instruction},
    ]

    for _ in range(8):
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
