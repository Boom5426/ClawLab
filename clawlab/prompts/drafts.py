from __future__ import annotations

from clawlab.core.models import ManagerPlan, MaterialSummary, ProjectCard, ResearcherProfile, TaskPlan


def build_draft_prompts(
    *,
    task_type: str,
    profile: ResearcherProfile,
    project: ProjectCard,
    material_summary: MaterialSummary,
    task_plan: TaskPlan | None = None,
    manager_plan: ManagerPlan | None = None,
    company_handbook_excerpt: str = "",
    employee_playbook_excerpt: str = "",
    relevant_assets_excerpt: str = "",
    recent_protocol_excerpt: str = "",
) -> tuple[str, str]:
    system_prompt = (
        "You generate concise research drafting markdown. "
        "Return markdown only. Respect the requested task_type, current planning strategy, "
        "company handbook, employee playbook, and recent review history."
    )
    user_prompt = f"""
Task type: {task_type}
Researcher:
- name: {profile.name}
- role: {profile.role}
- discipline: {profile.discipline}
- subfield: {profile.subfield}
- methods: {", ".join(profile.methods)}

Project:
- title: {project.title}
- question: {project.research_question}
- current_goal: {project.current_goal}
- blockers: {"; ".join(project.blockers)}
- next_step: {project.next_step}

Material summary:
- title: {material_summary.title}
- short_summary: {material_summary.short_summary}
- key_topics: {", ".join(material_summary.key_topics)}
- methods_or_entities: {", ".join(material_summary.methods_or_entities)}
- useful_snippets:
  {chr(10).join(f"- {item}" for item in material_summary.useful_snippets)}
- relevance_to_project: {material_summary.relevance_to_project}

Task plan:
- goal: {task_plan.task_goal if task_plan else "none"}
- strategy: {task_plan.output_strategy if task_plan else "none"}
- key points: {", ".join(task_plan.key_points_to_cover[:5]) if task_plan else "none"}
- structure: {", ".join(task_plan.recommended_structure[:5]) if task_plan else "none"}

Manager plan:
- final output strategy: {manager_plan.final_output_strategy if manager_plan else "none"}
- employee sequence: {", ".join(manager_plan.selected_employees) if manager_plan else "none"}

Company handbook excerpt:
{company_handbook_excerpt or "none"}

Draft writer playbook excerpt:
{employee_playbook_excerpt or "none"}

Relevant assets:
{relevant_assets_excerpt or "none"}

Recent protocol context:
{recent_protocol_excerpt or "none"}
""".strip()
    return system_prompt, user_prompt
