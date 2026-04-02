from pathlib import Path
from typing import Dict, Iterable

from agent_skill_runtime.core.contracts import SkillBundle
from agent_skill_runtime.core.loader import discover_skill_bundles


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: Dict[str, SkillBundle] = {}

    def register(self, skill: SkillBundle) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillBundle:
        return self._skills[name]

    def all(self) -> Iterable[SkillBundle]:
        return self._skills.values()


def build_registry(skills_root: Path) -> SkillRegistry:
    registry = SkillRegistry()
    for bundle in discover_skill_bundles(skills_root):
        registry.register(bundle)
    return registry

