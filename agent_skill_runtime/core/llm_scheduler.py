import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from agent_skill_runtime.core.contracts import SkillBundle


@dataclass(frozen=True)
class SchedulerDecision:
    skill_name: str
    input_payload: Dict[str, Any]
    rationale: str


def choose_skill_with_llm(
    *,
    client: Any,
    skills: List[SkillBundle],
    task: str,
    model: str = "",
) -> SchedulerDecision:
    skill_names = [skill.name for skill in skills]
    tool_schema = {
        "type": "function",
        "function": {
            "name": "select_skill",
            "description": "Select the best skill for the user task and produce a minimal JSON input payload for that skill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "enum": skill_names},
                    "input_payload": {"type": "object"},
                    "rationale": {"type": "string"},
                },
                "required": ["skill_name", "input_payload", "rationale"],
                "additionalProperties": False,
            },
        },
    }

    skill_cards = [
        {
            "name": skill.name,
            "title": skill.title,
            "description": skill.description,
            "functional_overview": skill.functional_overview,
        }
        for skill in skills
    ]

    messages = [
        {
            "role": "system",
            "content": "You are a scheduler in an AI agent system. Use only the provided skill cards (functional overview only). Choose exactly one skill and produce a minimal input payload. Do not reference scripts or implementation details.",
        },
        {
            "role": "user",
            "content": json.dumps(
                {"task": task, "skills": skill_cards},
                ensure_ascii=False,
            ),
        },
    ]
    payload: Dict[str, Any] = {"messages": messages, "tools": [tool_schema], "tool_choice": "auto"}
    resp = client.chat_completions(payload, model=model) if model else client.chat_completions(payload)
    tool_call = _extract_first_tool_call(resp)
    if tool_call:
        args = _parse_tool_call_arguments(tool_call)
        decision = SchedulerDecision(
            skill_name=str(args.get("skill_name") or ""),
            input_payload=_coerce_dict(args.get("input_payload")),
            rationale=str(args.get("rationale") or "").strip(),
        )
        return _normalize_decision(decision, skills, task)

    content = _extract_message_content(resp)
    decision = _parse_json_object(content) if content else None
    if decision:
        parsed = SchedulerDecision(
            skill_name=str(decision.get("skill_name") or ""),
            input_payload=_coerce_dict(decision.get("input_payload")),
            rationale=str(decision.get("rationale") or "").strip(),
        )
        return _normalize_decision(parsed, skills, task)

    fallback_skill = _heuristic_pick(skills, task)
    return SchedulerDecision(
        skill_name=fallback_skill.name,
        input_payload=_default_payload_for_skill(fallback_skill.name, task),
        rationale="fallback",
    )


def _normalize_decision(decision: SchedulerDecision, skills: List[SkillBundle], task: str) -> SchedulerDecision:
    skill_map = {skill.name: skill for skill in skills}
    selected = skill_map.get(decision.skill_name)
    if not selected:
        selected = _heuristic_pick(skills, task)

    input_payload = dict(decision.input_payload) if isinstance(decision.input_payload, dict) else {}
    input_payload = _normalize_input_payload(selected.name, input_payload, task)
    rationale = decision.rationale or "selected"
    return SchedulerDecision(skill_name=selected.name, input_payload=input_payload, rationale=rationale)


def _normalize_input_payload(skill_name: str, input_payload: Dict[str, Any], task: str) -> Dict[str, Any]:
    if skill_name == "text_analyzer":
        text = input_payload.get("text")
        if not isinstance(text, str) or not text.strip():
            return {"text": task}
        return {"text": text}

    if skill_name == "compute":
        a = input_payload.get("a")
        b = input_payload.get("b")
        a_num, b_num = _extract_two_numbers(task)
        try:
            a_val = float(a) if a is not None else a_num
        except Exception:
            a_val = a_num
        try:
            b_val = float(b) if b is not None else b_num
        except Exception:
            b_val = b_num
        return {"a": a_val, "b": b_val}

    return input_payload if input_payload else _default_payload_for_skill(skill_name, task)


def _extract_two_numbers(text: str) -> Tuple[float, float]:
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", text)
    if len(matches) >= 2:
        return float(matches[0]), float(matches[1])
    if len(matches) == 1:
        return float(matches[0]), 2.0
    return 1.0, 2.0


def _heuristic_pick(skills: List[SkillBundle], task: str) -> SkillBundle:
    lower = task.lower()
    for skill in skills:
        if skill.name == "text_analyzer" and any(k in lower for k in ["text", "文本", "关键词", "统计", "分析"]):
            return skill
    for skill in skills:
        if skill.name == "compute" and any(k in lower for k in ["compute", "计算", "+", "-", "*", "/", "加", "减", "乘", "除"]):
            return skill
    return skills[0]


def _default_payload_for_skill(skill_name: str, task: str) -> Dict[str, Any]:
    if skill_name == "text_analyzer":
        return {"text": task}
    return {"a": 1, "b": 2}


def _extract_first_tool_call(resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    choice0 = (resp or {}).get("choices", [{}])[0] or {}
    message = (choice0.get("message") or {}) if isinstance(choice0, dict) else {}
    tool_calls = message.get("tool_calls") or []
    if isinstance(tool_calls, list) and tool_calls:
        first = tool_calls[0]
        return first if isinstance(first, dict) else None
    return None


def _parse_tool_call_arguments(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    function = tool_call.get("function") or {}
    args_raw = function.get("arguments") or "{}"
    if not isinstance(args_raw, str):
        return {}
    try:
        value = json.loads(args_raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _extract_message_content(resp: Dict[str, Any]) -> Optional[str]:
    choice0 = (resp or {}).get("choices", [{}])[0] or {}
    message = (choice0.get("message") or {}) if isinstance(choice0, dict) else {}
    content = message.get("content")
    return content if isinstance(content, str) else None


def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    if not text:
        return None
    if text.startswith("{") and text.endswith("}"):
        try:
            value = json.loads(text)
            return value if isinstance(value, dict) else None
        except Exception:
            return None
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        try:
            value = json.loads(snippet)
            return value if isinstance(value, dict) else None
        except Exception:
            return None
    return None


def _coerce_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}
