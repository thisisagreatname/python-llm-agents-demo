from llm_client import load_client_from_config
import json

client = load_client_from_config("llm_configs.json")

def compute_func(a: float, b: float) -> float:
    return a - b


tools = [
    {
        "type": "function",
        "function": {
            "name": "compute_func",
            "description": "计算两个数字的结果",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个数字"},
                    "b": {"type": "number", "description": "第二个数字"},
                },
                "required": ["a", "b"],
                "additionalProperties": False,
            },
        },
    }
]

messages = [{"role": "user", "content": "请计算 compute_func(1, 2)"}]
resp1 = client.chat_completions(
    {"messages": messages, "tools": tools, "tool_choice": "auto"}
)

choice0 = (resp1 or {}).get("choices", [{}])[0]
assistant_msg = (choice0 or {}).get("message", {})
tool_calls = assistant_msg.get("tool_calls") or []

if tool_calls:
    tool_call = tool_calls[0]
    tool_call_id = tool_call.get("id")
    fn = (tool_call.get("function") or {}).get("name")
    args_raw = (tool_call.get("function") or {}).get("arguments") or "{}"

    try:
        args = json.loads(args_raw)
    except Exception:
        args = {}

    if fn == "compute_func":
        result = compute_func(args.get("a"), args.get("b"))
    else:
        result = None

    messages2 = [
        {"role": "user", "content": "请计算 compute_func(1, 2)"},
        {"role": "assistant", "tool_calls": tool_calls},
        {"role": "tool", "tool_call_id": tool_call_id, "content": str(result)},
    ]
    resp2 = client.chat_completions({"messages": messages2})
    print(resp2)
