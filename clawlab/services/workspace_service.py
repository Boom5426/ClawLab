from __future__ import annotations

from pathlib import Path

from clawlab.core.constants import (
    ASSETS_INDEX_FILENAME,
    DEFAULT_CONFIG_NAME,
    DEFAULT_WORKSPACE_ROOT,
    PROFILE_FILENAME,
    PROJECT_FILENAME,
    TASK_FILENAME,
    TASKS_INDEX_FILENAME,
)
from clawlab.core.models import (
    CompanyJob,
    CompanyProfile,
    Deliverable,
    FounderProfile,
    Handoff,
    JobResult,
    ManagerPlan,
    MaterialSummary,
    ProjectCard,
    ResearcherProfile,
    ReusableAsset,
    TaskCard,
    TaskPlan,
    TeamConfig,
    ReassignmentAction,
    ReviewDecision,
    WorkOrder,
    WorkspaceConfig,
    WorkspaceState,
)
from clawlab.storage.filesystem import ensure_directory, read_json, read_model, write_json, write_model, write_text


ASSET_MARKDOWN_DIRS = {
    "writing_rule": "writing-rules",
    "structure_template": "templates",
    "project_note": "project-notes",
    "common_mistake": "common-mistakes",
    "sop_seed": "sop-seeds",
}


def get_repo_root() -> Path:
    return Path.cwd()


def get_workspace_root(repo_root: Path | None = None) -> Path:
    base = repo_root or get_repo_root()
    return base / DEFAULT_WORKSPACE_ROOT


def get_config_path(repo_root: Path | None = None) -> Path:
    base = repo_root or get_repo_root()
    return base / DEFAULT_CONFIG_NAME


def load_config(repo_root: Path | None = None) -> WorkspaceConfig:
    config_path = get_config_path(repo_root)
    if config_path.exists():
        return WorkspaceConfig.model_validate(read_json(config_path))
    return WorkspaceConfig()


def save_config(config: WorkspaceConfig, repo_root: Path | None = None) -> Path:
    config_path = get_config_path(repo_root)
    write_model(config_path, config)
    return config_path


def init_workspace(repo_root: Path | None = None) -> WorkspaceConfig:
    workspace_root = get_workspace_root(repo_root)
    ensure_directory(workspace_root / "profile")
    ensure_directory(workspace_root / "projects")
    ensure_directory(workspace_root / "assets")
    ensure_directory(workspace_root / "tasks")
    ensure_directory(workspace_root / "jobs")
    ensure_directory(workspace_root / "company")
    ensure_directory(get_company_handbook_root(repo_root))
    ensure_directory(get_employee_playbooks_root(repo_root))
    for directory in ASSET_MARKDOWN_DIRS.values():
        ensure_directory(workspace_root / "assets" / directory)
        ensure_directory(get_company_handbook_root(repo_root) / directory)

    config = WorkspaceConfig(workspace_root=str(workspace_root.relative_to(repo_root or get_repo_root())))
    save_config(config, repo_root)
    write_json(workspace_root / "tasks" / TASKS_INDEX_FILENAME, [])
    write_json(workspace_root / "assets" / ASSETS_INDEX_FILENAME, [])
    return config


def get_profile_path(repo_root: Path | None = None) -> Path:
    return get_workspace_root(repo_root) / "profile" / PROFILE_FILENAME


def get_company_root(repo_root: Path | None = None) -> Path:
    return get_workspace_root(repo_root) / "company"


def get_founder_profile_path(repo_root: Path | None = None) -> Path:
    return get_company_root(repo_root) / "founder_profile.json"


def get_company_profile_path(repo_root: Path | None = None) -> Path:
    return get_company_root(repo_root) / "company_profile.json"


def get_team_config_path(repo_root: Path | None = None) -> Path:
    return get_company_root(repo_root) / "team_config.json"


def get_projects_root(repo_root: Path | None = None) -> Path:
    return get_workspace_root(repo_root) / "projects"


def get_project_dir(project_id: str, repo_root: Path | None = None) -> Path:
    return get_projects_root(repo_root) / project_id


def get_project_path(project_id: str, repo_root: Path | None = None) -> Path:
    return get_project_dir(project_id, repo_root) / PROJECT_FILENAME


def get_outputs_dir(project_id: str, repo_root: Path | None = None) -> Path:
    return get_project_dir(project_id, repo_root) / "outputs"


def get_project_assets_dir(project_id: str, repo_root: Path | None = None) -> Path:
    return get_project_dir(project_id, repo_root) / "assets"


def get_project_materials_dir(project_id: str, repo_root: Path | None = None) -> Path:
    return get_project_dir(project_id, repo_root) / "materials"


