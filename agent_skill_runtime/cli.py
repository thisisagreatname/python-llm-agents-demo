import argparse
import json
import sys
from pathlib import Path


def _ensure_repo_root_on_sys_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    return repo_root


def build_parser(repo_root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-skill-runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scheduler_parser = subparsers.add_parser("scheduler")
    scheduler_parser.add_argument("--json", action="store_true")
    scheduler_parser.add_argument("--task", type=str, default="")
    scheduler_parser.add_argument("--model", type=str, default="")
    scheduler_parser.add_argument("--config", type=str, default=str(repo_root / "llm_configs.json"))

    executor_parser = subparsers.add_parser("executor")
    executor_parser.add_argument("skill", help="要查看的技能名称")
    executor_parser.add_argument("--json", action="store_true")

    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("skill", help="要执行的技能名称")
    execute_parser.add_argument("--a", type=float, default=1.0)
    execute_parser.add_argument("--b", type=float, default=2.0)
    execute_parser.add_argument("--text", type=str, default="")
    execute_parser.add_argument("--input-json", type=str, default="")
    execute_parser.add_argument("--json", action="store_true")

    dispatch_parser = subparsers.add_parser("dispatch")
    dispatch_parser.add_argument("--task", type=str, required=True)
    dispatch_parser.add_argument("--model", type=str, default="")
    dispatch_parser.add_argument("--config", type=str, default=str(repo_root / "llm_configs.json"))
    dispatch_parser.add_argument("--json", action="store_true")
    return parser


def build_input_payload(args: argparse.Namespace) -> dict:
    if args.input_json:
        payload = json.loads(args.input_json)
        if not isinstance(payload, dict):
            raise ValueError("--input-json 必须是 JSON object")
        return payload

    if args.skill == "text_analyzer":
        if args.text:
            return {"text": args.text}
        return {"text": "请对这段文本进行统计分析：字符数、句子数与关键词。"}

    return {"a": args.a, "b": args.b}


def main() -> int:
    repo_root = _ensure_repo_root_on_sys_path()
    skills_root = repo_root / "agent_skill_runtime" / "skills"

    from agent_skill_runtime.core.console import print_event, render_scheduler_card
    from agent_skill_runtime.core.disclosure import executor_view, scheduler_view
    from agent_skill_runtime.core.llm_scheduler import choose_skill_with_llm
    from agent_skill_runtime.core.registry import build_registry
    from agent_skill_runtime.core.runner import run_skill

    parser = build_parser(repo_root)
    args = parser.parse_args()
    registry = build_registry(skills_root)

    if args.command == "scheduler":
        skill_list = list(registry.all())
        skills = [scheduler_view(skill) for skill in skill_list]
        if args.task:
            from llm_client import load_client_from_config

            client = load_client_from_config(args.config)
            decision = choose_skill_with_llm(client=client, skills=skill_list, task=args.task, model=args.model)
            print(
                json.dumps(
                    {
                        "task": args.task,
                        "skill_name": decision.skill_name,
                        "input_payload": decision.input_payload,
                        "rationale": decision.rationale,
                    },
                    ensure_ascii=False,
                )
                if args.json
                else f'{decision.skill_name} | {decision.rationale}'
            )
            return 0
        if args.json:
            print(
                json.dumps(
                    [
                        {
                            "name": item.name,
                            "title": item.title,
                            "description": item.description,
                            "functional_overview": item.functional_overview,
                        }
                        for item in skills
                    ],
                    ensure_ascii=False,
                )
            )
        else:
            for item in skills:
                print(render_scheduler_card(item))
        return 0

    if args.command == "dispatch":
        from llm_client import load_client_from_config

        skill_list = list(registry.all())
        client = load_client_from_config(args.config)
        decision = choose_skill_with_llm(client=client, skills=skill_list, task=args.task, model=args.model)
        selected_skill = registry.get(decision.skill_name)
        result = run_skill(skill=selected_skill, input_payload=decision.input_payload)
        if not args.json:
            for event in result.events:
                print_event(event)
        summary = {
            "task": args.task,
            "selected_skill": decision.skill_name,
            "scheduler_rationale": decision.rationale,
            "command": result.record.command,
            "return_code": result.record.return_code,
            "result": result.record.result,
            "stdout": result.record.stdout if args.json else "",
            "stderr": result.record.stderr if args.json else "",
            "event_count": len(result.events),
        }
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    skill = registry.get(args.skill)
    if args.command == "executor":
        package = executor_view(skill)
        payload = {
            "name": package.name,
            "title": package.title,
            "description": package.description,
            "scripts_dir": str(package.scripts_dir),
            "skill_markdown": package.skill_markdown,
            "metadata": package.metadata,
        }
        print(json.dumps(payload, ensure_ascii=False) if args.json else package.skill_markdown)
        return 0

    result = run_skill(skill=skill, input_payload=build_input_payload(args))
    if not args.json:
        for event in result.events:
            print_event(event)

    summary = {
        "skill": result.record.skill_name,
        "command": result.record.command,
        "return_code": result.record.return_code,
        "result": result.record.result,
        "stdout": result.record.stdout if args.json else "",
        "stderr": result.record.stderr if args.json else "",
        "event_count": len(result.events),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
