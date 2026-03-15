from __future__ import annotations

from pathlib import Path

import typer

from clawlab.core.constants import SUPPORTED_TASK_TYPES
from clawlab.services.asset_service import retrieve_assets_for_task
from clawlab.services.employee_service import get_employee_spec, list_employee_specs
from clawlab.services.llm_service import get_llm_runtime_status
from clawlab.services.manager_service import (
    collect_deliverables,
    create_manager_plan,
    dispatch_work_orders,
    synthesize_job_result,
)
from clawlab.services.draft_service import generate_draft
from clawlab.services.ingest_service import read_cv_text
from clawlab.services.learning_service import derive_assets_from_revision
from clawlab.services.material_service import condense_material
from clawlab.services.planning_service import create_task_plan
from clawlab.services.profile_service import parse_cv_to_profile
from clawlab.services.project_service import create_project_from_intake
from clawlab.services.workspace_service import (
    get_outputs_dir,
    get_job_result_path,
    get_manager_plan_path,
    init_workspace,
    load_config,
    load_assets,
    load_company_job,
    load_material_summary,
    load_manager_plan,
    load_current_state,
    load_jobs,
    load_profile,
    load_project,
    load_task,
    load_task_plan,
    load_work_orders,
    save_asset,
    save_material_summary,
    save_project_asset,
    save_profile,
    save_project,
    save_task,
    save_task_plan,
)

app = typer.Typer(help="ClawLab CLI MVP")
project_app = typer.Typer(help="Project commands")
task_app = typer.Typer(help="Task commands")
config_app = typer.Typer(help="Config commands")
employees_app = typer.Typer(help="Employee commands")
job_app = typer.Typer(help="Manager job commands")

app.add_typer(project_app, name="project")
app.add_typer(task_app, name="task")
app.add_typer(config_app, name="config")
app.add_typer(employees_app, name="employees")
app.add_typer(job_app, name="job")


