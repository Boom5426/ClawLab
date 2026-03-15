from __future__ import annotations

from pathlib import Path
import json

from clawlab.core.models import (
    CompanyJob,
    Deliverable,
    Handoff,
    JobResult,
    JobType,
    LlmSettings,
    ManagerPlan,
    MaterialSummary,
    ProjectCard,
    ReassignmentAction,
    ResearcherProfile,
    ReviewDecision,
    TaskCard,
    TaskPlan,
    WorkOrder,
)
from clawlab.prompts.planning import build_manager_plan_prompts
from clawlab.services.asset_service import retrieve_assets_for_task
from clawlab.services.context_service import (
    get_company_handbook_context,
    get_employee_playbook_context,
    get_recent_protocol_context,
)
from clawlab.services.employee_service import run_employee_task
from clawlab.services.llm_service import call_llm, is_llm_enabled
from clawlab.services.workspace_service import (
    get_job_dir,
    load_assets,
    load_material_summary,
    load_task,
    load_task_plan,
    save_company_job,
    save_handoff,
    save_job_result,
    save_manager_plan,
    save_reassignment_action,
    save_review_decision,
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
        sequence = ["literature_analyst", "project_manager", "draft_writer", "review_editor"]
    elif job_type == "paper-outline":
        sequence = ["project_manager", "literature_analyst", "draft_writer", "review_editor"]
    else:
        sequence = ["literature_analyst", "project_manager", "draft_writer", "review_editor"]
    return sequence


def create_manager_plan(
    *,
    job_type: JobType,
    boss_goal: str,
    project: ProjectCard,
    input_path: Path,
    revised_path: Path | None = None,
    profile: ResearcherProfile | None = None,
    llm_settings: LlmSettings | None = None,
) -> tuple[CompanyJob, ManagerPlan, list[WorkOrder]]:
    job = CompanyJob(
        id=create_id("job"),
        job_type=job_type,
        project_card_id=project.id,
        boss_goal=boss_goal,
        input_path=str(input_path),
        revised_path=str(revised_path) if revised_path else None,
    )
    expected_deliverables = {
        "literature_analyst": "Material summary",
        "project_manager": "Task plan",
        "draft_writer": "Draft markdown",
        "review_editor": "Review decision and revision report",
    }
    selected_employees = _employee_sequence(job_type, revised_path)
    final_output_strategy = "Produce a concise manager-level brief that explains employee outputs and points to the final artifact."
    if llm_settings and is_llm_enabled(llm_settings, "planning"):
        try:
            company_handbook_excerpt, _company_sources = get_company_handbook_context()
            playbook_excerpt, _playbook_sources = get_employee_playbook_context("project_manager")
            protocol_excerpt, _protocol_sources = get_recent_protocol_context(
                project_id=project.id,
                employee_role="project_manager",
            )
            system_prompt, user_prompt = build_manager_plan_prompts(
                job_type=job_type,
                boss_goal=boss_goal,
                profile=profile,
                project=project,
                company_handbook_excerpt=company_handbook_excerpt,
                employee_playbook_excerpt=playbook_excerpt,
                recent_protocol_excerpt=protocol_excerpt,
            )
            payload = json.loads(
                call_llm(
                    settings=llm_settings,
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.15,
                    max_tokens=800,
                )
            )
            candidate_roles = [
                role for role in payload.get("selected_employees", [])
                if role in {"literature_analyst", "project_manager", "draft_writer", "review_editor"}
            ]
            if candidate_roles:
                if "review_editor" not in candidate_roles:
                    candidate_roles.append("review_editor")
                selected_employees = candidate_roles
            llm_deliverables = payload.get("expected_deliverables", [])
            if llm_deliverables and len(llm_deliverables) == len(selected_employees):
                expected_deliverables = {
                    role: llm_deliverables[index]
                    for index, role in enumerate(selected_employees)
                }
            final_output_strategy = payload.get("final_output_strategy", final_output_strategy)
        except Exception:
            pass

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
        final_output_strategy=final_output_strategy,
    )
    return job, plan, work_orders


