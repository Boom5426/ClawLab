from __future__ import annotations

from pathlib import Path

from clawlab.core.models import (
    Deliverable,
    EmployeeRole,
    EmployeeSpec,
    LlmSettings,
    MaterialSummary,
    ProjectCard,
    ResearcherProfile,
    ReusableAsset,
    TaskCard,
    TaskPlan,
    WorkOrder,
)
from clawlab.services.asset_service import retrieve_assets_for_task
from clawlab.services.draft_service import generate_draft
from clawlab.services.learning_service import derive_assets_from_revision
from clawlab.services.material_service import condense_material
from clawlab.services.planning_service import create_task_plan
from clawlab.services.workspace_service import (
    get_outputs_dir,
    load_assets,
    save_asset,
    save_deliverable,
    save_material_summary,
    save_project,
    save_project_asset,
    save_task,
    save_task_plan,
)
from clawlab.storage.filesystem import write_text
from clawlab.utils.ids import create_id


EMPLOYEE_REGISTRY: dict[EmployeeRole, EmployeeSpec] = {
    "literature_analyst": EmployeeSpec(
        id="employee_literature_analyst",
        role_name="literature_analyst",
        display_name="Literature Analyst",
        description="Reads raw materials and turns them into structured research briefs.",
        core_capabilities=["material extraction", "material summarization", "topic and method identification"],
        supported_task_types=["literature-outline", "paper-outline"],
        accessible_context=["project", "materials"],
        default_templates=["material_summary"],
        memory_scope=["project"],
    ),
    "project_manager": EmployeeSpec(
        id="employee_project_manager",
        role_name="project_manager",
        display_name="Project Manager",
        description="Turns project context, material briefs, and prior assets into a task plan.",
        core_capabilities=["asset retrieval", "task planning", "structure recommendation"],
        supported_task_types=["literature-outline", "paper-outline"],
        accessible_context=["profile", "project", "materials", "assets"],
        default_templates=["task_plan"],
        memory_scope=["project", "task"],
    ),
    "draft_writer": EmployeeSpec(
        id="employee_draft_writer",
        role_name="draft_writer",
        display_name="Draft Writer",
        description="Generates focused markdown drafts from structured project context.",
        core_capabilities=["outline drafting", "markdown generation", "task card creation"],
        supported_task_types=["literature-outline", "paper-outline"],
        accessible_context=["profile", "project", "materials", "assets", "task_plan"],
        default_templates=["literature_outline", "paper_outline"],
        memory_scope=["task"],
    ),
    "review_editor": EmployeeSpec(
        id="employee_review_editor",
        role_name="review_editor",
        display_name="Review Editor",
        description="Analyzes revision deltas and writes back reusable rules, templates, and notes.",
        core_capabilities=["revision analysis", "asset extraction", "project note updates"],
        supported_task_types=["literature-outline", "paper-outline"],
        accessible_context=["project", "task", "draft_revision"],
        default_templates=["writing_rules", "structure_template", "project_note"],
        memory_scope=["global", "project", "task"],
    ),
}


def list_employee_specs() -> list[EmployeeSpec]:
    return list(EMPLOYEE_REGISTRY.values())


def get_employee_spec(role: str) -> EmployeeSpec:
    if role not in EMPLOYEE_REGISTRY:
        raise ValueError(f"Unknown employee role: {role}")
    return EMPLOYEE_REGISTRY[role]  # type: ignore[index]


def _save_deliverable_output(project_id: str, deliverable_id: str, title: str, body: str, repo_root: Path | None = None) -> Path:
    output_dir = Path.cwd() / "workspace" / "projects" / project_id / "deliverables"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{deliverable_id}.md"
    write_text(path, f"# {title}\n\n{body}\n")
    return path