def _read_text_file(path: Path) -> str:
    if not path.exists():
        raise typer.BadParameter(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def _collect_multiline_input(prompt: str) -> str:
    typer.echo(prompt)
    typer.echo("直接粘贴多行内容，结束时单独输入一行 `END`。")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _resolve_project_source(raw_value: str) -> tuple[str, str | None]:
    candidate = Path(raw_value).expanduser()
    if candidate.exists():
        try:
            text = read_cv_text(candidate)
        except (FileNotFoundError, ValueError) as error:
            raise typer.BadParameter(str(error)) from error
        return text, str(candidate)
    return raw_value.strip(), None


def _fail(message: str) -> None:
    typer.echo(message)
    raise typer.Exit(code=1)


def _emit_llm_fallback_message(config, module_name: str) -> None:
    enabled, reason = get_llm_runtime_status(config.llm, module_name)
    if config.llm.mode == "hybrid" and getattr(config.llm, f"use_llm_for_{module_name}", False) and not enabled:
        typer.echo(f"LLM fallback for {module_name}: {reason}. Using rule-based mode.")


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

    typer.echo("项目 intake 支持三种方式：文件路径、直接输入一句说明、或输入 `paste` 粘贴多行内容。")
    source_input = typer.prompt("请给我当前项目材料或说明")
    if source_input.strip().lower() == "paste":
        project_brief = _collect_multiline_input("请粘贴项目说明、论文摘要、网站描述或研究 memo。")
        source_label = "pasted project brief"
    else:
        project_brief, source_label = _resolve_project_source(source_input)

    current_goal = typer.prompt("你这次最想推进什么？可顺带写当前卡点")
    title_hint = typer.prompt("如果想手动指定项目标题，在这里输入；否则直接回车", default="")

    project = create_project_from_intake(
        profile,
        project_brief=project_brief,
        current_goal=current_goal,
        title_hint=title_hint,
        source_label=source_label,
    )
    saved_path = save_project(project)

    typer.echo("Created ProjectCard.")
    typer.echo(f"- id: {project.id}")
    typer.echo(f"- title: {project.title}")
    typer.echo(f"- research question: {project.research_question}")
    typer.echo(f"- materials: {', '.join(project.materials[:3])}")
    typer.echo(f"- saved: {saved_path}")


@app.command("status")
def status_command() -> None:
    """Show current profile, active project, latest task, and latest assets."""
    config = load_config()
    state = load_current_state()

    typer.echo("ClawLab Status")
    typer.echo(f"- mode: {config.llm.mode}")
    typer.echo(f"- provider: {config.llm.provider}")
    typer.echo(f"- model: {config.llm.model}")
    material_status = get_llm_runtime_status(config.llm, "materials")[1]
    draft_status = get_llm_runtime_status(config.llm, "drafts")[1]
    learning_status = get_llm_runtime_status(config.llm, "learning")[1]
    typer.echo(
        "- llm modules: "
        f"materials={config.llm.use_llm_for_materials} ({material_status}), "
        f"drafts={config.llm.use_llm_for_drafts} ({draft_status}), "
        f"learning={config.llm.use_llm_for_learning} ({learning_status})"
    )
    typer.echo(f"- employees: {', '.join(spec.role_name for spec in list_employee_specs())}")
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
        typer.echo(f"  material summary: {'yes' if latest_task.material_summary_path else 'no'}")
        typer.echo(f"  retrieved assets: {len(latest_task.retrieved_asset_ids)}")
        if latest_task.material_summary_title:
            typer.echo(f"  summary title: {latest_task.material_summary_title}")
        if latest_task.material_summary_path:
            summary = load_material_summary(latest_task.material_summary_path)
            if summary:
                typer.echo(f"  summary short: {summary.short_summary}")
                if summary.key_topics:
                    typer.echo(f"  summary topics: {', '.join(summary.key_topics[:5])}")
                if summary.methods_or_entities:
                    typer.echo(f"  summary methods/entities: {', '.join(summary.methods_or_entities[:5])}")
        if latest_task.task_plan_path:
            plan = load_task_plan(latest_task.task_plan_path)
            if plan:
                typer.echo(f"  plan strategy: {plan.output_strategy}")
                typer.echo(f"  plan key points: {' | '.join(plan.key_points_to_cover[:3])}")
                if plan.recommended_structure:
                    typer.echo(f"  plan structure: {' | '.join(plan.recommended_structure[:4])}")
                if plan.selected_assets:
                    typer.echo(f"  plan selected assets: {' | '.join(plan.selected_assets[:3])}")
        if latest_task.retrieved_asset_ids:
            retrieved_assets = [asset for asset in state.assets if asset.id in set(latest_task.retrieved_asset_ids)]
            if retrieved_assets:
                typer.echo("  retrieved asset titles:")
                for asset in retrieved_assets[:3]:
                    typer.echo(f"    - {asset.asset_type}: {asset.title}")
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

    jobs = load_jobs()
    if jobs:
        latest_job = jobs[0]
        typer.echo(f"- latest job: {latest_job.id} | {latest_job.job_type}")
        plan = load_manager_plan(get_manager_plan_path(latest_job.id))
        if plan:
            typer.echo(f"  manager plan employees: {' -> '.join(plan.selected_employees)}")
            typer.echo(f"  manager strategy: {plan.final_output_strategy}")
        work_orders = load_work_orders(latest_job.id)
        if work_orders:
            typer.echo(
                "  work orders: "
                + " | ".join(f"{work_order.employee_role}:{work_order.status}" for work_order in work_orders)
            )
        result = load_job_result(get_job_result_path(latest_job.id))
        if result:
            typer.echo(f"  job result: {result.summary}")
            typer.echo(f"  final output: {result.final_output_path}")
    else:
        typer.echo("- latest job: none")


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
    config = load_config()
    _emit_llm_fallback_message(config, "materials")
    _emit_llm_fallback_message(config, "drafts")

    try:
        material_summary = condense_material(input_path, project_card, config.llm)
    except FileNotFoundError as error:
        raise typer.BadParameter(str(error)) from error
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    material_summaries = [material_summary]
    retrieved_assets = retrieve_assets_for_task(
        task_type=task_type,
        project=project_card,
        profile=profile,
        material_summaries=material_summaries,
        assets=load_assets(),
    )
    task_plan = create_task_plan(
        task_type=task_type,
        profile=profile,
        project=project_card,
        material_summaries=material_summaries,
        retrieved_assets=retrieved_assets,
        llm_settings=config.llm,
    )
    summary_path = save_material_summary(project_card.id, material_summary)
    output_dir = get_outputs_dir(project_card.id)
    task, draft_path = generate_draft(
        profile,
        project_card,
        task_type=task_type,
        material_summaries=material_summaries,
        retrieved_assets=retrieved_assets,
        task_plan=task_plan,
        output_dir=output_dir,
        workspace_root=Path.cwd() / "workspace",
        llm_settings=config.llm,
    )
    plan_path = save_task_plan(task.id, task_plan)
    task = task.model_copy(
        update={
            "material_summary_path": str(summary_path.relative_to(Path.cwd())),
            "material_summary_title": material_summary.title,
            "task_plan_path": str(plan_path.relative_to(Path.cwd())),
        }
    )
    save_task(task)

    typer.echo("Generated draft and TaskCard.")
    typer.echo(f"- task id: {task.id}")
    typer.echo(f"- task type: {task.task_type}")
    typer.echo(f"- input: {material_summary.source_path} ({material_summary.source_type})")
    typer.echo(f"- material summary: {material_summary.title}")
    typer.echo(f"- retrieved assets: {len(retrieved_assets)}")
    typer.echo(f"- task plan strategy: {task_plan.output_strategy}")
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
    config = load_config()
    _emit_llm_fallback_message(config, "learning")

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
        llm_settings=config.llm,
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


@config_app.command("show")
def config_show() -> None:
    """Show the current ClawLab configuration."""
    config = load_config()
    typer.echo("ClawLab Config")
    typer.echo(f"- mode: {config.llm.mode}")
    typer.echo(f"- provider: {config.llm.provider}")
    typer.echo(f"- model: {config.llm.model}")
    typer.echo(f"- use_llm_for_materials: {config.llm.use_llm_for_materials}")
    typer.echo(f"- use_llm_for_drafts: {config.llm.use_llm_for_drafts}")
    typer.echo(f"- use_llm_for_learning: {config.llm.use_llm_for_learning}")
    typer.echo(f"- openai_base_url: {config.llm.openai_base_url}")


@employees_app.command("list")
def employees_list() -> None:
    """List available employee roles."""
    typer.echo("Available employees")
    for spec in list_employee_specs():
        typer.echo(f"- {spec.role_name}: {spec.display_name}")
        typer.echo(f"  {spec.description}")


@employees_app.command("show")
def employees_show(role: str) -> None:
    """Show one employee role in detail."""
    try:
        spec = get_employee_spec(role)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"Employee: {spec.role_name}")
    typer.echo(f"- display_name: {spec.display_name}")
    typer.echo(f"- description: {spec.description}")
    typer.echo(f"- core_capabilities: {', '.join(spec.core_capabilities)}")
    typer.echo(f"- supported_task_types: {', '.join(spec.supported_task_types)}")
    typer.echo(f"- accessible_context: {', '.join(spec.accessible_context)}")
    typer.echo(f"- default_templates: {', '.join(spec.default_templates)}")
    typer.echo(f"- memory_scope: {', '.join(spec.memory_scope)}")


