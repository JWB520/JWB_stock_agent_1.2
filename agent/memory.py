"""结构化对话记忆管理模块。"""
import time
from dataclasses import dataclass, field
from typing import Any

# 粗估 token：字符数 / 2（中英混合折中）
_CHARS_PER_TOKEN = 2
# assistant 消息超过此字符数时硬截断，防止历史挤占推理空间
_TRUNCATE_CHARS = 1600


@dataclass
class MemoryMessage:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    # 约定键：tickers: list[str], topic: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryManager:
    """结构化记忆管理器，支持按 ticker/topic 精准召回与删除。"""

    def __init__(self) -> None:
        self._messages: list[MemoryMessage] = []
        self._ticker_index: dict[str, set[int]] = {}  # ticker → 消息位置集合

    # ------------------------------------------------------------------ #
    # 写入
    # ------------------------------------------------------------------ #
    def add_memory(self, msg: MemoryMessage) -> None:
        """追加记忆并更新 ticker 索引。"""
        if msg.role == "assistant" and len(msg.content) > _TRUNCATE_CHARS:
            msg.content = msg.content[:_TRUNCATE_CHARS] + "…[已截断]"

        idx = len(self._messages)
        self._messages.append(msg)
        for ticker in msg.metadata.get("tickers", []):
            self._ticker_index.setdefault(ticker, set()).add(idx)

    def add(self, role: str, content: str) -> None:
        """兼容 core.py 旧接口。"""
        self.add_memory(MemoryMessage(role=role, content=content))

    def append_raw(self, msg: Any) -> None:
        """兼容 dict 或 ChatCompletionMessage 对象（core.py 工具调用链路）。"""
        if isinstance(msg, dict):
            role, content = msg.get("role", "tool"), str(msg.get("content") or "")
        else:
            role, content = getattr(msg, "role", "assistant"), str(getattr(msg, "content") or "")
        self.add_memory(MemoryMessage(role=role, content=content))

    # ------------------------------------------------------------------ #
    # 读取
    # ------------------------------------------------------------------ #
    def get(self) -> list[dict]:
        """返回全部消息（OpenAI 格式）。"""
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def get_context(self, max_tokens: int = 4000) -> list[dict]:
        """从最新消息往前累加，返回不超过 max_tokens 的上下文列表。"""
        budget = max_tokens * _CHARS_PER_TOKEN
        result: list[dict] = []
        for msg in reversed(self._messages):
            budget -= len(msg.content)
            if budget < 0:
                break
            result.append({"role": msg.role, "content": msg.content})
        result.reverse()
        return result

    def get_context_by_topic(self, query: str) -> list[dict]:
        """按 ticker 或 topic 关键词精准召回相关记忆。"""
        q = query.lower()
        matched = [
            m for m in self._messages
            if q in [t.lower() for t in m.metadata.get("tickers", [])]
            or q in m.metadata.get("topic", "").lower()
        ]
        return [{"role": m.role, "content": m.content} for m in matched]

    # ------------------------------------------------------------------ #
    # 删除 / 修剪
    # ------------------------------------------------------------------ #
    def clear_all(self) -> None:
        self._messages.clear()
        self._ticker_index.clear()

    def delete_by_ticker(self, ticker: str) -> int:
        """删除与指定股票相关的全部记忆，返回删除条数。"""
        indices = self._ticker_index.pop(ticker, set())
        if not indices:
            return 0
        self._messages = [m for i, m in enumerate(self._messages) if i not in indices]
        self._rebuild_index()
        return len(indices)

    def prune_oldest(self, keep_last_n: int) -> None:
        """仅保留最新的 keep_last_n 条记忆。"""
        if len(self._messages) > keep_last_n:
            self._messages = self._messages[-keep_last_n:]
            self._rebuild_index()

    def _rebuild_index(self) -> None:
        self._ticker_index.clear()
        for idx, msg in enumerate(self._messages):
            for ticker in msg.metadata.get("tickers", []):
                self._ticker_index.setdefault(ticker, set()).add(idx)


# 向后兼容别名：core.py 中 `from agent.memory import Memory` 无需改动
Memory = MemoryManager
