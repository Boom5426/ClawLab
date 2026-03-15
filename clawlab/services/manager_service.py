from __future__ import annotations

from pathlib import Path

from clawlab.core.models import (
    CompanyJob,
    Deliverable,
    JobResult,
    JobType,
    LlmSettings,
    ManagerPlan,
    MaterialSummary,
    ProjectCard,
    ResearcherProfile,
    TaskCard,
    TaskPlan,
    WorkOrder,
)
from clawlab.services.asset_service import retrieve_assets_for_task
from clawlab.services.employee_service import run_employee_task
from clawlab.services.workspace_service import (
    get_job_dir,
    load_assets,
    load_material_summary,
    load_task,
    load_task_plan,
    save_company_job,
    save_job_result,
    save_manager_plan,
    save_work_order,
)
from clawlab.storage.filesystem import write_text
from clawlab.utils.ids import create_id


JOB_TASK_TYPE_MAP: dict[JobType, str | None] = {
    "literature-brief": "literature-outline",
    "paper-outline": "paper-outline",
    "project-brief": "literature-outline",
}


def _employee_sequence(job_type: JobType, revised_path: Path | None = None) -> list[str]:
    if job_type == "literature-brief":
        sequence = ["literature_analyst", "project_manager", "draft_writer"]
    elif job_type == "paper-outline":
        sequence = ["project_manager", "literature_analyst", "draft_writer"]
    else:
        sequence = ["literature_analyst", "project_manager", "draft_writer"]
    if revised_path is not None:
        sequence.append("review_editor")
    return sequence


def create_manager_plan(
    *,
    job_type: JobType,
    boss_goal: str,
    project: ProjectCard,
    input_path: Path,
    revised_path: Path | None = None,
) -> tuple[CompanyJob, ManagerPlan, list[WorkOrder]]:
    job = CompanyJob(
        id=create_id("job"),
        job_type=job_type,
        project_card_id=project.id,
        boss_goal=boss_goal,
        input_path=str(input_path),
        revised_path=str(revised_path) if revised_path else None,
    )
    selected_employees = _employee_sequence(job_type, revised_path)
    expected_deliverables = {
        "literature_analyst": "Material summary",
        "project_manager": "Task plan",
        "draft_writer": "Draft markdown",
        "review_editor": "Revision report and reusable assets",
    }
    work_orders: list[WorkOrder] = []
    for role in selected_employees:
        work_orders.append(
            WorkOrder(
                id=create_id("workorder"),
                employee_role=role,  # type: ignore[arg-type]
                project_card_id=project.id,
                task_type=JOB_TASK_TYPE_MAP[job_type],  # type: ignore[arg-type]
                task_goal=boss_goal,
                input_context_refs=[str(input_path), project.id],
                expected_output=expected_deliverables[role],
            )
        )

    plan = ManagerPlan(
        id=create_id("manager_plan"),
        job_type=job_type,
        boss_goal=boss_goal,
        selected_employees=selected_employees,  # type: ignore[arg-type]
        work_order_sequence=[work_order.id for work_order in work_orders],
        expected_deliverables=[expected_deliverables[role] for role in selected_employees],
        final_output_strategy=(
            "Produce a concise manager-level brief that explains employee outputs and points to the final artifact."
        ),
    )
    return job, plan, work_orders


