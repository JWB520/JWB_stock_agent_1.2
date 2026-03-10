import json

from agent.memory import MemoryManager
from agent.schema import TaskContext
from agent.workers import scout, analyst, judge, editor, translator
from utils.logger import logger


class Orchestrator:
    def run(self, user_input: str) -> str:
        memory = MemoryManager()
        ctx = TaskContext(user_instruction=user_input)

        translator.run(ctx)

        # 优先处理记忆控制指令
        action = ctx.structured_instruction.get("memory_action")
        if action == "clear_all":
            memory.clear_all()
            logger.info("MemoryManager: 已清空全部记忆")
        elif action == "forget_ticker":
            target = ctx.structured_instruction.get("forget_target") or ""
            if target:
                removed = memory.delete_by_ticker(target)
                logger.info("MemoryManager: 已删除 %s 相关记忆 %d 条", target, removed)

        # Scout 优先使用结构化指令，降级到原始指令
        scout_instruction = (
            json.dumps(ctx.structured_instruction, ensure_ascii=False)
            if ctx.structured_instruction
            else user_input
        )
        ctx.user_instruction = scout_instruction

        scout.run(ctx)
        if not ctx.raw_data:
            return "❌ 情报官未能获取到任何数据，请检查日期或网络连接后重试。"

        analyst.run(ctx)
        judge.run(ctx)
        editor.run(ctx)
        return ctx.final_report