def run_employee_task(
    employee_role: EmployeeRole,
    *,
    profile: ResearcherProfile | None = None,
    project: ProjectCard,
    task_type: str | None = None,
    input_path: Path | None = None,
    material_summaries: list[MaterialSummary] | None = None,
    retrieved_assets: list[ReusableAsset] | None = None,
    task_plan: TaskPlan | None = None,
    task_card: TaskCard | None = None,
    revised_path: Path | None = None,
    work_order: WorkOrder | None = None,
    llm_settings: LlmSettings | None = None,
) -> Deliverable:
    spec = get_employee_spec(employee_role)

    if employee_role == "literature_analyst":
        if input_path is None:
            raise ValueError("literature_analyst requires input_path")
        summary = condense_material(input_path, project=project, llm_settings=llm_settings)
        saved_path = save_material_summary(project.id, summary)
        deliverable = Deliverable(
            id=create_id("deliverable"),
            employee_role=employee_role,
            source_work_order_id=work_order.id if work_order else None,
            title=f"{spec.display_name}: {summary.title}",
            summary=summary.short_summary,
            output_path=str(saved_path.relative_to(Path.cwd())),
        )
        save_deliverable(project.id, deliverable)
        return deliverable

    if employee_role == "project_manager":
        if profile is None or task_type is None:
            raise ValueError("project_manager requires profile and task_type")
        if not material_summaries:
            if input_path is None:
                raise ValueError("project_manager requires material_summaries or input_path")
            material_summaries = [condense_material(input_path, project=project, llm_settings=llm_settings)]
        assets = retrieved_assets or retrieve_assets_for_task(
            task_type=task_type,
            project=project,
            profile=profile,
            material_summaries=material_summaries,
            assets=load_assets(),
        )
        plan = create_task_plan(
            task_type=task_type,
            profile=profile,
            project=project,
            material_summaries=material_summaries,
            retrieved_assets=assets,
            llm_settings=llm_settings,
        )
        plan_task_id = create_id("task")
        plan_path = save_task_plan(plan_task_id, plan)
        deliverable = Deliverable(
            id=create_id("deliverable"),
            employee_role=employee_role,
            source_work_order_id=work_order.id if work_order else None,
            title=f"{spec.display_name}: {task_type} plan",
            summary=plan.task_goal,
            output_path=str(plan_path.relative_to(Path.cwd())),
        )
        save_deliverable(project.id, deliverable)
        return deliverable

    if employee_role == "draft_writer":
        if profile is None or task_type is None or not material_summaries:
            raise ValueError("draft_writer requires profile, task_type, and material_summaries")
        assets = retrieved_assets or retrieve_assets_for_task(
            task_type=task_type,
            project=project,
            profile=profile,
            material_summaries=material_summaries,
            assets=load_assets(),
        )
        plan = task_plan or create_task_plan(
            task_type=task_type,
            profile=profile,
            project=project,
            material_summaries=material_summaries,
            retrieved_assets=assets,
            llm_settings=llm_settings,
        )
        task, draft_path = generate_draft(
            profile,
            project,
            task_type=task_type,
            material_summaries=material_summaries,
            retrieved_assets=assets,
            task_plan=plan,
            output_dir=get_outputs_dir(project.id),
            workspace_root=Path.cwd() / "workspace",
            llm_settings=llm_settings,
        )
        plan_path = save_task_plan(task.id, plan)
        task = task.model_copy(
            update={
                "task_plan_path": str(plan_path.relative_to(Path.cwd())),
            }
        )
        save_task(task)
        deliverable = Deliverable(
            id=create_id("deliverable"),
            employee_role=employee_role,
            source_task_id=task.id,
            source_work_order_id=work_order.id if work_order else None,
            title=f"{spec.display_name}: {task_type} draft",
            summary=task.input_summary,
            output_path=str(draft_path.relative_to(Path.cwd())),
        )
        save_deliverable(project.id, deliverable)
        return deliverable

    if employee_role == "review_editor":
        if task_card is None or revised_path is None:
            raise ValueError("review_editor requires task_card and revised_path")
        generated_path = Path(task_card.generated_draft_path)
        generated_text = generated_path.read_text(encoding="utf-8")
        revised_text = revised_path.read_text(encoding="utf-8")
        updated_task, updated_project, assets = derive_assets_from_revision(
            task_card,
            project,
            generated_text=generated_text,
            revised_text=revised_text,
            llm_settings=llm_settings,
        )
        save_task(updated_task.model_copy(update={"revised_draft_path": str(revised_path)}))
        save_project(updated_project)
        for asset in assets:
            save_asset(asset)
            save_project_asset(updated_project.id, asset)
        output_path = _save_deliverable_output(
            project.id,
            create_id("review"),
            f"{spec.display_name}: revision report",
            updated_task.feedback_summary,
        )
        deliverable = Deliverable(
            id=create_id("deliverable"),
            employee_role=employee_role,
            source_task_id=task_card.id,
            source_work_order_id=work_order.id if work_order else None,
            title=f"{spec.display_name}: revision report",
            summary=updated_task.feedback_summary,
            output_path=str(output_path.relative_to(Path.cwd())),
        )
        save_deliverable(project.id, deliverable)
        return deliverable

    raise ValueError(f"Unsupported employee role: {employee_role}")
