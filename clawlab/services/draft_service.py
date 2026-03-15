from __future__ import annotations

from pathlib import Path

from clawlab.core.constants import SUPPORTED_TASK_TYPES
from clawlab.core.models import (
    LlmSettings,
    ManagerPlan,
    MaterialSummary,
    ProjectCard,
    ResearcherProfile,
    ReusableAsset,
    TaskCard,
    TaskPlan,
    utc_now,
)
from clawlab.prompts.drafts import build_draft_prompts
from clawlab.services.context_service import (
    get_company_handbook_context,
    get_employee_playbook_context,
    get_recent_protocol_context,
    get_relevant_assets_context,
)
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
    manager_plan: ManagerPlan | None = None,
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
    draft_used_llm = False
    company_handbook_excerpt, company_sources = get_company_handbook_context()
    playbook_excerpt, playbook_sources = get_employee_playbook_context("draft_writer")
    protocol_excerpt, protocol_sources = get_recent_protocol_context(
        project_id=project.id,
        employee_role="draft_writer",
    )
    relevant_assets_excerpt, asset_sources, _ = get_relevant_assets_context(
        project=project,
        employee_role="draft_writer",
    )
    context_sources = company_sources + playbook_sources + protocol_sources + asset_sources
    if llm_settings and is_llm_enabled(llm_settings, "drafts"):
        try:
            system_prompt, user_prompt = build_draft_prompts(
                task_type=task_type,
                profile=profile,
                project=project,
                material_summary=primary_material,
                task_plan=task_plan,
                manager_plan=manager_plan,
                company_handbook_excerpt=company_handbook_excerpt,
                employee_playbook_excerpt=playbook_excerpt,
                relevant_assets_excerpt=relevant_assets_excerpt,
                recent_protocol_excerpt=protocol_excerpt,
            )
            draft_content = call_llm(
                settings=llm_settings,
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.25,
                max_tokens=1400,
            )
            draft_used_llm = True
        except Exception:
            draft_content = None
            draft_used_llm = False

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
        draft_mode="llm" if draft_used_llm else "rule",
        draft_context_sources=context_sources,
        expected_output=expected_output,
        generated_draft_path=str(draft_path.relative_to(workspace_root.parent)),
        revised_draft_path=None,
        feedback_summary="",
        created_at=timestamp,
        updated_at=timestamp,
    )
    return task, draft_path