def get_project_deliverables_dir(project_id: str, repo_root: Path | None = None) -> Path:
    return get_project_dir(project_id, repo_root) / "deliverables"


def get_material_summary_path(project_id: str, summary_id: str, repo_root: Path | None = None) -> Path:
    return get_project_materials_dir(project_id, repo_root) / f"{summary_id}.json"


def get_deliverable_path(project_id: str, deliverable_id: str, repo_root: Path | None = None) -> Path:
    return get_project_deliverables_dir(project_id, repo_root) / f"{deliverable_id}.json"


def get_tasks_root(repo_root: Path | None = None) -> Path:
    return get_workspace_root(repo_root) / "tasks"


def get_jobs_root(repo_root: Path | None = None) -> Path:
    return get_workspace_root(repo_root) / "jobs"


def get_job_dir(job_id: str, repo_root: Path | None = None) -> Path:
    return get_jobs_root(repo_root) / job_id


def get_job_path(job_id: str, repo_root: Path | None = None) -> Path:
    return get_job_dir(job_id, repo_root) / "job.json"


def get_manager_plan_path(job_id: str, repo_root: Path | None = None) -> Path:
    return get_job_dir(job_id, repo_root) / "manager_plan.json"


def get_work_orders_dir(job_id: str, repo_root: Path | None = None) -> Path:
    return get_job_dir(job_id, repo_root) / "work_orders"


def get_work_order_path(job_id: str, work_order_id: str, repo_root: Path | None = None) -> Path:
    return get_work_orders_dir(job_id, repo_root) / f"{work_order_id}.json"


def get_job_result_path(job_id: str, repo_root: Path | None = None) -> Path:
    return get_job_dir(job_id, repo_root) / "job_result.json"


def get_handoffs_dir(job_id: str, repo_root: Path | None = None) -> Path:
    return get_job_dir(job_id, repo_root) / "handoffs"


def get_handoff_path(job_id: str, handoff_id: str, repo_root: Path | None = None) -> Path:
    return get_handoffs_dir(job_id, repo_root) / f"{handoff_id}.json"


def get_reviews_dir(job_id: str, repo_root: Path | None = None) -> Path:
    return get_job_dir(job_id, repo_root) / "reviews"


def get_review_path(job_id: str, review_id: str, repo_root: Path | None = None) -> Path:
    return get_reviews_dir(job_id, repo_root) / f"{review_id}.json"


def get_reassignments_dir(job_id: str, repo_root: Path | None = None) -> Path:
    return get_job_dir(job_id, repo_root) / "reassignments"


def get_reassignment_path(job_id: str, reassignment_id: str, repo_root: Path | None = None) -> Path:
    return get_reassignments_dir(job_id, repo_root) / f"{reassignment_id}.json"


def get_task_path(task_id: str, repo_root: Path | None = None) -> Path:
    return get_tasks_root(repo_root) / task_id / TASK_FILENAME


def get_task_plan_path(task_id: str, repo_root: Path | None = None) -> Path:
    return get_tasks_root(repo_root) / task_id / "task_plan.json"


def get_assets_root(repo_root: Path | None = None) -> Path:
    return get_workspace_root(repo_root) / "assets"


def get_company_handbook_root(repo_root: Path | None = None) -> Path:
    return get_company_root(repo_root) / "handbook"


def get_employee_playbooks_root(repo_root: Path | None = None) -> Path:
    return get_company_root(repo_root) / "employee_playbooks"


def get_employee_playbook_dir(employee_role: str, repo_root: Path | None = None) -> Path:
    return get_employee_playbooks_root(repo_root) / employee_role


def get_asset_path(asset_id: str, repo_root: Path | None = None) -> Path:
    return get_assets_root(repo_root) / f"{asset_id}.json"


def get_asset_markdown_path(asset: ReusableAsset, repo_root: Path | None = None) -> Path:
    directory = ASSET_MARKDOWN_DIRS[asset.asset_type]
    return get_assets_root(repo_root) / directory / f"{asset.id}.md"


def get_company_handbook_asset_path(asset: ReusableAsset, repo_root: Path | None = None) -> Path:
    directory = ASSET_MARKDOWN_DIRS[asset.asset_type]
    return get_company_handbook_root(repo_root) / directory / f"{asset.id}.md"


def get_employee_playbook_asset_path(asset: ReusableAsset, repo_root: Path | None = None) -> Path:
    if not asset.employee_role:
        raise ValueError("employee-scoped asset requires employee_role")
    directory = ASSET_MARKDOWN_DIRS[asset.asset_type]
    return get_employee_playbook_dir(asset.employee_role, repo_root) / directory / f"{asset.id}.md"


