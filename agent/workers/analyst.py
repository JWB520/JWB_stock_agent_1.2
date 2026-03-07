"""分析师：纯逻辑推理，不挂载任何工具。"""
import json
import os

from openai import OpenAI
from dotenv import load_dotenv

from agent.schema import TaskContext

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

_SYSTEM = """你是一名身经百战的顶级游资操盘手，拥有20年A股实战经验，擅长解读龙虎榜资金意图与市场情绪。
你的任务是基于情报官提供的原始数据，输出一份深度复盘分析，必须严格包含以下三个章节：

## 一、市场情绪定性
对当日整体市场情绪（亢奋/分歧/低迷）给出明确定性，并说明判断依据。

## 二、核心阵眼逻辑
点出当日市场的核心主线题材与领涨龙头，分析其能否持续发酵。

## 三、龙虎榜资金拆解
对龙虎榜数据进行深度拆解，推演主力资金的真实意图（买入/出货/对倒），此章节不少于300字。

输出语言：简体中文，专业、直接、不废话。"""


def run(ctx: TaskContext, model: str = "deepseek-chat") -> None:
    raw = json.dumps(ctx.raw_data, ensure_ascii=False)
    resp = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"以下是今日原始数据，请开始分析：\n\n{raw}"},
        ],
        tools=[],
    )
    ctx.analysis_draft = resp.choices[0].message.content or ""
