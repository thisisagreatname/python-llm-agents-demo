import json
from pathlib import Path
from typing import Any, Dict


def load_config(config_path: Path) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def compute(a: float, b: float, *, operation: str) -> float:
    if operation == "add":
        return a + b
    if operation == "subtract":
        return a - b
    if operation == "multiply":
        return a * b
    if operation == "divide":
        if b == 0:
            raise ValueError("除数不能为 0")
        return a / b
    raise ValueError(f"不支持的 operation: {operation}")