def _create_handoff(
    *,
    from_role: str,
    to_role: str,
    source_deliverable: Deliverable,
    material_summaries: list[MaterialSummary],
    task_plan: TaskPlan | None,
    latest_task: TaskCard | None,
) -> Handoff:
    if from_role == "literature_analyst" and material_summaries:
        summary = material_summaries[0]
        handoff_summary = (
            f"Material summary ready: {summary.title}. "
            f"Key topics: {', '.join(summary.key_topics[:4])}. "
            f"Relevant snippets: {' | '.join(summary.useful_snippets[:2])}. "
            f"Relevance: {summary.relevance_to_project}"
        )
        contract_type = "material_brief"
        payload: dict[str, object] = {
            "material_title": summary.title,
            "key_topics": summary.key_topics[:5],
            "relevant_snippets": summary.useful_snippets[:3],
            "relevance_note": summary.relevance_to_project,
        }
        expected_use = "Use the material summary, key topics, snippets, and relevance note to plan the next step."
    elif from_role == "project_manager" and task_plan is not None:
        handoff_summary = (
            f"Task focus: {task_plan.task_goal}. "
            f"Recommended structure: {' | '.join(task_plan.recommended_structure[:4])}. "
            f"Selected assets: {' | '.join(task_plan.selected_assets[:3])}. "
            f"Project constraints: {' | '.join(task_plan.project_considerations[:3])}"
        )
        contract_type = "planning_brief"
        payload = {
            "task_focus": task_plan.task_goal,
            "recommended_structure": task_plan.recommended_structure[:5],
            "selected_assets": task_plan.selected_assets[:4],
            "project_constraints": task_plan.project_considerations[:4],
        }
        expected_use = "Use the task focus, structure, selected assets, and project constraints when drafting."
    elif from_role == "draft_writer" and latest_task is not None:
        handoff_summary = (
            f"Draft produced at {latest_task.generated_draft_path}. "
            f"Outline summary: {latest_task.input_summary}. "
            "Open weaknesses to inspect: gap clarity, structure quality, and evidence placement."
        )
        contract_type = "draft_review"
        payload = {
            "draft_path": latest_task.generated_draft_path,
            "outline_summary": latest_task.input_summary,
            "open_weaknesses": ["gap clarity", "structure quality", "evidence placement"],
        }
        expected_use = "Review the draft for structural clarity, explicit gap statement, and missing context."
    else:
        handoff_summary = f"Deliverable ready: {source_deliverable.title}"
        contract_type = "generic"
        payload = {
            "deliverable_title": source_deliverable.title,
            "deliverable_summary": source_deliverable.summary,
        }
        expected_use = "Consume the previous deliverable in the next work step."

    return Handoff(
        id=create_id("handoff"),
        from_role=from_role,  # type: ignore[arg-type]
        to_role=to_role,  # type: ignore[arg-type]
        source_deliverable_id=source_deliverable.id,
        contract_type=contract_type,  # type: ignore[arg-type]
        handoff_summary=handoff_summary,
        payload=payload,
        expected_use=expected_use,
    )


def _create_review_decision(
    *,
    target_deliverable: Deliverable,
    draft_text: str,
) -> ReviewDecision:
    suggestions: list[str] = []
    decision = "accept"
    rationale = "The draft is structurally clear enough to move into final synthesis."
    issue_type = "none"
    risk_level = "low"
    review_checks = {
        "material_grounding": "pass",
        "structure_clarity": "pass",
        "gap_explicitness": "pass",
    }

    if len(draft_text) < 350:
        decision = "escalate"
        rationale = "The produced draft is too thin; this usually indicates insufficient material grounding."
        suggestions = ["Add stronger material evidence before final synthesis.", "Clarify whether source materials are sufficient."]
        issue_type = "material_insufficiency"
        risk_level = "high"
        review_checks["material_grounding"] = "fail"
    elif draft_text.count("##") < 2:
        decision = "revise"
        rationale = "The draft needs clearer section hierarchy before it can be accepted."
        suggestions = ["Add clearer section headings.", "Separate framing, evidence, and gap more explicitly."]
        issue_type = "structure_problem"
        risk_level = "medium"
        review_checks["structure_clarity"] = "revise"
    elif "gap" not in draft_text.lower():
        decision = "revise"
        rationale = "The project-specific gap is still not explicit enough."
        suggestions = ["State the research gap explicitly.", "Tie the gap back to the active mission."]
        issue_type = "project_context_gap"
        risk_level = "medium"
        review_checks["gap_explicitness"] = "revise"

    return ReviewDecision(
        id=create_id("review"),
        reviewer_role="review_editor",
        target_deliverable_id=target_deliverable.id,
        decision=decision,  # type: ignore[arg-type]
        rationale=rationale,
        issue_type=issue_type,  # type: ignore[arg-type]
        risk_level=risk_level,  # type: ignore[arg-type]
        review_checks=review_checks,
        suggested_revisions=suggestions,
    )


