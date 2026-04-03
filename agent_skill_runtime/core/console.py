import json

from agent_skill_runtime.core.contracts import SkillBundle, SkillRunEvent


def render_event(event: SkillRunEvent) -> str:
    payload = json.dumps(event.payload, ensure_ascii=False)
    return f"[{event.index:02d}] {event.phase} | {event.message} | {payload}"


def print_event(event: SkillRunEvent) -> None:
    print(render_event(event))


def render_scheduler_card(skill: SkillBundle) -> str:
    return f"{skill.name} | {skill.title} | {skill.description} | {skill.functional_overview}"