def get_project_notes_dir(project_id: str, repo_root: Path | None = None) -> Path:
    return get_project_dir(project_id, repo_root) / "notes"


def get_project_asset_markdown_path(project_id: str, asset: ReusableAsset, repo_root: Path | None = None) -> Path:
    if asset.asset_type == "project_note":
        return get_project_notes_dir(project_id, repo_root) / f"{asset.id}.md"
    return get_project_assets_dir(project_id, repo_root) / f"{asset.id}.md"


def _render_asset_markdown(asset: ReusableAsset) -> str:
    return "\n".join(
        [
            f"# {asset.title}",
            "",
            f"- asset_type: {asset.asset_type}",
            f"- scope: {asset.scope}",
            f"- confidence: {asset.confidence:.2f}",
            f"- source_task_id: {asset.source_task_id}",
            f"- employee_role: {asset.employee_role or 'n/a'}",
            f"- created_at: {asset.created_at}",
            "",
            "## Content",
            asset.content,
            "",
        ]
    )


def save_profile(profile: ResearcherProfile, repo_root: Path | None = None) -> Path:
    path = get_profile_path(repo_root)
    write_model(path, profile)
    return path


def save_founder_profile(founder_profile: FounderProfile, repo_root: Path | None = None) -> Path:
    path = get_founder_profile_path(repo_root)
    write_model(path, founder_profile)
    return path


def load_founder_profile(repo_root: Path | None = None) -> FounderProfile | None:
    path = get_founder_profile_path(repo_root)
    if not path.exists():
        return None
    return read_model(path, FounderProfile)


def save_company_profile(company_profile: CompanyProfile, repo_root: Path | None = None) -> Path:
    path = get_company_profile_path(repo_root)
    write_model(path, company_profile)
    return path


def load_company_profile(repo_root: Path | None = None) -> CompanyProfile | None:
    path = get_company_profile_path(repo_root)
    if not path.exists():
        return None
    return read_model(path, CompanyProfile)


def save_team_config(team_config: TeamConfig, repo_root: Path | None = None) -> Path:
    path = get_team_config_path(repo_root)
    write_model(path, team_config)
    return path


def load_team_config(repo_root: Path | None = None) -> TeamConfig | None:
    path = get_team_config_path(repo_root)
    if not path.exists():
        return None
    return read_model(path, TeamConfig)


def load_profile(repo_root: Path | None = None) -> ResearcherProfile | None:
    path = get_profile_path(repo_root)
    if not path.exists():
        return None
    return read_model(path, ResearcherProfile)


def save_project(project: ProjectCard, repo_root: Path | None = None) -> Path:
    project_dir = get_project_dir(project.id, repo_root)
    ensure_directory(project_dir)
    ensure_directory(get_outputs_dir(project.id, repo_root))
    ensure_directory(get_project_assets_dir(project.id, repo_root))
    ensure_directory(get_project_materials_dir(project.id, repo_root))
    ensure_directory(get_project_deliverables_dir(project.id, repo_root))
    ensure_directory(get_project_notes_dir(project.id, repo_root))
    path = get_project_path(project.id, repo_root)
    write_model(path, project)
    config = load_config(repo_root)
    config.active_project_id = project.id
    save_config(config, repo_root)
    return path


def load_project(project_id: str, repo_root: Path | None = None) -> ProjectCard | None:
    path = get_project_path(project_id, repo_root)
    if not path.exists():
        return None
    return read_model(path, ProjectCard)


def load_active_project(repo_root: Path | None = None) -> ProjectCard | None:
    config = load_config(repo_root)
    if not config.active_project_id:
        return None
    return load_project(config.active_project_id, repo_root)


def save_task(task: TaskCard, repo_root: Path | None = None) -> Path:
    task_dir = get_tasks_root(repo_root) / task.id
    ensure_directory(task_dir)
    path = get_task_path(task.id, repo_root)
    write_model(path, task)

    index_path = get_tasks_root(repo_root) / TASKS_INDEX_FILENAME
    existing = read_json(index_path) if index_path.exists() else []
    existing = [item for item in existing if item.get("id") != task.id]
    existing.insert(0, task.model_dump())
    write_json(index_path, existing)
    return path


def save_company_job(job: CompanyJob, repo_root: Path | None = None) -> Path:
    job_dir = get_job_dir(job.id, repo_root)
    ensure_directory(job_dir)
    ensure_directory(get_work_orders_dir(job.id, repo_root))
    ensure_directory(get_handoffs_dir(job.id, repo_root))
    ensure_directory(get_reviews_dir(job.id, repo_root))
    ensure_directory(get_reassignments_dir(job.id, repo_root))
    path = get_job_path(job.id, repo_root)
    write_model(path, job)
    return path


