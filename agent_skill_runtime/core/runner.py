import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Sequence

from agent_skill_runtime.core.contracts import SkillBundle, SkillRunEvent, SkillRunRecord, SkillRunResult


def run_skill(
    *,
    skill: SkillBundle,
    input_payload: Dict[str, object],
    selected_by: str = "manual",
    task: str = "",
    python_executable: Optional[str] = None,
) -> SkillRunResult:
    run_script = skill.scripts_dir / "run_skill.py"
    command = [
        python_executable or sys.executable,
        str(run_script),
        "--input-json",
        json.dumps(input_payload, ensure_ascii=False),
    ]
    completed = subprocess.run(
        command,
        cwd=str(skill.scripts_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        },
    )
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    result = _extract_result(stdout)
    events = tuple(_parse_events(stdout, stderr, command, skill, completed.returncode, selected_by, task))
    return SkillRunResult(
        record=SkillRunRecord(
            skill_name=skill.name,
            command=command,
            return_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            result=result,
        ),
        events=events,
    )


def _parse_events(
    stdout: str,
    stderr: str,
    command: Sequence[str],
    skill: SkillBundle,
    return_code: int,
    selected_by: str,
    task: str,
) -> List[SkillRunEvent]:
    events: List[SkillRunEvent] = [
        SkillRunEvent(
            index=1,
            phase="skill_selected",
            message="已确定要执行的技能",
            payload={
                "skill": skill.name,
                "title": skill.title,
                "selected_by": selected_by,
                "task": task,
                "functional_overview": skill.functional_overview,
            },
        ),
        SkillRunEvent(
            index=2,
            phase="executor_loaded",
            message="执行器加载完整 SKILL.md 与 scripts 目录",
            payload={"skill_dir": str(skill.skill_dir), "scripts_dir": str(skill.scripts_dir)},
        ),
        SkillRunEvent(
            index=3,
            phase="script_started",
            message="执行技能脚本",
            payload={"command": list(command)},
        ),
    ]

    event_index = len(events) + 1
    for line in stdout.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.startswith("EVENT "):
            payload_text = text[6:]
            try:
                payload = json.loads(payload_text)
            except Exception:
                payload = {"raw": payload_text}
            events.append(
                SkillRunEvent(
                    index=event_index,
                    phase=str(payload.get("phase") or "script_event"),
                    message=str(payload.get("message") or "脚本事件"),
                    payload=payload,
                )
            )
            event_index += 1

    if stderr.strip():
        events.append(
            SkillRunEvent(
                index=event_index,
                phase="script_stderr",
                message="脚本产生标准错误输出",
                payload={"stderr": stderr.strip()},
            )
        )
        event_index += 1

    events.append(
        SkillRunEvent(
            index=event_index,
            phase="run_completed",
            message="技能脚本执行结束",
            payload={"return_code": return_code, "has_result": _result_exists(stdout)},
        )
    )
    return events


def _result_exists(stdout: str) -> bool:
    return any(line.strip().startswith("RESULT ") for line in stdout.splitlines())


def _extract_result(stdout: str) -> Optional[Dict[str, object]]:
    for line in reversed(stdout.splitlines()):
        text = line.strip()
        if not text.startswith("RESULT "):
            continue
        payload_text = text[7:]
        try:
            payload = json.loads(payload_text)
        except Exception:
            return {"raw": payload_text}
        if isinstance(payload, dict):
            return payload
        return {"value": payload}
    return None
