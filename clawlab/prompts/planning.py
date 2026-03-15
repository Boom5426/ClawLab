from __future__ import annotations

from clawlab.core.models import MaterialSummary, ProjectCard, ResearcherProfile, ReusableAsset


def build_planning_prompts(
    *,
    task_type: str,
    profile: ResearcherProfile,
    project: ProjectCard,
    material_summaries: list[MaterialSummary],
    retrieved_assets: list[ReusableAsset],
    company_handbook_excerpt: str = "",
    employee_playbook_excerpt: str = "",
    recent_protocol_excerpt: str = "",
) -> tuple[str, str]:
    system_prompt = (
        "You are a project manager inside a virtual research company. "
        "Return valid JSON only. "
        "Use structured planning and respect the company's handbook, employee playbook, and recent review history."
    )
    material_lines = "\n".join(
        f"- {summary.title}: {summary.short_summary} | topics={', '.join(summary.key_topics[:4])}"
        for summary in material_summaries[:3]
    )
    asset_lines = "\n".join(
        f"- {asset.scope}/{asset.asset_type}: {asset.title} => {asset.content[:220]}"
        for asset in retrieved_assets[:5]
    )
    user_prompt = f"""
Task type: {task_type}

Researcher:
- name: {profile.name}
- role: {profile.role}
- discipline: {profile.discipline}
- methods: {", ".join(profile.methods)}

Project:
- title: {project.title}
- research_question: {project.research_question}
- current_goal: {project.current_goal}
- blockers: {"; ".join(project.blockers)}
- next_step: {project.next_step}

Material summaries:
{material_lines or "- none"}

Relevant assets:
{asset_lines or "- none"}

Company handbook excerpt:
{company_handbook_excerpt or "none"}

Project manager playbook excerpt:
{employee_playbook_excerpt or "none"}

Recent protocol context:
{recent_protocol_excerpt or "none"}

Return JSON only with keys:
- task_goal
- output_strategy
- key_points_to_cover
- recommended_structure
- project_considerations
- selected_assets
""".strip()
    return system_prompt, user_prompt


def build_manager_plan_prompts(
    *,
    job_type: str,
    boss_goal: str,
    profile: ResearcherProfile | None,
    project: ProjectCard,
    company_handbook_excerpt: str = "",
    employee_playbook_excerpt: str = "",
    recent_protocol_excerpt: str = "",
) -> tuple[str, str]:
    system_prompt = (
        "You are a manager inside a virtual research company. "
        "Return valid JSON only with keys: selected_employees, expected_deliverables, final_output_strategy. "
        "Choose from these employees only: literature_analyst, project_manager, draft_writer, review_editor."
    )
    user_prompt = f"""
Job type: {job_type}
Boss goal: {boss_goal}

Founder/profile context:
- name: {profile.name if profile else "unknown"}
- role: {profile.role if profile else "unknown"}
- discipline: {profile.discipline if profile else "unknown"}

Project:
- title: {project.title}
- research_question: {project.research_question}
- current_goal: {project.current_goal}
- blockers: {"; ".join(project.blockers)}

Company handbook excerpt:
{company_handbook_excerpt or "none"}

Project manager playbook excerpt:
{employee_playbook_excerpt or "none"}

Recent protocol context:
{recent_protocol_excerpt or "none"}
""".strip()
    return system_prompt, user_prompt
