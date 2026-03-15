from __future__ import annotations

from clawlab.core.models import ProjectCard, TaskCard


def build_learning_prompts(
    *,
    task: TaskCard,
    project: ProjectCard,
    generated_text: str,
    revised_text: str,
    company_handbook_excerpt: str = "",
    employee_playbook_excerpt: str = "",
    recent_protocol_excerpt: str = "",
) -> tuple[str, str]:
    system_prompt = (
        "Analyze a research draft revision. Return valid JSON only with keys: "
        "writing_rules, structure_template, project_note, role_memory. "
        "Use the company handbook, role playbook, issue taxonomy, and intervention history when provided."
    )
    user_prompt = f"""
Task type: {task.task_type}
Project title: {project.title}
Project blockers: {"; ".join(project.blockers)}

Company handbook excerpt:
{company_handbook_excerpt or "none"}

Review editor playbook excerpt:
{employee_playbook_excerpt or "none"}

Recent protocol context:
{recent_protocol_excerpt or "none"}

Generated draft:
{generated_text[:10000]}

Revised draft:
{revised_text[:10000]}
""".strip()
    return system_prompt, user_prompt
