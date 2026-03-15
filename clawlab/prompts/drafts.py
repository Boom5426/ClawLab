from __future__ import annotations

from clawlab.core.models import MaterialSummary, ProjectCard, ResearcherProfile


def build_draft_prompts(
    *,
    task_type: str,
    profile: ResearcherProfile,
    project: ProjectCard,
    material_summary: MaterialSummary,
) -> tuple[str, str]:
    system_prompt = (
        "You generate concise research drafting markdown. "
        "Return markdown only. Respect the requested task_type."
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
""".strip()
    return system_prompt, user_prompt
