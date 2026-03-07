from collections import deque
from typing import Optional


class Memory:
    """短期对话记忆，维持滑动窗口上下文"""

    def __init__(self, max_turns: int = 10):
        self._history: deque = deque(maxlen=max_turns * 2)

    def add(self, role: str, content: str):
        self._history.append({"role": role, "content": content})

    def append_raw(self, msg) -> None:
        """追加任意消息对象（dict 或 ChatCompletionMessage）"""
        self._history.append(msg)

    def get(self) -> list:
        return list(self._history)

    def clear(self):
        self._history.clear()
