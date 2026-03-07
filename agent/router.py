"""主控路由：解析用户指令，分发至 data_agent 或 write_agent"""
import re
from agent.workers import data_agent, write_agent


def route(instruction: str, date: str | None = None) -> str:
    """
    路由规则：
    - 含"数据"/"拉取"/"获取" → 仅运行 data_agent
    - 含"研报"/"复盘"/"分析"/"撰写" → data_agent + write_agent
    - 其他 → 直接返回提示
    """
    instr = instruction.lower()
    is_write = bool(re.search(r"研报|复盘|分析|撰写|总结", instr))
    is_data = bool(re.search(r"数据|拉取|获取|查询", instr))

    if is_write or (not is_data and not is_write):
        data = data_agent.run(date)
        return write_agent.run(data)
    else:
        data = data_agent.run(date)
        return "\n\n".join(f"**{k}**\n{v}" for k, v in data.items() if k != "date")
