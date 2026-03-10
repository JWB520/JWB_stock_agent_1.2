import json

from agent.schema import TaskContext
from agent.workers import scout, analyst, judge, editor, translator


class Orchestrator:
    def run(self, user_input: str) -> str:
        ctx = TaskContext(user_instruction=user_input)

        translator.run(ctx)

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
