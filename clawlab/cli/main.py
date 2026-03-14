from __future__ import annotations

from pathlib import Path

import typer

from clawlab.core.constants import SUPPORTED_TASK_TYPES
from clawlab.services.draft_service import generate_draft
from clawlab.services.ingest_service import read_cv_text, read_material
from clawlab.services.learning_service import derive_assets_from_revision
from clawlab.services.profile_service import parse_cv_to_profile
from clawlab.services.project_service import create_project_from_answers
from clawlab.services.workspace_service import (
    get_outputs_dir,
    init_workspace,
    load_current_state,
    load_profile,
    load_project,
    load_task,
    save_asset,
    save_project_asset,
    save_profile,
    save_project,
    save_task,
)

app = typer.Typer(help="ClawLab CLI MVP")
project_app = typer.Typer(help="Project commands")
task_app = typer.Typer(help="Task commands")

app.add_typer(project_app, name="project")
app.add_typer(task_app, name="task")


def _read_text_file(path: Path) -> str:
    if not path.exists():
        raise typer.BadParameter(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def _fail(message: str) -> None:
    typer.echo(message)
    raise typer.Exit(code=1)


@app.command("init")
def init_command() -> None:
    """Create the workspace scaffold and default config."""
    config = init_workspace()
    typer.echo("Initialized ClawLab workspace.")
    typer.echo(f"- workspace root: {config.workspace_root}")
    typer.echo("- next: run `clawlab ingest-cv <path>`")


@app.command("ingest-cv")
def ingest_cv(path: Path) -> None:
    """Read a CV text file and create the initial researcher profile."""
    try:
        cv_text = read_cv_text(path)
    except FileNotFoundError as error:
        raise typer.BadParameter(str(error)) from error
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    profile = parse_cv_to_profile(cv_text)
    saved_path = save_profile(profile)

    typer.echo("Created ResearcherProfile.")
    typer.echo(f"- id: {profile.id}")
    typer.echo(f"- name: {profile.name}")
    typer.echo(f"- role: {profile.role}")
    typer.echo(f"- discipline: {profile.discipline}")
    typer.echo(f"- saved: {saved_path}")


@project_app.command("create")
def create_project() -> None:
    """Interactively create the active project card."""
    profile = load_profile()
    if profile is None:
        _fail("No profile found. Run `clawlab ingest-cv <path>` first.")

    title = typer.prompt("你当前最重要的研究项目是什么？")
    desired_outcome = typer.prompt("你近期最想推进的成果是什么？")
    blocker = typer.prompt("你当前最卡的是哪一步？")
    materials = typer.prompt("你手头有哪些材料？")

    project = create_project_from_answers(
        profile,
        title=title,
        desired_outcome=desired_outcome,
        blocker=blocker,
        materials=materials,
    )
    saved_path = save_project(project)

    typer.echo("Created ProjectCard.")
    typer.echo(f"- id: {project.id}")
    typer.echo(f"- title: {project.title}")
    typer.echo(f"- saved: {saved_path}")


@app.command("status")
def status_command() -> None:
    """Show current profile, active project, latest task, and latest assets."""
    state = load_current_state()

    typer.echo("ClawLab Status")
    if state.profile:
        typer.echo(f"- profile: {state.profile.name} | {state.profile.role} | {state.profile.discipline}")
    else:
        typer.echo("- profile: missing")

    if state.active_project:
        typer.echo(f"- active project: {state.active_project.id} | {state.active_project.title}")
        typer.echo(f"  goal: {state.active_project.current_goal}")
    else:
        typer.echo("- active project: missing")

    if state.tasks:
        latest_task = state.tasks[0]
        typer.echo(f"- latest task: {latest_task.id} | {latest_task.task_type}")
        typer.echo(f"  draft: {latest_task.generated_draft_path}")
        typer.echo(f"  materials: {', '.join(latest_task.input_material_paths)}")
        typer.echo(f"  material types: {', '.join(latest_task.input_material_types)}")
        if latest_task.feedback_summary:
            typer.echo(f"  learning: {latest_task.feedback_summary}")
    else:
        typer.echo("- latest task: none")

    if state.assets:
        typer.echo("- recent assets:")
        for asset in state.assets[:3]:
            typer.echo(f"  - {asset.asset_type}: {asset.title} ({asset.confidence:.2f})")
    else:
        typer.echo("- recent assets: none")


@task_app.command("run")
def task_run(
    task_type: str,
    project: str = typer.Option(..., "--project", help="Project ID"),
    input_path: Path = typer.Option(..., "--input", help="Path to task input text"),
) -> None:
    """Generate a draft and create a TaskCard."""
    if task_type not in SUPPORTED_TASK_TYPES:
        raise typer.BadParameter(f"task_type must be one of: {', '.join(SUPPORTED_TASK_TYPES)}")

    profile = load_profile()
    if profile is None:
        _fail("No profile found. Run `clawlab ingest-cv <path>` first.")

    project_card = load_project(project)
    if project_card is None:
        _fail(f"Project not found: {project}")

    try:
        material = read_material(input_path)
    except FileNotFoundError as error:
        raise typer.BadParameter(str(error)) from error
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    output_dir = get_outputs_dir(project_card.id)
    task, draft_path = generate_draft(
        profile,
        project_card,
        task_type=task_type,
        material=material,
        output_dir=output_dir,
        workspace_root=Path.cwd() / "workspace",
    )
    save_task(task)

    typer.echo("Generated draft and TaskCard.")
    typer.echo(f"- task id: {task.id}")
    typer.echo(f"- task type: {task.task_type}")
    typer.echo(f"- input: {material.path} ({material.material_type})")
    typer.echo(f"- draft: {draft_path}")


@app.command("learn")
def learn_command(
    task: str = typer.Option(..., "--task", help="Task ID"),
    revised: Path = typer.Option(..., "--revised", help="Path to revised markdown file"),
) -> None:
    """Compare generated and revised drafts, then persist learned assets."""
    task_card = load_task(task)
    if task_card is None:
        _fail(f"Task not found: {task}")

    project_card = load_project(task_card.project_card_id)
    if project_card is None:
        _fail(f"Project not found: {task_card.project_card_id}")

    generated_path = Path(task_card.generated_draft_path)
    if not generated_path.exists():
        _fail(f"Generated draft not found: {generated_path}")

    revised_text = _read_text_file(revised)
    generated_text = _read_text_file(generated_path)

    updated_task, updated_project, assets = derive_assets_from_revision(
        task_card,
        project_card,
        generated_text=generated_text,
        revised_text=revised_text,
    )
    updated_task = updated_task.model_copy(update={"revised_draft_path": str(revised)})

    save_task(updated_task)
    save_project(updated_project)
    for asset in assets:
        save_asset(asset)
        save_project_asset(updated_project.id, asset)

    typer.echo("Learning step completed.")
    typer.echo(f"- task updated: {updated_task.id}")
    typer.echo(f"- assets created: {len(assets)}")
    for asset in assets:
        typer.echo(f"  - {asset.asset_type}: {asset.title}")


if __name__ == "__main__":
    app()
