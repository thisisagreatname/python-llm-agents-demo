from agent_skill_runtime.core.contracts import ExecutorSkillPackage, SchedulerSkillCard, SkillBundle


def scheduler_view(bundle: SkillBundle) -> SchedulerSkillCard:
    return SchedulerSkillCard(
        name=bundle.name,
        title=bundle.title,
        description=bundle.description,
        functional_overview=bundle.functional_overview,
    )


def executor_view(bundle: SkillBundle) -> ExecutorSkillPackage:
    return ExecutorSkillPackage(
        name=bundle.name,
        title=bundle.title,
        description=bundle.description,
        skill_markdown=bundle.full_markdown,
        scripts_dir=bundle.scripts_dir,
        metadata=bundle.metadata,
    )

