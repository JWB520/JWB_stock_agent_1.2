"""金融数据清洗：剔除无用列、处理缺失值、压缩为极简 Markdown 表格"""
import pandas as pd

_KEEP_COLS = {
    "limit_up": ["代码", "名称", "涨停原因类别", "连续涨停", "涨停时间", "流通市值"],
    "dragon_tiger": ["股票代码", "股票名称", "解读", "净额", "买入额", "卖出额", "上榜原因"],
}


def clean(df: pd.DataFrame, schema: str | None = None) -> pd.DataFrame:
    df = df.dropna(axis=1, how="all")
    if schema and (cols := _KEEP_COLS.get(schema)):
        df = df[[c for c in cols if c in df.columns]]
    df = df.fillna("—")
    return df.reset_index(drop=True)


def to_markdown(df: pd.DataFrame, schema: str | None = None, max_rows: int = 50) -> str:
    """压缩为极简 Markdown 表格；涨停池优先按连续涨停降序排列"""
    if schema == "limit_up" and "连续涨停" in df.columns:
        df = df.sort_values("连续涨停", ascending=False)
    df = df.head(max_rows)
    header = " | ".join(df.columns)
    sep = " | ".join(["---"] * len(df.columns))
    rows = "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False))
    return f"| {header} |\n| {sep} |\n{rows}"
