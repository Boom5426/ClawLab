from __future__ import annotations

from pathlib import Path

from clawlab.core.models import EmployeeRole, ProjectCard, ReusableAsset
from clawlab.services.workspace_service import (
    load_assets,
    load_company_handbook,
    load_employee_playbook,
    load_handoffs,
    load_jobs,
    load_reassignment_actions,
    load_review_decisions,
)


def _read_excerpt(paths: list[Path], *, max_files: int = 3, max_chars_per_file: int = 600) -> tuple[str, list[str]]:
    used_sources: list[str] = []
    chunks: list[str] = []
    for path in paths[:max_files]:
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not text:
            continue
        used_sources.append(path.name)
        chunks.append(f"[{path.name}]\n{text[:max_chars_per_file]}")
    return "\n\n".join(chunks), used_sources


def get_company_handbook_context() -> tuple[str, list[str]]:
    return _read_excerpt(load_company_handbook())


def get_employee_playbook_context(role: EmployeeRole) -> tuple[str, list[str]]:
    return _read_excerpt(load_employee_playbook(role))


def get_relevant_assets_context(
    *,
    project: ProjectCard | None = None,
    employee_role: EmployeeRole | None = None,
    limit: int = 4,
) -> tuple[str, list[str], list[ReusableAsset]]:
    all_assets = load_assets()
    filtered = [
        asset
        for asset in all_assets
        if (
            (project is None or asset.project_card_id in {None, project.id})
            and (employee_role is None or asset.employee_role in {None, employee_role})
        )
    ]
    selected = filtered[:limit]
    lines = [
        f"- {asset.scope}/{asset.asset_type}: {asset.title} => {asset.content[:220]}"
        for asset in selected
    ]
    source_labels = [f"asset:{asset.id}" for asset in selected]
    return "\n".join(lines), source_labels, selected


def get_recent_protocol_context(*, project_id: str | None = None, employee_role: EmployeeRole | None = None) -> tuple[str, list[str]]:
    jobs = load_jobs()
    lines: list[str] = []
    used_sources: list[str] = []
    for job in jobs[:4]:
        if project_id and job.project_card_id != project_id:
            continue
        reviews = load_review_decisions(job.id)
        handoffs = load_handoffs(job.id)
        reassignments = load_reassignment_actions(job.id)

        for review in reviews[-2:]:
            used_sources.append(f"review:{review.id}")
            lines.append(
                f"- review {review.id}: decision={review.decision}, issue_type={review.issue_type}, "
                f"risk={review.risk_level}, rationale={review.rationale}"
            )
        for handoff in handoffs[-2:]:
            if employee_role and employee_role not in {handoff.from_role, handoff.to_role}:
                continue
            used_sources.append(f"handoff:{handoff.id}")
            lines.append(
                f"- handoff {handoff.id}: {handoff.from_role}->{handoff.to_role}, "
                f"contract={handoff.contract_type}, status={handoff.status}"
            )
        for action in reassignments[-1:]:
            used_sources.append(f"reassign:{action.id}")
            lines.append(
                f"- reassignment {action.id}: to={action.reassigned_to}, "
                f"policy={action.intervention_policy or 'n/a'}, reason={action.reason}"
            )
    return "\n".join(lines[:12]), used_sources[:12]
