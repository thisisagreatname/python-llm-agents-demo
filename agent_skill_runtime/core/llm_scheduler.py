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
    source: str
    messages: Tuple[Dict[str, Any], ...]
    assistant_message: Optional[Dict[str, Any]]
    tool_call_id: str


def choose_skill_with_llm(
    *,
    client: Any,
    skills: List[SkillBundle],
    task: str,
    model: str = "",
) -> SchedulerDecision:
    tools = [_build_skill_tool(skill) for skill in skills]

    messages = [
        {
            "role": "system",
            "content": "You are a scheduler in an AI agent system. Choose exactly one native function tool. Use the tool descriptions only, which represent the functional overview of each skill. Do not describe implementation details.",
        },
        {
            "role": "user",
            "content": task,
        },
    ]
    payload: Dict[str, Any] = {"messages": messages, "tools": tools, "tool_choice": "required"}
    resp = client.chat_completions(payload, model=model) if model else client.chat_completions(payload)
    assistant_message = _extract_assistant_message(resp)
    tool_call = _extract_first_tool_call(resp)
    if tool_call:
        skill_name, args = _parse_selected_skill_call(tool_call)
        decision = SchedulerDecision(
            skill_name=skill_name,
            input_payload=_coerce_dict(args),
            rationale=_extract_message_content(resp) or "selected_by_native_tool_call",
            source="native_tool_call",
            messages=tuple(messages),
            assistant_message=assistant_message,
            tool_call_id=str(tool_call.get("id") or ""),
        )
        return _normalize_decision(decision, skills, task)

    content = _extract_message_content(resp)
    decision = _parse_json_object(content) if content else None
    if decision:
        parsed = SchedulerDecision(
            skill_name=str(decision.get("skill_name") or ""),
            input_payload=_coerce_dict(decision.get("input_payload")),
            rationale=str(decision.get("rationale") or "").strip(),
            source="content_json",
            messages=tuple(messages),
            assistant_message=assistant_message,
            tool_call_id="",
        )
        return _normalize_decision(parsed, skills, task)

    fallback_skill = _heuristic_pick(skills, task)
    return SchedulerDecision(
        skill_name=fallback_skill.name,
        input_payload=_default_payload_for_skill(fallback_skill.name, task),
        rationale="fallback",
        source="fallback",
        messages=tuple(messages),
        assistant_message=assistant_message,
        tool_call_id="",
    )


def continue_after_tool_result(
    *,
    client: Any,
    decision: SchedulerDecision,
    tool_result: Dict[str, Any],
    model: str = "",
) -> Dict[str, Any]:
    if not decision.assistant_message or not decision.tool_call_id:
        return {}

    messages = list(decision.messages)
    messages.append(decision.assistant_message)
    messages.append(
        {
            "role": "tool",
            "tool_call_id": decision.tool_call_id,
            "content": json.dumps(tool_result, ensure_ascii=False),
        }
    )
    payload: Dict[str, Any] = {"messages": messages}
    return client.chat_completions(payload, model=model) if model else client.chat_completions(payload)


def extract_final_text(resp: Dict[str, Any]) -> str:
    return _extract_message_content(resp) or ""


def _build_skill_tool(skill: SkillBundle) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": _tool_name_for_skill(skill.name),
            "description": f"{skill.description} Functional overview: {skill.functional_overview}",
            "parameters": _parameters_for_skill(skill.name),
        },
    }


def _tool_name_for_skill(skill_name: str) -> str:
    return f"skill__{skill_name}"


def _skill_name_from_tool_name(tool_name: str) -> str:
    if tool_name.startswith("skill__"):
        return tool_name[7:]
    return tool_name


def _parameters_for_skill(skill_name: str) -> Dict[str, Any]:
    if skill_name == "text_analyzer":
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text that should be analyzed.",
                }
            },
            "required": ["text"],
            "additionalProperties": False,
        }
    if skill_name == "compute":
        return {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "The first number."},
                "b": {"type": "number", "description": "The second number."},
            },
            "required": ["a", "b"],
            "additionalProperties": False,
        }
    return {
        "type": "object",
        "properties": {},
        "additionalProperties": True,
    }


def _normalize_decision(decision: SchedulerDecision, skills: List[SkillBundle], task: str) -> SchedulerDecision:
    skill_map = {skill.name: skill for skill in skills}
    selected = skill_map.get(decision.skill_name)
    if not selected:
        selected = _heuristic_pick(skills, task)

    input_payload = dict(decision.input_payload) if isinstance(decision.input_payload, dict) else {}
    input_payload = _normalize_input_payload(selected.name, input_payload, task)
    rationale = decision.rationale or "selected"
    return SchedulerDecision(
        skill_name=selected.name,
        input_payload=input_payload,
        rationale=rationale,
        source=decision.source,
        messages=decision.messages,
        assistant_message=decision.assistant_message,
        tool_call_id=decision.tool_call_id,
    )


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
    message = _extract_assistant_message(resp) or {}
    tool_calls = message.get("tool_calls") or []
    if isinstance(tool_calls, list) and tool_calls:
        first = tool_calls[0]
        return first if isinstance(first, dict) else None
    return None


def _extract_assistant_message(resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    choice0 = (resp or {}).get("choices", [{}])[0] or {}
    message = (choice0.get("message") or {}) if isinstance(choice0, dict) else {}
    return message if isinstance(message, dict) else None


def _parse_selected_skill_call(tool_call: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    function = tool_call.get("function") or {}
    tool_name = function.get("name") or ""
    args_raw = function.get("arguments") or "{}"
    if not isinstance(args_raw, str):
        return _skill_name_from_tool_name(str(tool_name)), {}
    try:
        value = json.loads(args_raw)
        return _skill_name_from_tool_name(str(tool_name)), value if isinstance(value, dict) else {}
    except Exception:
        return _skill_name_from_tool_name(str(tool_name)), {}


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
