from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SkillBundle:
    name: str
    title: str
    description: str
    full_markdown: str
    functional_overview: str
    skill_dir: Path
    scripts_dir: Path
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class SkillRunRecord:
    skill_name: str
    command: List[str]
    return_code: int
    stdout: str
    stderr: str
    result: Optional[Dict[str, Any]]


@dataclass(frozen=True)
class SkillRunEvent:
    index: int
    phase: str
    message: str
    payload: Dict[str, Any]


@dataclass(frozen=True)
class SkillRunResult:
    record: SkillRunRecord
    events: Tuple[SkillRunEvent, ...]
