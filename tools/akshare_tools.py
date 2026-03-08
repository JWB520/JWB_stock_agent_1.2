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
            result = {"status": "no_data", "message": "盘面无数据(大概率周末/休市)，请务必将日期往前推1天重试！", "data": ""}
        else:
            df = clean(df, schema)
            result = {"status": "ok", "data": to_markdown(df, max_rows=50)}
        log_tool_result(func_name, start, result["status"])
        _cache_set(key, json.dumps(result, ensure_ascii=False))
        return result
    except TypeError as e:
        msg = str(e)
        log_tool_result(func_name, start, "no_data", msg)
        return {"status": "no_data", "message": "周末无数据触发底层TypeError，请务必将日期往前推1天重试！", "data": ""}
    except Exception as e:
        msg = str(e)
        log_tool_result(func_name, start, "no_data", msg)
        return {"status": "no_data", "message": f"接口异常(可能休市): {msg}，请往前推1天重试！", "data": ""}


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


def get_stock_kline(symbol: str, days: int = 20) -> str:
    key = _cache_key("get_stock_kline", {"symbol": symbol, "days": days})
    if cached := _cache_get(key):
        return cached
    start = log_tool_call("get_stock_kline", {"symbol": symbol, "days": days})
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
        if df is None or df.empty:
            return json.dumps({"status": "no_data", "message": "无K线数据"}, ensure_ascii=False)
        col_map = {"日期": "日期", "开盘": "开盘", "收盘": "收盘", "最高": "最高", "最低": "最低",
                   "成交量": "成交量", "成交额": "成交额", "换手率": "换手率", "涨跌幅": "涨跌幅"}
        df = df[[c for c in col_map if c in df.columns]].tail(days)
        result = {"status": "ok", "data": df.to_markdown(index=False)}
        log_tool_result("get_stock_kline", start, "ok")
        _cache_set(key, json.dumps(result, ensure_ascii=False))
        return json.dumps(result, ensure_ascii=False)
    except TypeError as e:
        log_tool_result("get_stock_kline", start, "no_data", str(e))
        return json.dumps({"status": "no_data", "message": "周末无数据，请往前推1天重试！"}, ensure_ascii=False)
    except Exception as e:
        log_tool_result("get_stock_kline", start, "no_data", str(e))
        return json.dumps({"status": "no_data", "message": f"接口异常: {e}"}, ensure_ascii=False)


def get_stock_fundamentals(symbol: str) -> str:
    key = _cache_key("get_stock_fundamentals", {"symbol": symbol})
    if cached := _cache_get(key):
        return cached
    start = log_tool_call("get_stock_fundamentals", {"symbol": symbol})
    try:
        df = ak.stock_individual_info_em(symbol=symbol)
        if df is None or df.empty:
            return json.dumps({"status": "no_data", "message": "无基本面数据"}, ensure_ascii=False)
        data = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
        result = {"status": "ok", "data": data}
        log_tool_result("get_stock_fundamentals", start, "ok")
        _cache_set(key, json.dumps(result, ensure_ascii=False))
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log_tool_result("get_stock_fundamentals", start, "error", str(e))
        return json.dumps({"status": "error", "message": f"接口异常: {e}"}, ensure_ascii=False)


TOOLS = [
    {"type": "function", "function": {"name": "get_limit_up_pool", "description": "获取A股指定日期涨停股池，含连板高度、涨停原因", "parameters": {"type": "object", "properties": {"date": {"type": "string", "description": "日期 YYYYMMDD"}}, "required": ["date"]}}},
    {"type": "function", "function": {"name": "get_dragon_tiger_list", "description": "获取龙虎榜游资席位买卖数据", "parameters": {"type": "object", "properties": {"date": {"type": "string", "description": "日期 YYYYMMDD"}}, "required": ["date"]}}},
    {"type": "function", "function": {"name": "get_stock_news", "description": "获取个股最新新闻，用于题材归因", "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "股票代码如 000001"}}, "required": ["symbol"]}}},
    {"type": "function", "function": {"name": "get_market_sentiment", "description": "获取市场情绪：强势股、连板股统计", "parameters": {"type": "object", "properties": {"date": {"type": "string", "description": "日期 YYYYMMDD"}}, "required": ["date"]}}},
    {"type": "function", "function": {"name": "get_stock_kline", "description": "获取个股近期K线与量价数据，用于分析技术面和股性", "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "股票代码如 000001"}, "days": {"type": "integer", "description": "获取最近N天，默认20"}}, "required": ["symbol"]}}},
    {"type": "function", "function": {"name": "get_stock_fundamentals", "description": "获取个股基本面与财务摘要，含总市值、流通市值、总股本等", "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "股票代码如 000001"}}, "required": ["symbol"]}}},
]

TOOL_MAP = {
    "get_limit_up_pool": get_limit_up_pool,
    "get_dragon_tiger_list": get_dragon_tiger_list,
    "get_stock_news": get_stock_news,
    "get_market_sentiment": get_market_sentiment,
    "get_stock_kline": get_stock_kline,
    "get_stock_fundamentals": get_stock_fundamentals,
}