@job_app.command("run")
def job_run(
    job_type: str,
    project: str = typer.Option(..., "--project", help="Project ID"),
    input_path: Path = typer.Option(..., "--input", help="Path to job input material"),
    goal: str = typer.Option(..., "--goal", help="Boss goal for this job"),
    revised: Path | None = typer.Option(None, "--revised", help="Optional revised draft for review_editor"),
) -> None:
    """Run a manager-orchestrated job over the employee chain."""
    if job_type not in {"literature-brief", "paper-outline", "project-brief"}:
        raise typer.BadParameter("job_type must be one of: literature-brief, paper-outline, project-brief")

    profile = load_profile()
    if profile is None:
        _fail("No profile found. Run `clawlab ingest-cv <path>` first.")
    project_card = load_project(project)
    if project_card is None:
        _fail(f"Project not found: {project}")
    config = load_config()
    for module_name in ("materials", "drafts", "learning"):
        _emit_llm_fallback_message(config, module_name)

    job, plan, work_orders = create_manager_plan(
        job_type=job_type,  # type: ignore[arg-type]
        boss_goal=goal,
        project=project_card,
        input_path=input_path,
        revised_path=revised,
    )
    deliverables = dispatch_work_orders(
        job=job,
        plan=plan,
        work_orders=work_orders,
        profile=profile,
        project=project_card,
        llm_settings=config.llm,
    )
    result = synthesize_job_result(
        job=job,
        plan=plan,
        deliverables=collect_deliverables(deliverables),
    )

    typer.echo("Manager job completed.")
    typer.echo(f"- job id: {job.id}")
    typer.echo(f"- job type: {job.job_type}")
    typer.echo(f"- employees: {' -> '.join(plan.selected_employees)}")
    typer.echo(f"- deliverables: {len(deliverables)}")
    typer.echo(f"- final output: {result.final_output_path}")


if __name__ == "__main__":
    app()