def _manager_intervention_for_review(review_decision: ReviewDecision) -> tuple[str, str, str]:
    if review_decision.issue_type == "material_insufficiency":
        return (
            "literature_analyst",
            "recover_material_grounding",
            "Manager requests stronger evidence extraction before drafting again.",
        )
    if review_decision.issue_type == "structure_problem":
        return (
            "project_manager",
            "repair_structure_plan",
            "Manager requests a tighter structure plan before rewriting the draft.",
        )
    if review_decision.issue_type == "project_context_gap":
        return (
            "project_manager",
            "clarify_project_context",
            "Manager requests clearer project framing and gap articulation before rewriting.",
        )
    return (
        "project_manager",
        "generic_manager_recovery",
        "Manager triggers a generic recovery step before a final rewrite.",
    )


def _consume_pending_handoff(
    *,
    handoffs: list[Handoff],
    receiving_role: str,
    job_id: str,
) -> None:
    for index in range(len(handoffs) - 1, -1, -1):
        handoff = handoffs[index]
        if handoff.to_role == receiving_role and handoff.status == "created":
            consumed = handoff.model_copy(update={"status": "consumed"})
            handoffs[index] = consumed
            save_handoff(job_id, consumed)
            return


def _save_review_report(job_id: str, review_decision: ReviewDecision) -> Path:
    output_path = get_job_dir(job_id) / f"{review_decision.id}_review.md"
    write_text(
        output_path,
        "\n".join(
            [
                "# Review Decision",
                "",
                f"- decision: {review_decision.decision}",
                f"- issue_type: {review_decision.issue_type}",
                f"- risk_level: {review_decision.risk_level}",
                f"- rationale: {review_decision.rationale}",
                "",
                "## Review Checks",
                *[f"- {name}: {status}" for name, status in review_decision.review_checks.items()],
                "",
                "## Suggested Revisions",
                *[f"- {item}" for item in review_decision.suggested_revisions],
                "",
            ]
        ),
    )
    return output_path


