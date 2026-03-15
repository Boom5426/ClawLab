from __future__ import annotations


def build_material_summary_prompts(
    *,
    source_path: str,
    source_type: str,
    text: str,
    project_context: str,
    company_handbook_excerpt: str = "",
    employee_playbook_excerpt: str = "",
    relevant_assets_excerpt: str = "",
    recent_protocol_excerpt: str = "",
) -> tuple[str, str]:
    system_prompt = (
        "You condense research material into a compact JSON object. "
        "Return valid JSON only with keys: title, short_summary, key_topics, methods_or_entities, "
        "useful_snippets, relevance_to_project, raw_text_excerpt. "
        "Use company and role context when present, but do not mention that context explicitly unless useful."
    )
    user_prompt = f"""
Source path: {source_path}
Source type: {source_type}
Project context: {project_context}

Company handbook excerpt:
{company_handbook_excerpt or "none"}

Employee playbook excerpt:
{employee_playbook_excerpt or "none"}

Relevant assets:
{relevant_assets_excerpt or "none"}

Recent review / handoff / intervention context:
{recent_protocol_excerpt or "none"}

Material text:
{text[:12000]}
""".strip()
    return system_prompt, user_prompt
