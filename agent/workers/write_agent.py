"""write_agent：用 Jinja2 + settings.yaml 模板组装研报，调用 LLM 填充分析内容"""
import os
from datetime import datetime

import yaml
from jinja2 import Template
from openai import OpenAI

from agent.prompts import SYSTEM_PROMPT
from utils.logger import log_llm_request, log_llm_response

_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

with open("settings.yaml", encoding="utf-8") as f:
    _cfg = yaml.safe_load(f)


def run(data: dict[str, str], model: str | None = None) -> str:
    model = model or _cfg.get("model", "deepseek-chat")
    prompt = (
        f"以下是{data['date']}的市场数据，请按游资逻辑撰写龙头逻辑归因与操作建议：\n\n"
        f"**市场情绪**\n{data['sentiment']}\n\n"
        f"**涨停股池**\n{data['limit_up_table']}\n\n"
        f"**龙虎榜**\n{data['dragon_tiger_table']}"
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
    log_llm_request(messages)
    resp = _client.chat.completions.create(model=model, messages=messages)
    msg = resp.choices[0].message
    log_llm_response(msg.content, None)

    analysis, _, suggestion = (msg.content or "").partition("## 五、操作建议")
    ctx = {
        **data,
        "top_n": _cfg.get("top_n", 20),
        "analysis": analysis.strip(),
        "suggestion": suggestion.strip() or "见上文分析",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    return Template(_cfg["report"]["template"]).render(**ctx)
