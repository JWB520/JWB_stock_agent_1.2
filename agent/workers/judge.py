"""风控总监：纯逻辑评判，不调用任何工具。"""
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

_SYSTEM = """你是一位极其冷酷、挑剔的游资风控总监，拥有丰富的A股短线打板、游资接力和事件驱动策略风控经验。
你的任务是审阅分析师提交的复盘底稿，重点打击致命漏洞。

必须严格输出以下两个章节：

## 【推演亮点】
列出底稿中哪些逻辑非常契合游资打法，言简意赅。

## 【致命盲区/风险】
列出底稿中的致命漏洞，例如：无视恶庄席位抛压、情绪退潮期盲目看多、强凑事件驱动逻辑等。每条风险必须有数据支撑。

【深度扒皮纪律】
不要只写一两句简单的警告。你必须逐条针对分析师的长篇底稿进行字斟句酌的反驳。挖出深层的流动性陷阱、恶庄席位历史操盘劣迹、以及宏观情绪退潮时的连环踩踏风险。你的批判报告篇幅同样不受限制，必须鞭辟入里，充满压迫感。

语气：冷酷、直接、不留情面。"""


def run(ctx: TaskContext, model: str = "deepseek-chat") -> None:
    payload = json.dumps(
        {"raw_data": ctx.raw_data, "analysis_draft": ctx.analysis_draft},
        ensure_ascii=False,
    )
    resp = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"请审阅以下材料：\n\n{payload}"},
        ],
        tools=[],
    )
    ctx.critique = resp.choices[0].message.content or ""
