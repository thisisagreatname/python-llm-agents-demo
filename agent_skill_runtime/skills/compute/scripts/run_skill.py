import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

from tool_compute import compute, load_config


def emit_event(phase: str, message: str, **payload: Any) -> None:
    print(
        "EVENT "
        + json.dumps(
            {"phase": phase, "message": message, **payload},
            ensure_ascii=False,
        )
    )


def emit_result(result: Dict[str, Any]) -> None:
    print("RESULT " + json.dumps(result, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="compute-skill")
    parser.add_argument("--input-json", required=True)
    return parser.parse_args()


def load_input(raw_text: str) -> Dict[str, Any]:
    payload = json.loads(raw_text)
    if not isinstance(payload, dict):
        raise ValueError("输入必须是 JSON object")
    return payload


def configure_logging(config: Dict[str, Any]) -> None:
    level_name = str(config.get("log_level") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    config_path = base_dir / "skill_config.json"
    try:
        config = load_config(config_path)
        configure_logging(config)
        emit_event("config_loaded", "技能配置加载完成", config_path=str(config_path), operation=config.get("operation"))

        args = parse_args()
        input_payload = load_input(args.input_json)
        emit_event("input_loaded", "输入参数解析完成", input_payload=input_payload)

        a = float(input_payload["a"])
        b = float(input_payload["b"])
        operation = str(config.get("operation") or "subtract")
        precision = int(config.get("precision") or 2)

        logging.info("开始执行计算")
        emit_event("tool_selected", "已选择本地计算工具", tool="tool_compute.compute", operation=operation)
        value = compute(a, b, operation=operation)
        rounded = round(value, precision)
        emit_event("tool_completed", "本地计算完成", raw_result=value, rounded_result=rounded)

        result = {
            "skill": "compute",
            "operation": operation,
            "inputs": {"a": a, "b": b},
            "result": rounded,
        }
        emit_result(result)
        return 0
    except Exception as exc:
        logging.exception("技能执行失败")
        emit_event("error", "技能执行失败", error=str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