def dispatch_work_orders(
    *,
    job: CompanyJob,
    plan: ManagerPlan,
    work_orders: list[WorkOrder],
    profile: ResearcherProfile,
    project: ProjectCard,
    llm_settings: LlmSettings | None = None,
) -> tuple[list[Deliverable], list[Handoff], list[ReviewDecision], list[ReassignmentAction], str]:
    save_company_job(job)
    save_manager_plan(job.id, plan)

    deliverables: list[Deliverable] = []
    handoffs: list[Handoff] = []
    review_decisions: list[ReviewDecision] = []
    reassignments: list[ReassignmentAction] = []
    material_summaries: list[MaterialSummary] = []
    task_plan: TaskPlan | None = None
    latest_task: TaskCard | None = None
    latest_draft_deliverable: Deliverable | None = None
    final_status = "accepted_directly"

    for index, work_order in enumerate(work_orders):
        _consume_pending_handoff(
            handoffs=handoffs,
            receiving_role=work_order.employee_role,
            job_id=job.id,
        )
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
                manager_plan=plan,
                work_order=work_order,
                llm_settings=llm_settings,
            )
            latest_task = load_task(deliverable.source_task_id or "")
            latest_draft_deliverable = deliverable
        elif work_order.employee_role == "review_editor":
            if latest_task is None or latest_draft_deliverable is None:
                work_order = work_order.model_copy(update={"status": "failed"})
                save_work_order(job.id, work_order)
                continue
            draft_text = Path(latest_draft_deliverable.output_path).read_text(encoding="utf-8")
            review_decision = _create_review_decision(
                target_deliverable=latest_draft_deliverable,
                draft_text=draft_text,
            )
            save_review_decision(job.id, review_decision)
            review_decisions.append(review_decision)
            review_report_path = _save_review_report(job.id, review_decision)
            deliverable = Deliverable(
                id=create_id("deliverable"),
                employee_role="review_editor",
                source_task_id=latest_task.id,
                source_work_order_id=work_order.id,
                title="Review Editor: review decision",
                summary=f"{review_decision.decision}: {review_decision.rationale}",
                output_path=str(review_report_path.relative_to(Path.cwd())),
            )

            if review_decision.decision == "revise":
                retry_work_order = WorkOrder(
                    id=create_id("workorder"),
                    employee_role="draft_writer",
                    project_card_id=project.id,
                    task_type=JOB_TASK_TYPE_MAP[job.job_type],  # type: ignore[arg-type]
                    task_goal=f"{work_order.task_goal} | revise once based on review suggestions",
                    input_context_refs=[latest_draft_deliverable.output_path],
                    expected_output="Revised draft markdown",
                    status="running",
                )
                save_work_order(job.id, retry_work_order)
                revised_plan = task_plan.model_copy(
                    update={
                        "project_considerations": [
                            *(task_plan.project_considerations if task_plan else []),
                            *review_decision.suggested_revisions,
                        ]
                    }
                ) if task_plan else None
                retry_deliverable = run_employee_task(
                    "draft_writer",
                    profile=profile,
                    project=project,
                    task_type=JOB_TASK_TYPE_MAP[job.job_type],
                    material_summaries=material_summaries,
                    task_plan=revised_plan,
                    manager_plan=plan,
                    work_order=retry_work_order,
                    llm_settings=llm_settings,
                )
                retry_work_order = retry_work_order.model_copy(update={"status": "completed"})
                save_work_order(job.id, retry_work_order)
                deliverables.append(retry_deliverable)
                latest_draft_deliverable = retry_deliverable
                latest_task = load_task(retry_deliverable.source_task_id or "")
                revised_handoff = _create_handoff(
                    from_role="draft_writer",
                    to_role="review_editor",
                    source_deliverable=retry_deliverable,
                    material_summaries=material_summaries,
                    task_plan=task_plan,
                    latest_task=latest_task,
                )
                save_handoff(job.id, revised_handoff)
                handoffs.append(revised_handoff)
                second_review = _create_review_decision(
                    target_deliverable=retry_deliverable,
                    draft_text=Path(retry_deliverable.output_path).read_text(encoding="utf-8"),
                )
                save_review_decision(job.id, second_review)
                review_decisions.append(second_review)
                second_review_report_path = _save_review_report(job.id, second_review)
                second_review_deliverable = Deliverable(
                    id=create_id("deliverable"),
                    employee_role="review_editor",
                    source_task_id=latest_task.id if latest_task else None,
                    source_work_order_id=work_order.id,
                    title="Review Editor: retry review decision",
                    summary=f"{second_review.decision}: {second_review.rationale}",
                    output_path=str(second_review_report_path.relative_to(Path.cwd())),
                )
                deliverables.append(second_review_deliverable)
                if second_review.decision == "accept":
                    final_status = "revised_then_accepted"
                else:
                    final_status = "escalated_with_risk"
            elif review_decision.decision == "escalate":
                reassigned_to, intervention_policy, resolution_note = _manager_intervention_for_review(review_decision)
                reassignment = ReassignmentAction(
                    id=create_id("reassign"),
                    job_id=job.id,
                    manager_plan_id=plan.id,
                    original_work_order_id=work_order.id,
                    reassigned_to=reassigned_to,  # type: ignore[arg-type]
                    reason=review_decision.rationale,
                    trigger_review_decision_id=review_decision.id,
                    intervention_policy=intervention_policy,
                    resolution_note=resolution_note,
                )
                save_reassignment_action(job.id, reassignment)
                reassignments.append(reassignment)

                reassigned_work_order = WorkOrder(
                    id=create_id("workorder"),
                    employee_role=reassigned_to,  # type: ignore[arg-type]
                    project_card_id=project.id,
                    task_type=JOB_TASK_TYPE_MAP[job.job_type],  # type: ignore[arg-type]
                    task_goal=f"Escalated follow-up: {review_decision.rationale}",
                    input_context_refs=[latest_draft_deliverable.output_path],
                    expected_output="Manager-requested remediation output",
                    status="running",
                )
                save_work_order(job.id, reassigned_work_order)
                if reassigned_to == "literature_analyst":
                    remedial_deliverable = run_employee_task(
                        "literature_analyst",
                        project=project,
                        input_path=Path(job.input_path or ""),
                        work_order=reassigned_work_order,
                        llm_settings=llm_settings,
                    )
                    remedial_summary = load_material_summary(remedial_deliverable.output_path)
                    if remedial_summary:
                        material_summaries = [remedial_summary]
                else:
                    remedial_deliverable = run_employee_task(
                        "project_manager",
                        profile=profile,
                        project=project,
                        task_type=JOB_TASK_TYPE_MAP[job.job_type],
                        input_path=Path(job.input_path or "") if job.input_path else None,
                        material_summaries=material_summaries,
                        work_order=reassigned_work_order,
                        llm_settings=llm_settings,
                    )
                    task_plan = load_task_plan(remedial_deliverable.output_path)
                reassigned_work_order = reassigned_work_order.model_copy(update={"status": "completed"})
                save_work_order(job.id, reassigned_work_order)
                deliverables.append(remedial_deliverable)
                remediation_handoff = _create_handoff(
                    from_role=reassigned_to,
                    to_role="draft_writer",
                    source_deliverable=remedial_deliverable,
                    material_summaries=material_summaries,
                    task_plan=task_plan,
                    latest_task=latest_task,
                )
                save_handoff(job.id, remediation_handoff)
                handoffs.append(remediation_handoff)

                followup_draft_work_order = WorkOrder(
                    id=create_id("workorder"),
                    employee_role="draft_writer",
                    project_card_id=project.id,
                    task_type=JOB_TASK_TYPE_MAP[job.job_type],  # type: ignore[arg-type]
                    task_goal=f"Follow-up draft after escalation: {review_decision.rationale}",
                    input_context_refs=[remedial_deliverable.output_path],
                    expected_output="Revised draft markdown",
                    status="running",
                )
                reassignment = reassignment.model_copy(update={"follow_up_work_order_id": followup_draft_work_order.id})
                save_reassignment_action(job.id, reassignment)
                reassignments[-1] = reassignment
                save_work_order(job.id, followup_draft_work_order)
                followup_draft = run_employee_task(
                    "draft_writer",
                    profile=profile,
                    project=project,
                    task_type=JOB_TASK_TYPE_MAP[job.job_type],
                    material_summaries=material_summaries,
                    task_plan=task_plan,
                    manager_plan=plan,
                    work_order=followup_draft_work_order,
                    llm_settings=llm_settings,
                )
                followup_draft_work_order = followup_draft_work_order.model_copy(update={"status": "completed"})
                save_work_order(job.id, followup_draft_work_order)
                deliverables.append(followup_draft)
                latest_draft_deliverable = followup_draft
                latest_task = load_task(followup_draft.source_task_id or "")
                final_status = "escalated_with_risk"
            else:
                final_status = "accepted_directly"
        else:
            raise ValueError(f"Unsupported employee role in manager dispatch: {work_order.employee_role}")

        deliverables.append(deliverable)
        work_order = work_order.model_copy(update={"status": "completed"})
        save_work_order(job.id, work_order)

        if index + 1 < len(work_orders):
            next_role = work_orders[index + 1].employee_role
            handoff = _create_handoff(
                from_role=work_order.employee_role,
                to_role=next_role,
                source_deliverable=deliverable,
                material_summaries=material_summaries,
                task_plan=task_plan,
                latest_task=latest_task,
            )
            save_handoff(job.id, handoff)
            handoffs.append(handoff)

    return deliverables, handoffs, review_decisions, reassignments, final_status


