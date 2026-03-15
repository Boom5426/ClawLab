from __future__ import annotations

import json

from clawlab.core.models import LlmSettings, MaterialSummary, ProjectCard, ResearcherProfile, ReusableAsset, TaskPlan
from clawlab.prompts.drafts import build_draft_prompts
from clawlab.services.llm_service import call_llm, is_llm_enabled


def _rule_based_strategy(task_type: str) -> tuple[str, list[str]]:
    if task_type == "literature-outline":
        return (
            "background_review",
            [
                "Context and stakes",
                "Key literature groupings",
                "Methods or evidence differences",
                "Open gap tied to the project",
            ],
        )
    return (
        "paper_storyline",
        [
            "Problem framing",
            "Gap and main claim",
            "Section ordering",
            "Evidence and next step",
        ],
    )


def create_task_plan(
    *,
    task_type: str,
    profile: ResearcherProfile,
    project: ProjectCard,
    material_summaries: list[MaterialSummary],
    retrieved_assets: list[ReusableAsset],
    llm_settings: LlmSettings | None = None,
) -> TaskPlan:
    if llm_settings and is_llm_enabled(llm_settings, "drafts"):
        try:
            merged_material = material_summaries[0]
            system_prompt, user_prompt = build_draft_prompts(
                task_type=task_type,
                profile=profile,
                project=project,
                material_summary=merged_material,
            )
            planning_prompt = (
                f"{user_prompt}\n\nReturn JSON only with keys: "
                "task_goal, output_strategy, key_points_to_cover, recommended_structure, "
                "project_considerations, selected_assets."
            )
            content = call_llm(
                settings=llm_settings,
                prompt=planning_prompt,
                system_prompt=system_prompt,
                temperature=0.15,
                max_tokens=900,
            )
            payload = json.loads(content)
            return TaskPlan(
                task_type=task_type,  # type: ignore[arg-type]
                task_goal=payload["task_goal"],
                output_strategy=payload["output_strategy"],
                key_points_to_cover=payload.get("key_points_to_cover", []),
                recommended_structure=payload.get("recommended_structure", []),
                project_considerations=payload.get("project_considerations", []),
                selected_assets=payload.get("selected_assets", []),
            )
        except Exception:
            pass

    output_strategy, recommended_structure = _rule_based_strategy(task_type)
    merged_topics = []
    merged_entities = []
    for summary in material_summaries:
        merged_topics.extend(summary.key_topics[:3])
        merged_entities.extend(summary.methods_or_entities[:3])
    deduped_topics = list(dict.fromkeys(merged_topics))
    deduped_entities = list(dict.fromkeys(merged_entities))
    key_points = [
        f"Cover the main project question: {project.research_question}",
        f"Use the strongest material topics: {', '.join(deduped_topics[:5]) or 'none extracted'}",
        f"Track methods or entities: {', '.join(deduped_entities[:5]) or 'none extracted'}",
    ]
    considerations = [
        f"Keep the draft aligned with the current goal: {project.current_goal}",
        f"Address the blocker directly: {'; '.join(project.blockers) or 'no blocker listed'}",
        "Prefer learned assets when they reduce generic framing.",
    ]
    selected_asset_labels = [f"{asset.asset_type}: {asset.title}" for asset in retrieved_assets[:4]]
    return TaskPlan(
        task_type=task_type,  # type: ignore[arg-type]
        task_goal=(
            f"Prepare a {task_type} draft that uses condensed materials and prior assets "
            f"to support the active project: {project.title}"
        ),
        output_strategy=output_strategy,
        key_points_to_cover=key_points,
        recommended_structure=recommended_structure,
        project_considerations=considerations,
        selected_assets=selected_asset_labels,
    )
