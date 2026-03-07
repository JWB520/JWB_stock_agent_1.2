from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskContext:
    user_instruction: str
    raw_data: dict[str, Any] = field(default_factory=dict)
    analysis_draft: str = ""
    critique: str = ""
    final_report: str = ""
