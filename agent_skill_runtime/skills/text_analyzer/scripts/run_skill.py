import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict

from tool_text_stats import analyze_text


def emit_event(phase: str, message: str, **payload: Any) -> None:
    print("EVENT " + json.dumps({"phase": phase, "message": message, **payload}, ensure_ascii=False))


def emit_result(result: Dict[str, Any]) -> None:
    print("RESULT " + json.dumps(result, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="text-analyzer-skill")
    parser.add_argument("--input-json", required=True)
    return parser.parse_args()


def load_config(config_path: Path) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


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
        emit_event("config_loaded", "文本分析技能配置加载完成", config_path=str(config_path))

        args = parse_args()
        input_payload = load_input(args.input_json)
        emit_event("input_loaded", "文本分析输入解析完成", input_keys=sorted(input_payload.keys()))

        text = str(input_payload["text"])
        logging.info("开始执行文本分析")
        emit_event("tool_selected", "已选择文本分析工具", tool="tool_text_stats.analyze_text")
        analysis = analyze_text(
            text,
            max_keywords=int(config.get("max_keywords") or 5),
            min_token_length=int(config.get("min_token_length") or 2),
            warn_length=int(config.get("warn_length") or 200),
        )
        emit_event(
            "tool_completed",
            "文本分析完成",
            char_count=analysis["char_count"],
            sentence_count=analysis["sentence_count"],
            keyword_count=len(analysis["keywords"]),
        )
        result = {"skill": "text_analyzer", "input": {"text": text}, "analysis": analysis}
        emit_result(result)
        return 0
    except Exception as exc:
        logging.exception("文本分析技能执行失败")
        emit_event("error", "文本分析技能执行失败", error=str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

