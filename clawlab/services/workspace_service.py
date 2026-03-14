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
    ProjectCard,
    ResearcherProfile,
    ReusableAsset,
    TaskCard,
    WorkspaceConfig,
    WorkspaceState,
)
from clawlab.storage.filesystem import ensure_directory, read_json, read_model, write_json, write_model


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

    config = WorkspaceConfig(workspace_root=str(workspace_root.relative_to(repo_root or get_repo_root())))
    save_config(config, repo_root)
    write_json(workspace_root / "tasks" / TASKS_INDEX_FILENAME, [])
    write_json(workspace_root / "assets" / ASSETS_INDEX_FILENAME, [])
    return config


def get_profile_path(repo_root: Path | None = None) -> Path:
    return get_workspace_root(repo_root) / "profile" / PROFILE_FILENAME


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


def get_tasks_root(repo_root: Path | None = None) -> Path:
    return get_workspace_root(repo_root) / "tasks"


def get_task_path(task_id: str, repo_root: Path | None = None) -> Path:
    return get_tasks_root(repo_root) / task_id / TASK_FILENAME


def get_assets_root(repo_root: Path | None = None) -> Path:
    return get_workspace_root(repo_root) / "assets"


def get_asset_path(asset_id: str, repo_root: Path | None = None) -> Path:
    return get_assets_root(repo_root) / f"{asset_id}.json"


def save_profile(profile: ResearcherProfile, repo_root: Path | None = None) -> Path:
    path = get_profile_path(repo_root)
    write_model(path, profile)
    return path


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

    index_path = get_assets_root(repo_root) / ASSETS_INDEX_FILENAME
    existing = read_json(index_path) if index_path.exists() else []
    existing = [item for item in existing if item.get("id") != asset.id]
    existing.insert(0, asset.model_dump())
    write_json(index_path, existing)
    return path


def save_project_asset(project_id: str, asset: ReusableAsset, repo_root: Path | None = None) -> Path:
    project_asset_path = get_project_assets_dir(project_id, repo_root) / f"{asset.id}.json"
    write_model(project_asset_path, asset)
    return project_asset_path


def load_assets(repo_root: Path | None = None) -> list[ReusableAsset]:
    index_path = get_assets_root(repo_root) / ASSETS_INDEX_FILENAME
    if not index_path.exists():
        return []
    return [ReusableAsset.model_validate(item) for item in read_json(index_path)]


def load_current_state(repo_root: Path | None = None) -> WorkspaceState:
    return WorkspaceState(
        profile=load_profile(repo_root),
        active_project=load_active_project(repo_root),
        tasks=load_tasks(repo_root),
        assets=load_assets(repo_root),
    )