def dispatch_work_orders(
    *,
    job: CompanyJob,
    plan: ManagerPlan,
    work_orders: list[WorkOrder],
    profile: ResearcherProfile,
    project: ProjectCard,
    llm_settings: LlmSettings | None = None,
) -> list[Deliverable]:
    save_company_job(job)
    save_manager_plan(job.id, plan)

    deliverables: list[Deliverable] = []
    material_summaries: list[MaterialSummary] = []
    task_plan: TaskPlan | None = None
    latest_task: TaskCard | None = None

    for work_order in work_orders:
        work_order = work_order.model_copy(update={"status": "running"})
        save_work_order(job.id, work_order)

        if work_order.employee_role == "literature_analyst":
            deliverable = run_employee_task(
                "literature_analyst",
                project=project,
                input_path=Path(job.input_path or ""),
                work_order=work_order,
                llm_settings=llm_settings,
            )
            summary = load_material_summary(deliverable.output_path)
            if summary:
                material_summaries = [summary]
        elif work_order.employee_role == "project_manager":
            deliverable = run_employee_task(
                "project_manager",
                profile=profile,
                project=project,
                task_type=JOB_TASK_TYPE_MAP[job.job_type],
                input_path=Path(job.input_path or "") if job.input_path else None,
                material_summaries=material_summaries,
                retrieved_assets=retrieve_assets_for_task(
                    task_type=JOB_TASK_TYPE_MAP[job.job_type] or "literature-outline",
                    project=project,
                    profile=profile,
                    material_summaries=material_summaries,
                    assets=load_assets(),
                ),
                work_order=work_order,
                llm_settings=llm_settings,
            )
            task_plan = load_task_plan(deliverable.output_path)
        elif work_order.employee_role == "draft_writer":
            if not material_summaries:
                raise ValueError("draft_writer requires a material summary before dispatch")
            deliverable = run_employee_task(
                "draft_writer",
                profile=profile,
                project=project,
                task_type=JOB_TASK_TYPE_MAP[job.job_type],
                material_summaries=material_summaries,
                task_plan=task_plan,
                work_order=work_order,
                llm_settings=llm_settings,
            )
            latest_task = load_task(deliverable.source_task_id or "")
        elif work_order.employee_role == "review_editor":
            if latest_task is None or job.revised_path is None:
                work_order = work_order.model_copy(update={"status": "failed"})
                save_work_order(job.id, work_order)
                continue
            deliverable = run_employee_task(
                "review_editor",
                project=project,
                task_card=latest_task,
                revised_path=Path(job.revised_path),
                work_order=work_order,
                llm_settings=llm_settings,
            )
        else:
            raise ValueError(f"Unsupported employee role in manager dispatch: {work_order.employee_role}")

        deliverables.append(deliverable)
        work_order = work_order.model_copy(update={"status": "completed"})
        save_work_order(job.id, work_order)

    return deliverables


def collect_deliverables(deliverables: list[Deliverable]) -> list[Deliverable]:
    return deliverables


def synthesize_job_result(
    *,
    job: CompanyJob,
    plan: ManagerPlan,
    deliverables: list[Deliverable],
) -> JobResult:
    job_dir = get_job_dir(job.id)
    output_path = job_dir / "final_output.md"
    lines = [
        f"# Job Result: {job.job_type}",
        "",
        f"- boss_goal: {job.boss_goal}",
        f"- manager_plan_id: {plan.id}",
        f"- participating_employees: {', '.join(plan.selected_employees)}",
        "",
        "## Deliverables",
    ]
    for deliverable in deliverables:
        lines.append(f"- {deliverable.employee_role}: {deliverable.title} -> {deliverable.output_path}")
        lines.append(f"  summary: {deliverable.summary}")
    lines.extend(
        [
            "",
            "## Final Output Strategy",
            plan.final_output_strategy,
            "",
            "## Manager Summary",
            "The final result is synthesized from the sequential employee chain above. "
            "Use the latest draft or report as the primary artifact, and inspect upstream deliverables when needed.",
            "",
        ]
    )
    write_text(output_path, "\n".join(lines))
    result = JobResult(
        id=create_id("job_result"),
        job_id=job.id,
        manager_plan_id=plan.id,
        project_card_id=job.project_card_id,
        final_output_path=str(output_path.relative_to(Path.cwd())),
        participating_employees=plan.selected_employees,
        deliverable_ids=[deliverable.id for deliverable in deliverables],
        summary=(
            f"Executed {len(deliverables)} deliverable(s) across employees: "
            f"{', '.join(plan.selected_employees)}."
        ),
    )
    save_job_result(job.id, result)
    return result
