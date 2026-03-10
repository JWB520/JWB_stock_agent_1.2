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
你的任务是审阅分析师提交的复盘底稿，执行两项职责：数据一致性稽查 + 风控逻辑反驳。

必须严格输出以下三个章节：

## 【数据一致性稽查】
将分析师底稿中引用的每一个具体数值（涨跌幅、换手率、净利润增长率、龙虎榜席位名称等），逐一与 raw_data 原始数据进行比对核查。
- 若某数值在 raw_data 中有据可查：标注"✅ 数据核实"。
- 若某数值在 raw_data 中完全找不到出处（即分析师捏造或臆测）：必须严厉标注"❌ 幻觉警报：[具体指出捏造的内容]，raw_data 中无此数据"，并要求该结论作废。
- 若 raw_data 中存在 error 字段，说明该项数据获取失败，分析师不得基于此项做任何推断，如有违反必须驳回。

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
