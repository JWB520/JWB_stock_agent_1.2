"""AkShare 工具封装：SQLite 缓存 + 统一异常处理 + Function Calling Schema"""
import hashlib
import json
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any, Callable

import akshare as ak
import pandas as pd

from utils.data_cleaner import clean, to_markdown
from utils.logger import log_tool_call, log_tool_result

_DB = Path("logs/cache.db")


def _get_conn() -> sqlite3.Connection:
    _DB.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(_DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, expires_at REAL)"
    )
    return conn


def _cache_get(key: str) -> str | None:
    with closing(_get_conn()) as conn:
        row = conn.execute(
            "SELECT value FROM cache WHERE key=? AND expires_at>?", (key, time.time())
        ).fetchone()
    return row[0] if row else None


def _cache_set(key: str, value: str, ttl: int = 3600 * 8) -> None:
    with closing(_get_conn()) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache VALUES (?,?,?)", (key, value, time.time() + ttl)
        )
        conn.commit()


def _cache_key(func_name: str, kwargs: dict[str, Any]) -> str:
    raw = func_name + json.dumps(kwargs, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def _norm_date(date: str) -> str:
    """统一日期格式为 YYYYMMDD，剥离横杠、斜杠或中文字符"""
    return re.sub(r"\D", "", date)


def _safe_call(func: Callable, func_name: str, schema: str | None = None, **kwargs) -> dict:
    key = _cache_key(func_name, kwargs)
    if cached := _cache_get(key):
        return json.loads(cached)

    start = log_tool_call(func_name, kwargs)
    try:
        df = func(**kwargs)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            result = {"status": "no_data", "message": "当日无交易数据（可能为节假日或停牌）", "data": ""}
        else:
            # 先按 schema 剔除无用列和处理空值
            df = clean(df, schema)
            # 修复点：to_markdown 第二个参数是 max_rows，这里放宽到 50 行，防止丢失高标股信息
            result = {"status": "ok", "data": to_markdown(df, max_rows=50)}
            
        log_tool_result(func_name, start, result["status"])
        _cache_set(key, json.dumps(result, ensure_ascii=False))
        return result
    except Exception as e:
        msg = str(e)
        log_tool_result(func_name, start, "error", msg)
        if any(k in msg for k in ["无数据", "empty", "holiday", "停牌"]):
            return {"status": "no_data", "message": f"无交易数据: {msg}", "data": ""}
        return {"status": "error", "message": f"接口调用失败: {msg}", "data": ""}


def get_limit_up_pool(date: str) -> str:
    return json.dumps(_safe_call(ak.stock_zt_pool_em, "get_limit_up_pool", schema="limit_up", date=_norm_date(date)), ensure_ascii=False)


def get_dragon_tiger_list(date: str) -> str:
    d = _norm_date(date)
    return json.dumps(_safe_call(ak.stock_lhb_detail_em, "get_dragon_tiger_list", schema="dragon_tiger", start_date=d, end_date=d), ensure_ascii=False)


def get_stock_news(symbol: str) -> str:
    # 新闻数据不需要特定的 schema 裁剪，保持默认清洗即可
    return json.dumps(_safe_call(ak.stock_news_em, "get_stock_news", symbol=symbol), ensure_ascii=False)


def get_market_sentiment(date: str) -> str:
    return json.dumps(_safe_call(ak.stock_zt_pool_strong_em, "get_market_sentiment", date=_norm_date(date)), ensure_ascii=False)


TOOLS = [
    {"type": "function", "function": {"name": "get_limit_up_pool", "description": "获取A股指定日期涨停股池，含连板高度、涨停原因", "parameters": {"type": "object", "properties": {"date": {"type": "string", "description": "日期 YYYYMMDD"}}, "required": ["date"]}}},
    {"type": "function", "function": {"name": "get_dragon_tiger_list", "description": "获取龙虎榜游资席位买卖数据", "parameters": {"type": "object", "properties": {"date": {"type": "string", "description": "日期 YYYYMMDD"}}, "required": ["date"]}}},
    {"type": "function", "function": {"name": "get_stock_news", "description": "获取个股最新新闻，用于题材归因", "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "股票代码如 000001"}}, "required": ["symbol"]}}},
    {"type": "function", "function": {"name": "get_market_sentiment", "description": "获取市场情绪：强势股、连板股统计", "parameters": {"type": "object", "properties": {"date": {"type": "string", "description": "日期 YYYYMMDD"}}, "required": ["date"]}}},
]

TOOL_MAP = {
    "get_limit_up_pool": get_limit_up_pool,
    "get_dragon_tiger_list": get_dragon_tiger_list,
    "get_stock_news": get_stock_news,
    "get_market_sentiment": get_market_sentiment,
}