def load_company_job(job_id: str, repo_root: Path | None = None) -> CompanyJob | None:
    path = get_job_path(job_id, repo_root)
    if not path.exists():
        return None
    return read_model(path, CompanyJob)


def save_manager_plan(job_id: str, plan: ManagerPlan, repo_root: Path | None = None) -> Path:
    job_dir = get_job_dir(job_id, repo_root)
    ensure_directory(job_dir)
    ensure_directory(get_work_orders_dir(job_id, repo_root))
    ensure_directory(get_handoffs_dir(job_id, repo_root))
    ensure_directory(get_reviews_dir(job_id, repo_root))
    ensure_directory(get_reassignments_dir(job_id, repo_root))
    path = get_manager_plan_path(job_id, repo_root)
    write_model(path, plan)
    return path


def load_manager_plan(path: str | Path, repo_root: Path | None = None) -> ManagerPlan | None:
    plan_path = Path(path)
    if not plan_path.is_absolute():
        plan_path = (repo_root or get_repo_root()) / plan_path
    if not plan_path.exists():
        return None
    return read_model(plan_path, ManagerPlan)


def save_work_order(job_id: str, work_order: WorkOrder, repo_root: Path | None = None) -> Path:
    ensure_directory(get_work_orders_dir(job_id, repo_root))
    path = get_work_order_path(job_id, work_order.id, repo_root)
    write_model(path, work_order)
    return path


def load_work_orders(job_id: str, repo_root: Path | None = None) -> list[WorkOrder]:
    directory = get_work_orders_dir(job_id, repo_root)
    if not directory.exists():
        return []
    return [read_model(path, WorkOrder) for path in sorted(directory.glob("*.json"))]


def save_job_result(job_id: str, result: JobResult, repo_root: Path | None = None) -> Path:
    job_dir = get_job_dir(job_id, repo_root)
    ensure_directory(job_dir)
    path = get_job_result_path(job_id, repo_root)
    write_model(path, result)
    return path


def save_handoff(job_id: str, handoff: Handoff, repo_root: Path | None = None) -> Path:
    ensure_directory(get_handoffs_dir(job_id, repo_root))
    path = get_handoff_path(job_id, handoff.id, repo_root)
    write_model(path, handoff)
    return path


def load_handoffs(job_id: str, repo_root: Path | None = None) -> list[Handoff]:
    directory = get_handoffs_dir(job_id, repo_root)
    if not directory.exists():
        return []
    return [read_model(path, Handoff) for path in sorted(directory.glob("*.json"))]


def save_review_decision(job_id: str, review_decision: ReviewDecision, repo_root: Path | None = None) -> Path:
    ensure_directory(get_reviews_dir(job_id, repo_root))
    path = get_review_path(job_id, review_decision.id, repo_root)
    write_model(path, review_decision)
    return path


def load_review_decisions(job_id: str, repo_root: Path | None = None) -> list[ReviewDecision]:
    directory = get_reviews_dir(job_id, repo_root)
    if not directory.exists():
        return []
    return [read_model(path, ReviewDecision) for path in sorted(directory.glob("*.json"))]


def save_reassignment_action(job_id: str, action: ReassignmentAction, repo_root: Path | None = None) -> Path:
    ensure_directory(get_reassignments_dir(job_id, repo_root))
    path = get_reassignment_path(job_id, action.id, repo_root)
    write_model(path, action)
    return path


def load_reassignment_actions(job_id: str, repo_root: Path | None = None) -> list[ReassignmentAction]:
    directory = get_reassignments_dir(job_id, repo_root)
    if not directory.exists():
        return []
    return [read_model(path, ReassignmentAction) for path in sorted(directory.glob("*.json"))]


def load_job_result(path: str | Path, repo_root: Path | None = None) -> JobResult | None:
    result_path = Path(path)
    if not result_path.is_absolute():
        result_path = (repo_root or get_repo_root()) / result_path
    if not result_path.exists():
        return None
    return read_model(result_path, JobResult)


def load_jobs(repo_root: Path | None = None) -> list[CompanyJob]:
    root = get_jobs_root(repo_root)
    if not root.exists():
        return []
    jobs: list[CompanyJob] = []
    for path in sorted(root.glob("*/job.json"), reverse=True):
        jobs.append(read_model(path, CompanyJob))
    return jobs


