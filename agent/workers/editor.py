"""主编：纯文本排版，无需大模型调用。"""
from datetime import datetime
from agent.schema import TaskContext

_DISCLAIMER = "> ⚠️ **免责声明**：本报告由AI多智能体系统自动生成，仅供学习研究参考，不构成任何投资建议。股市有风险，入市需谨慎。"


def run(ctx: TaskContext) -> None:
    date_str = datetime.now().strftime("%Y年%m月%d日")
    ctx.final_report = f"""# 📊 A股深度复盘研报 · {date_str}

{_DISCLAIMER}

---

{ctx.analysis_draft}

---

## 🚨 风控总监点评

{ctx.critique}

---
*由 A股多智能体研究组（情报官→分析师→风控总监→主编）联合出品*"""
