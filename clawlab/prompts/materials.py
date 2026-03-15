from __future__ import annotations


def build_material_summary_prompts(*, source_path: str, source_type: str, text: str, project_context: str) -> tuple[str, str]:
    system_prompt = (
        "You condense research material into a compact JSON object. "
        "Return valid JSON only with keys: title, short_summary, key_topics, methods_or_entities, "
        "useful_snippets, relevance_to_project, raw_text_excerpt."
    )
    user_prompt = f"""
Source path: {source_path}
Source type: {source_type}
Project context: {project_context}

Material text:
{text[:12000]}
""".strip()
    return system_prompt, user_prompt
