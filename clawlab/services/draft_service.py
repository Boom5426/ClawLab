from __future__ import annotations

from pathlib import Path

from clawlab.core.constants import SUPPORTED_TASK_TYPES
from clawlab.core.models import MaterialDocument, ProjectCard, ResearcherProfile, TaskCard, utc_now
from clawlab.templates.drafts import render_literature_outline, render_paper_outline
from clawlab.utils.ids import create_id
from clawlab.utils.text import normalize_lines


def generate_draft(
    profile: ResearcherProfile,
    project: ProjectCard,
    *,
    task_type: str,
    material: MaterialDocument,
    output_dir: Path,
    workspace_root: Path,
) -> tuple[TaskCard, Path]:
    if task_type not in SUPPORTED_TASK_TYPES:
        raise ValueError(f"Unsupported task_type: {task_type}")

    timestamp = utc_now()
    task_id = create_id("task")
    input_materials = normalize_lines(material.extracted_text)
    input_summary = input_materials[0] if input_materials else "No summary provided"

    if task_type == "literature-outline":
        draft_content = render_literature_outline(profile, project, input_summary, input_materials)
        expected_output = "Structured literature outline in markdown."
    else:
        draft_content = render_paper_outline(profile, project, input_summary, input_materials)
        expected_output = "Structured paper outline in markdown."

    draft_path = output_dir / f"{task_id}_{task_type}.md"
    draft_path.write_text(draft_content, encoding="utf-8")

    task = TaskCard(
        id=task_id,
        project_card_id=project.id,
        task_type=task_type,
        input_summary=input_summary,
        input_materials=input_materials,
        input_material_paths=[material.path],
        input_material_types=[material.material_type],
        expected_output=expected_output,
        generated_draft_path=str(draft_path.relative_to(workspace_root.parent)),
        revised_draft_path=None,
        feedback_summary="",
        created_at=timestamp,
        updated_at=timestamp,
    )
    return task, draft_path
