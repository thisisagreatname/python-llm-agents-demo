from pathlib import Path
from typing import Dict, List, Tuple

from agent_skill_runtime.core.contracts import SkillBundle


def discover_skill_bundles(skills_root: Path) -> List[SkillBundle]:
    if not skills_root.exists():
        return []

    bundles: List[SkillBundle] = []
    for child in sorted(skills_root.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        scripts_dir = child / "scripts"
        if not skill_md.exists() or not scripts_dir.exists():
            continue
        bundles.append(load_skill_bundle(child))
    return bundles


def load_skill_bundle(skill_dir: Path) -> SkillBundle:
    skill_md = skill_dir / "SKILL.md"
    full_markdown = skill_md.read_text(encoding="utf-8")
    metadata, body = _parse_frontmatter(full_markdown)
    title = _extract_title(body) or metadata.get("name") or skill_dir.name
    functional_overview = _extract_section(body, "功能概述") or _extract_section(body, "Functional Overview")
    description = str(metadata.get("description") or "").strip()
    name = str(metadata.get("name") or skill_dir.name).strip()
    return SkillBundle(
        name=name,
        title=title,
        description=description,
        full_markdown=full_markdown,
        functional_overview=functional_overview.strip(),
        skill_dir=skill_dir,
        scripts_dir=skill_dir / "scripts",
        metadata=metadata,
    )


def _parse_frontmatter(markdown_text: str) -> Tuple[Dict[str, str], str]:
    lines = markdown_text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, markdown_text

    metadata: Dict[str, str] = {}
    end_index = -1
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            end_index = index
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")

    if end_index == -1:
        return {}, markdown_text

    body = "\n".join(lines[end_index + 1 :]).strip()
    return metadata, body


def _extract_title(markdown_body: str) -> str:
    for line in markdown_body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _extract_section(markdown_body: str, heading: str) -> str:
    lines = markdown_body.splitlines()
    capture = False
    captured: List[str] = []
    target = f"## {heading}"
    for line in lines:
        if line.strip() == target:
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture:
            captured.append(line)
    return "\n".join(captured).strip()
