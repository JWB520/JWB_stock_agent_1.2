"""测试边界情况：无交易数据（节假日/停牌）、API异常"""
import json
from unittest.mock import patch
import pytest
from tools.akshare_tools import get_limit_up_pool, get_dragon_tiger_list, get_stock_news


def _parse(result: str) -> dict:
    return json.loads(result)


# ── 无交易数据（节假日）────────────────────────────────────────────────────────

def test_limit_up_pool_holiday():
    """节假日返回 no_data 而非崩溃"""
    with patch("tools.akshare_tools.ak.stock_zt_pool_em", side_effect=Exception("无数据")):
        r = _parse(get_limit_up_pool("20240101"))
    assert r["status"] == "no_data"
    assert r["data"] == []


def test_dragon_tiger_empty_df():
    """空 DataFrame 返回 no_data"""
    import pandas as pd
    with patch("tools.akshare_tools.ak.stock_lhb_detail_em", return_value=pd.DataFrame()):
        r = _parse(get_dragon_tiger_list("20240101"))
    assert r["status"] == "no_data"


# ── API 限流 ──────────────────────────────────────────────────────────────────

def test_api_rate_limit():
    """API 限流异常返回 error 状态，不崩溃"""
    with patch("tools.akshare_tools.ak.stock_zt_pool_em", side_effect=Exception("rate limit exceeded")):
        r = _parse(get_limit_up_pool("20240307"))
    assert r["status"] == "error"
    assert "接口调用失败" in r["message"]


# ── 正常数据 ──────────────────────────────────────────────────────────────────

def test_stock_news_truncated():
    """新闻只返回最多10条"""
    import pandas as pd
    fake = pd.DataFrame({"title": [f"news{i}" for i in range(20)]})
    with patch("tools.akshare_tools.ak.stock_news_em", return_value=fake):
        r = _parse(get_stock_news("000001"))
    assert r["status"] == "ok"
    assert len(r["data"]) <= 10
