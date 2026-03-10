"""翻译官：将用户口语化指令扩写为结构化 JSON 系统指令。"""
import json
import os

from openai import OpenAI
from dotenv import load_dotenv

from agent.schema import TaskContext
from utils.logger import logger

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

_SYSTEM = """你是一名A股指令解析专家。将用户的口语化指令解析为标准 JSON 结构化指令。

【输出格式（严格遵守）】
只输出合法 JSON 对象，禁止包含 ```json 标记、解释文字或任何额外内容。

{
  "target_assets": ["股票名称或代码列表，若为大盘分析则填 '大盘'"],
  "analysis_focus": ["从以下选项中选择：量价配合、情绪周期、基本面排雷、龙虎榜资金、事件驱动、盘前预案"],
  "required_data": ["从以下选项中选择：K线、龙虎榜、涨停池、个股新闻、财务数据"],
  "intent_summary": "一句话总结用户核心意图",
  "memory_action": "clear_all | forget_ticker | null",
  "forget_target": "当 memory_action=forget_ticker 时填入股票代码或名称，否则填 null"
}

【解析规则】
1. 提到具体股票名称/代码 → 填入 target_assets；只谈大盘/情绪/市场 → 填 ["大盘"]。
2. 提到"预案"/"明天"/"持仓" → analysis_focus 含"盘前预案"，required_data 含"K线"、"个股新闻"、"财务数据"。
3. 提到"复盘"/"今天"/"高标"/"连板" → required_data 含"龙虎榜"、"涨停池"。
4. 指令极度模糊 → 默认大盘情绪复盘。
5. 用户说"清空上下文"/"重新开始"/"忘了刚才" → memory_action="clear_all"。
6. 用户说"忘了XX股"/"不要XX的记忆"/"换个票" → memory_action="forget_ticker"，forget_target 填对应股票。
7. 无记忆操作意图 → memory_action=null，forget_target=null。"""


def run(ctx: TaskContext, model: str = "deepseek-chat") -> None:
    logger.info("翻译官开始解析指令：%s", ctx.user_instruction)
    resp = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": ctx.user_instruction},
        ],
        tools=[],
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        ctx.structured_instruction = json.loads(raw)
        logger.info("翻译官解析成功：%s", ctx.structured_instruction)
    except json.JSONDecodeError:
        logger.warning("翻译官输出非合法 JSON，降级使用原始指令。原始输出：%s", raw)
        ctx.structured_instruction = {"intent_summary": ctx.user_instruction, "_parse_error": raw}
