from __future__ import annotations

from pathlib import Path

from clawlab.core.constants import SUPPORTED_TASK_TYPES
from clawlab.core.models import (
    LlmSettings,
    MaterialSummary,
    ProjectCard,
    ResearcherProfile,
    ReusableAsset,
    TaskCard,
    TaskPlan,
    utc_now,
)
from clawlab.prompts.drafts import build_draft_prompts
from clawlab.services.llm_service import call_llm, is_llm_enabled
from clawlab.templates.drafts import render_literature_outline, render_paper_outline
from clawlab.utils.ids import create_id


def generate_draft(
    profile: ResearcherProfile,
    project: ProjectCard,
    *,
    task_type: str,
    material_summaries: list[MaterialSummary],
    retrieved_assets: list[ReusableAsset],
    task_plan: TaskPlan,
    output_dir: Path,
    workspace_root: Path,
    llm_settings: LlmSettings | None = None,
) -> tuple[TaskCard, Path]:
    if task_type not in SUPPORTED_TASK_TYPES:
        raise ValueError(f"Unsupported task_type: {task_type}")

    timestamp = utc_now()
    task_id = create_id("task")
    primary_material = material_summaries[0]
    input_materials = primary_material.useful_snippets or [primary_material.short_summary]
    input_summary = primary_material.short_summary

    expected_output = (
        "Structured literature outline in markdown."
        if task_type == "literature-outline"
        else "Structured paper outline in markdown."
    )

    draft_content: str | None = None
    if llm_settings and is_llm_enabled(llm_settings, "drafts"):
        try:
            system_prompt, user_prompt = build_draft_prompts(
                task_type=task_type,
                profile=profile,
                project=project,
                material_summary=primary_material,
            )
            if retrieved_assets:
                user_prompt = (
                    f"{user_prompt}\n\nRetrieved assets:\n"
                    + "\n".join(f"- {asset.asset_type}: {asset.title} => {asset.content}" for asset in retrieved_assets[:4])
                    + f"\n\nTask plan:\n- goal: {task_plan.task_goal}\n- strategy: {task_plan.output_strategy}\n"
                    + "\n".join(f"- {point}" for point in task_plan.key_points_to_cover)
                )
            draft_content = call_llm(
                settings=llm_settings,
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.25,
                max_tokens=1400,
            )
        except Exception:
            draft_content = None

    if draft_content is None:
        if task_type == "literature-outline":
            draft_content = render_literature_outline(profile, project, material_summaries, task_plan, retrieved_assets)
        else:
            draft_content = render_paper_outline(profile, project, material_summaries, task_plan, retrieved_assets)

    draft_path = output_dir / f"{task_id}_{task_type}.md"
    draft_path.write_text(draft_content, encoding="utf-8")

    task = TaskCard(
        id=task_id,
        project_card_id=project.id,
        task_type=task_type,
        input_summary=input_summary,
        input_materials=input_materials,
        input_material_paths=[summary.source_path for summary in material_summaries],
        input_material_types=[summary.source_type for summary in material_summaries],
        material_summary_title=primary_material.title,
        material_summary_count=len(material_summaries),
        retrieved_asset_ids=[asset.id for asset in retrieved_assets],
        expected_output=expected_output,
        generated_draft_path=str(draft_path.relative_to(workspace_root.parent)),
        revised_draft_path=None,
        feedback_summary="",
        created_at=timestamp,
        updated_at=timestamp,
    )
    return task, draft_path