def save_task_plan(task_id: str, plan: TaskPlan, repo_root: Path | None = None) -> Path:
    task_dir = get_tasks_root(repo_root) / task_id
    ensure_directory(task_dir)
    path = get_task_plan_path(task_id, repo_root)
    write_model(path, plan)
    return path


def load_task_plan(path: str | Path, repo_root: Path | None = None) -> TaskPlan | None:
    plan_path = Path(path)
    if not plan_path.is_absolute():
        plan_path = (repo_root or get_repo_root()) / plan_path
    if not plan_path.exists():
        return None
    return read_model(plan_path, TaskPlan)


def load_task(task_id: str, repo_root: Path | None = None) -> TaskCard | None:
    path = get_task_path(task_id, repo_root)
    if not path.exists():
        return None
    return read_model(path, TaskCard)


def load_tasks(repo_root: Path | None = None) -> list[TaskCard]:
    index_path = get_tasks_root(repo_root) / TASKS_INDEX_FILENAME
    if not index_path.exists():
        return []
    return [TaskCard.model_validate(item) for item in read_json(index_path)]


def save_asset(asset: ReusableAsset, repo_root: Path | None = None) -> Path:
    path = get_asset_path(asset.id, repo_root)
    write_model(path, asset)
    write_text(get_asset_markdown_path(asset, repo_root), _render_asset_markdown(asset))
    if asset.scope == "company":
        write_text(get_company_handbook_asset_path(asset, repo_root), _render_asset_markdown(asset))
    if asset.scope == "employee":
        employee_path = get_employee_playbook_asset_path(asset, repo_root)
        ensure_directory(employee_path.parent)
        write_text(employee_path, _render_asset_markdown(asset))

    index_path = get_assets_root(repo_root) / ASSETS_INDEX_FILENAME
    existing = read_json(index_path) if index_path.exists() else []
    existing = [item for item in existing if item.get("id") != asset.id]
    existing.insert(0, asset.model_dump())
    write_json(index_path, existing)
    return path


def save_project_asset(project_id: str, asset: ReusableAsset, repo_root: Path | None = None) -> Path:
    project_asset_path = get_project_assets_dir(project_id, repo_root) / f"{asset.id}.json"
    write_model(project_asset_path, asset)
    write_text(get_project_asset_markdown_path(project_id, asset, repo_root), _render_asset_markdown(asset))
    return project_asset_path


def save_material_summary(project_id: str, summary: MaterialSummary, repo_root: Path | None = None) -> Path:
    summary_path = get_material_summary_path(project_id, summary.id, repo_root)
    write_model(summary_path, summary)
    return summary_path


def save_deliverable(project_id: str, deliverable: Deliverable, repo_root: Path | None = None) -> Path:
    deliverable_path = get_deliverable_path(project_id, deliverable.id, repo_root)
    write_model(deliverable_path, deliverable)
    return deliverable_path


def load_project_deliverables(project_id: str, repo_root: Path | None = None) -> list[Deliverable]:
    directory = get_project_deliverables_dir(project_id, repo_root)
    if not directory.exists():
        return []
    return [read_model(path, Deliverable) for path in sorted(directory.glob("*.json"), reverse=True)]


def load_material_summary(path: str | Path, repo_root: Path | None = None) -> MaterialSummary | None:
    summary_path = Path(path)
    if not summary_path.is_absolute():
        summary_path = (repo_root or get_repo_root()) / summary_path
    if not summary_path.exists():
        return None
    return read_model(summary_path, MaterialSummary)


def load_assets(repo_root: Path | None = None) -> list[ReusableAsset]:
    index_path = get_assets_root(repo_root) / ASSETS_INDEX_FILENAME
    if not index_path.exists():
        return []
    normalized_items = []
    for item in read_json(index_path):
        if item.get("scope") == "global":
            item = {**item, "scope": "company"}
        normalized_items.append(item)
    return [ReusableAsset.model_validate(item) for item in normalized_items]


def load_company_handbook(repo_root: Path | None = None) -> list[Path]:
    root = get_company_handbook_root(repo_root)
    if not root.exists():
        return []
    return sorted(root.rglob("*.md"))


def load_employee_playbook(employee_role: str, repo_root: Path | None = None) -> list[Path]:
    root = get_employee_playbook_dir(employee_role, repo_root)
    if not root.exists():
        return []
    return sorted(root.rglob("*.md"))


def load_current_state(repo_root: Path | None = None) -> WorkspaceState:
    return WorkspaceState(
        profile=load_profile(repo_root),
        active_project=load_active_project(repo_root),
        tasks=load_tasks(repo_root),
        assets=load_assets(repo_root),
    )
