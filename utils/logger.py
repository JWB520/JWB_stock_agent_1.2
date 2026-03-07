"""可观测日志模块：分级输出，按天滚动写入 logs/ 目录"""
import logging
import time
import traceback
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any


def _build_logger(name: str = "agent") -> logging.Logger:
    Path("logs").mkdir(exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # 终端 handler（INFO+）
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)

    # 文件 handler（DEBUG+，按天滚动，保留7天）
    fh = TimedRotatingFileHandler("logs/agent.log", when="midnight", backupCount=7, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger


logger = _build_logger()


def log_llm_request(messages: list[dict], tools: list | None = None) -> None:
    logger.debug("LLM Request | messages=%d tools=%s", len(messages), [t["function"]["name"] for t in (tools or [])])


def log_llm_response(content: str | None, tool_calls: list | None) -> None:
    if tool_calls:
        logger.info("LLM → ToolCall: %s", [tc.function.name for tc in tool_calls])
    else:
        logger.debug("LLM Response | len=%d", len(content or ""))


def log_tool_call(name: str, args: dict[str, Any]) -> float:
    logger.info("Tool [%s] args=%s", name, args)
    return time.perf_counter()


def log_tool_result(name: str, start: float, status: str, error: str | None = None) -> None:
    elapsed = (time.perf_counter() - start) * 1000
    if error:
        logger.error("Tool [%s] FAILED in %.1fms | %s\n%s", name, elapsed, error, traceback.format_exc())
    else:
        logger.info("Tool [%s] OK in %.1fms | status=%s", name, elapsed, status)