def collect_deliverables(deliverables: list[Deliverable]) -> list[Deliverable]:
    return deliverables


def synthesize_job_result(
    *,
    job: CompanyJob,
    plan: ManagerPlan,
    deliverables: list[Deliverable],
    handoffs: list[Handoff],
    review_decisions: list[ReviewDecision],
    reassignments: list[ReassignmentAction],
    final_status: str,
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
    if handoffs:
        lines.extend(["", "## Handoffs"])
        for handoff in handoffs:
            lines.append(
                f"- {handoff.from_role} -> {handoff.to_role} [{handoff.contract_type}/{handoff.status}]: "
                f"{handoff.handoff_summary}"
            )
    if review_decisions:
        lines.extend(["", "## Reviews"])
        for review in review_decisions:
            lines.append(
                f"- {review.reviewer_role}: {review.decision} [{review.issue_type}/{review.risk_level}] | "
                f"{review.rationale}"
            )
    if reassignments:
        lines.extend(["", "## Reassignments"])
        for action in reassignments:
            lines.append(
                f"- {action.original_work_order_id} -> {action.reassigned_to} "
                f"[{action.intervention_policy or 'n/a'}]: {action.reason}"
            )
    lines.extend(
        [
            "",
            "## Final Output Strategy",
            plan.final_output_strategy,
            "",
            "## Manager Summary",
            "The final result is synthesized from the employee chain above, including handoff, review, and retry/reassign actions where needed.",
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
        handoff_ids=[handoff.id for handoff in handoffs],
        review_decision_ids=[review.id for review in review_decisions],
        reassignment_ids=[action.id for action in reassignments],
        final_status=final_status,  # type: ignore[arg-type]
        summary=(
            f"Executed {len(deliverables)} deliverable(s), {len(handoffs)} handoff(s), "
            f"{len(review_decisions)} review(s), and {len(reassignments)} reassignment(s)."
        ),
    )
    save_job_result(job.id, result)
    return result
