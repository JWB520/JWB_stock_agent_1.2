"""data_agent：负责调用工具链拉取并清洗数据，返回结构化 Markdown 表格"""
import json
from datetime import datetime

import pandas as pd

from tools.akshare_tools import get_dragon_tiger_list, get_limit_up_pool, get_market_sentiment
from utils.data_cleaner import clean, to_markdown


def run(date: str | None = None) -> dict[str, str]:
    date = date or datetime.now().strftime("%Y%m%d")

    def _parse(raw: str, schema: str) -> str:
        r = json.loads(raw)
        if r["status"] != "ok" or not r["data"]:
            return r.get("message", "暂无数据")
        return to_markdown(clean(pd.DataFrame(r["data"]), schema))

    return {
        "date": date,
        "sentiment": _parse(get_market_sentiment(date), "limit_up"),
        "limit_up_table": _parse(get_limit_up_pool(date), "limit_up"),
        "dragon_tiger_table": _parse(get_dragon_tiger_list(date), "dragon_tiger"),
    }
