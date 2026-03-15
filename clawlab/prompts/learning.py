from __future__ import annotations

from clawlab.core.models import ProjectCard, TaskCard


def build_learning_prompts(*, task: TaskCard, project: ProjectCard, generated_text: str, revised_text: str) -> tuple[str, str]:
    system_prompt = (
        "Analyze a research draft revision. Return valid JSON only with keys: "
        "writing_rules, structure_template, project_note."
    )
    user_prompt = f"""
Task type: {task.task_type}
Project title: {project.title}
Project blockers: {"; ".join(project.blockers)}

Generated draft:
{generated_text[:10000]}

Revised draft:
{revised_text[:10000]}
""".strip()
    return system_prompt, user_prompt
