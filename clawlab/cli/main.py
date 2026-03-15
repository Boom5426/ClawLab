from __future__ import annotations

from pathlib import Path

import typer

from clawlab.core.constants import SUPPORTED_TASK_TYPES
from clawlab.services.asset_service import retrieve_assets_for_task
from clawlab.services.company_service import (
    build_first_job_command,
    build_first_job_goal,
    create_company_profile,
    create_founder_profile,
    create_team_config,
    get_onboarding_input_path,
    recommend_first_job_type,
    recommend_starter_team,
)
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
    load_company_profile,
    load_company_job,
    load_company_handbook,
    load_founder_profile,
    load_job_result,
    load_handoffs,
    load_material_summary,
    load_manager_plan,
    load_current_state,
    load_employee_playbook,
    load_jobs,
    load_profile,
    load_project,
    load_project_deliverables,
    load_reassignment_actions,
    load_review_decisions,
    load_task,
    load_task_plan,
    load_team_config,
    load_work_orders,
    save_company_profile,
    save_asset,
    save_founder_profile,
    save_material_summary,
    save_project_asset,
    save_profile,
    save_project,
    save_task,
    save_task_plan,
    save_team_config,
)

app = typer.Typer(help="Build and operate your virtual research company.")
project_app = typer.Typer(help="Technical project commands")
task_app = typer.Typer(help="Technical task commands")
config_app = typer.Typer(help="Technical config commands")
employees_app = typer.Typer(help="Employee commands")
job_app = typer.Typer(help="Manager job commands")
company_app = typer.Typer(help="Company-facing onboarding and operating commands")
handbook_app = typer.Typer(help="Knowledge and handbook commands")
hire_app = typer.Typer(help="Hiring recommendation commands")
team_app = typer.Typer(help="Team overview commands")
employee_app = typer.Typer(help="Company-facing employee brief commands")

app.add_typer(project_app, name="project")
app.add_typer(task_app, name="task")
app.add_typer(config_app, name="config")
app.add_typer(employees_app, name="employees")
app.add_typer(job_app, name="job")
app.add_typer(company_app, name="company")
app.add_typer(handbook_app, name="handbook")
app.add_typer(hire_app, name="hire")
app.add_typer(team_app, name="team")
app.add_typer(employee_app, name="employee")


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


def _collect_project_intake_from_prompt() -> tuple[str, str | None]:
    typer.echo("项目 intake 支持三种方式：文件路径、直接输入一句说明、或输入 `paste` 粘贴多行内容。")
    source_input = typer.prompt("请给我当前项目材料或说明")
    if source_input.strip().lower() == "paste":
        project_brief = _collect_multiline_input("请粘贴项目说明、论文摘要、网站描述或研究 memo。")
        source_label = "pasted project brief"
    else:
        project_brief, source_label = _resolve_project_source(source_input)
    return project_brief, source_label


def _collect_job_input_source() -> tuple[Path, str]:
    typer.echo("第一份工作材料支持：文件路径、直接输入一句说明、或输入 `paste` 粘贴多行内容。")
    source_input = typer.prompt("请给公司一份可以开工的材料")
    if source_input.strip().lower() == "paste":
        raw_text = _collect_multiline_input("请粘贴第一份 job 的材料内容。")
        save_path = get_onboarding_input_path()
        save_path.write_text(raw_text, encoding="utf-8")
        return save_path, "onboarding pasted input"
    candidate = Path(source_input).expanduser()
    if candidate.exists():
        return candidate, str(candidate)
    save_path = get_onboarding_input_path()
    save_path.write_text(source_input.strip(), encoding="utf-8")
    return save_path, "onboarding inline input"


def _fail(message: str) -> None:
    typer.echo(message)
    raise typer.Exit(code=1)


def _emit_llm_fallback_message(config, module_name: str) -> None:
    enabled, reason = get_llm_runtime_status(config.llm, module_name)
    if config.llm.mode == "hybrid" and getattr(config.llm, f"use_llm_for_{module_name}", False) and not enabled:
        typer.echo(f"LLM fallback for {module_name}: {reason}. 当前先回退到规则版。")


def _emit_api_first_guidance(config) -> None:
    if config.llm.provider == "openai" and not get_llm_runtime_status(config.llm, "materials")[0]:
        typer.echo("ClawLab 当前按 API-first 范式运行。")
        typer.echo("建议先设置 `OPENAI_API_KEY`，否则系统会回退到规则版，体验会明显变弱。")
        typer.echo("示例：export OPENAI_API_KEY=your_key_here")


def _render_company_panel() -> None:
    config = load_config()
    state = load_current_state()
    company_profile = load_company_profile()
    founder_profile = load_founder_profile()
    team_config = load_team_config()

    typer.echo("ClawLab Company Status")
    typer.echo(f"- mode: {config.llm.mode}")
    typer.echo(f"- provider: {config.llm.provider}")
    if not get_llm_runtime_status(config.llm, "materials")[0]:
        typer.echo("- api state: not fully configured, company is falling back where needed")
        typer.echo("  set OPENAI_API_KEY to unlock the intended API-first workflow")
    typer.echo(
        "- llm enablement: "
        f"materials={get_llm_runtime_status(config.llm, 'materials')[0]}, "
        f"planning={get_llm_runtime_status(config.llm, 'planning')[0]}, "
        f"drafts={get_llm_runtime_status(config.llm, 'drafts')[0]}, "
        f"learning={get_llm_runtime_status(config.llm, 'learning')[0]}"
    )
    if company_profile:
        typer.echo(f"- company: {company_profile.company_name}")
        typer.echo(f"  mission: {company_profile.mission}")
        typer.echo(f"  focus: {company_profile.focus_area}")
    else:
        typer.echo("- company: not initialized")
    if founder_profile:
        typer.echo(f"- founder: {founder_profile.display_name} | {founder_profile.founder_title}")
    if team_config:
        typer.echo(f"- current team: {', '.join(team_config.active_roles)}")
        typer.echo(f"  manager enabled: {team_config.manager_enabled}")
    if state.active_project:
        typer.echo(f"- active mission: {state.active_project.title}")
        typer.echo(f"  current goal: {state.active_project.current_goal}")
    else:
        typer.echo("- active mission: none")

    jobs = load_jobs()
    if jobs:
        typer.echo("- recent jobs:")
        for job in jobs[:3]:
            typer.echo(f"  - {job.job_type}: {job.boss_goal}")
            plan = load_manager_plan(get_manager_plan_path(job.id))
            if plan:
                typer.echo(f"    chain: {' -> '.join(plan.selected_employees)}")
            reviews = load_review_decisions(job.id)
            if reviews:
                typer.echo(
                    f"    latest review: {reviews[-1].decision} "
                    f"[{reviews[-1].issue_type}/{reviews[-1].risk_level}]"
                )
    else:
        typer.echo("- recent jobs: none")

    if state.active_project:
        deliverables = load_project_deliverables(state.active_project.id)
        if deliverables:
            typer.echo("- recent deliverables:")
            for deliverable in deliverables[:3]:
                typer.echo(f"  - {deliverable.employee_role}: {deliverable.title}")
        else:
            typer.echo("- recent deliverables: none")
    company_handbook = load_company_handbook()
    typer.echo(f"- handbook updates: {len(company_handbook)}")
    if state.assets:
        typer.echo("- recent team memory:")
        for asset in state.assets[:3]:
            typer.echo(f"  - {asset.scope}/{asset.asset_type}: {asset.title}")
    else:
        typer.echo("- recent team memory: none")

    if jobs:
        latest_job = jobs[0]
        handoffs = load_handoffs(latest_job.id)
        reviews = load_review_decisions(latest_job.id)
        reassignments = load_reassignment_actions(latest_job.id)
        if handoffs:
            consumed = sum(1 for handoff in handoffs if handoff.status == "consumed")
            typer.echo(f"- collaboration handoffs: {len(handoffs)} total / {consumed} consumed")
        if reviews:
            typer.echo(
                f"- collaboration reviews: {reviews[-1].decision} "
                f"[{reviews[-1].issue_type}/{reviews[-1].risk_level}]"
            )
        if reassignments:
            typer.echo(f"- collaboration reassignments: {len(reassignments)}")
    if state.tasks:
        latest_task = state.tasks[0]
        typer.echo(
            f"- recent intelligence usage: materials={load_material_summary(latest_task.material_summary_path).generation_mode if latest_task.material_summary_path and load_material_summary(latest_task.material_summary_path) else 'n/a'}, "
            f"planning={load_task_plan(latest_task.task_plan_path).planning_mode if latest_task.task_plan_path and load_task_plan(latest_task.task_plan_path) else 'n/a'}, "
            f"drafts={latest_task.draft_mode}"
        )
        context_labels = latest_task.draft_context_sources[:4]
        if context_labels:
            typer.echo(f"- recent enhanced context: {' | '.join(context_labels)}")


@app.command("init")
def init_command() -> None:
    """Create the workspace scaffold and default config."""
    config = init_workspace()
    typer.echo("Initialized ClawLab workspace.")
    typer.echo(f"- workspace root: {config.workspace_root}")
    typer.echo("- runtime: API-first (hybrid + openai)")
    _emit_api_first_guidance(config)
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

    project_brief, source_label = _collect_project_intake_from_prompt()
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
    planning_status = get_llm_runtime_status(config.llm, "planning")[1]
    draft_status = get_llm_runtime_status(config.llm, "drafts")[1]
    learning_status = get_llm_runtime_status(config.llm, "learning")[1]
    typer.echo(
        "- llm modules: "
        f"materials={config.llm.use_llm_for_materials} ({material_status}), "
        f"planning={config.llm.use_llm_for_planning} ({planning_status}), "
        f"drafts={config.llm.use_llm_for_drafts} ({draft_status}), "
        f"learning={config.llm.use_llm_for_learning} ({learning_status})"
    )
    _emit_api_first_guidance(config)
    typer.echo(f"- employees: {', '.join(spec.role_name for spec in list_employee_specs())}")
    company_profile = load_company_profile()
    founder_profile = load_founder_profile()
    team_config = load_team_config()
    if company_profile:
        typer.echo(f"- company: {company_profile.company_name} | {company_profile.focus_area}")
        typer.echo(f"  mission: {company_profile.mission}")
    else:
        typer.echo("- company: not initialized")
    if founder_profile:
        typer.echo(f"- founder: {founder_profile.display_name} | {founder_profile.founder_title}")
    if team_config:
        typer.echo(f"- team: {', '.join(team_config.active_roles)}")
        typer.echo(f"  manager enabled: {team_config.manager_enabled}")
        company_handbook = load_company_handbook()
        typer.echo(f"  company handbook entries: {len(company_handbook)}")
        for role in team_config.active_roles[:3]:
            typer.echo(f"  {role} playbook entries: {len(load_employee_playbook(role))}")
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
        typer.echo(f"  draft mode: {latest_task.draft_mode}")
        typer.echo(f"  materials: {', '.join(latest_task.input_material_paths)}")
        typer.echo(f"  material types: {', '.join(latest_task.input_material_types)}")
        typer.echo(f"  material summary: {'yes' if latest_task.material_summary_path else 'no'}")
        typer.echo(f"  retrieved assets: {len(latest_task.retrieved_asset_ids)}")
        if latest_task.draft_context_sources:
            typer.echo(f"  draft context: {' | '.join(latest_task.draft_context_sources[:4])}")
        if latest_task.material_summary_title:
            typer.echo(f"  summary title: {latest_task.material_summary_title}")
        if latest_task.material_summary_path:
            summary = load_material_summary(latest_task.material_summary_path)
            if summary:
                typer.echo(f"  summary short: {summary.short_summary}")
                typer.echo(f"  summary mode: {summary.generation_mode}")
                if summary.context_sources:
                    typer.echo(f"  summary context: {' | '.join(summary.context_sources[:4])}")
                if summary.key_topics:
                    typer.echo(f"  summary topics: {', '.join(summary.key_topics[:5])}")
                if summary.methods_or_entities:
                    typer.echo(f"  summary methods/entities: {', '.join(summary.methods_or_entities[:5])}")
        if latest_task.task_plan_path:
            plan = load_task_plan(latest_task.task_plan_path)
            if plan:
                typer.echo(f"  plan strategy: {plan.output_strategy}")
                typer.echo(f"  plan mode: {plan.planning_mode}")
                if plan.context_sources:
                    typer.echo(f"  plan context: {' | '.join(plan.context_sources[:4])}")
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
            typer.echo(f"  - {asset.scope}/{asset.asset_type}: {asset.title} ({asset.confidence:.2f})")
            if asset.context_sources:
                typer.echo(f"    context: {' | '.join(asset.context_sources[:3])}")
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
    if state.active_project:
        deliverables = load_project_deliverables(state.active_project.id)
        if deliverables:
            typer.echo("- recent deliverables:")
            for deliverable in deliverables[:3]:
                typer.echo(f"  - {deliverable.employee_role}: {deliverable.title}")
        else:
            typer.echo("- recent deliverables: none")


@company_app.command("status")
def company_status() -> None:
    """Show the company-facing operating panel."""
    _render_company_panel()


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
    _emit_llm_fallback_message(config, "planning")
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
    typer.echo(f"- material mode: {material_summary.generation_mode}")
    typer.echo(f"- retrieved assets: {len(retrieved_assets)}")
    typer.echo(f"- task plan strategy: {task_plan.output_strategy}")
    typer.echo(f"- task plan mode: {task_plan.planning_mode}")
    typer.echo(f"- draft mode: {task.draft_mode}")
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
    typer.echo(f"- use_llm_for_planning: {config.llm.use_llm_for_planning}")
    typer.echo(f"- use_llm_for_drafts: {config.llm.use_llm_for_drafts}")
    typer.echo(f"- use_llm_for_learning: {config.llm.use_llm_for_learning}")
    typer.echo(f"- openai_base_url: {config.llm.openai_base_url}")
    typer.echo("- note: current default is API-first; without OPENAI_API_KEY the system falls back per module")


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


@company_app.command("init")
def company_init() -> None:
    """Guide the founder through creating a virtual research company."""
    config = init_workspace()
    _emit_api_first_guidance(config)
    profile = load_profile()
    if profile is None:
        _fail("No profile found. 先运行 `clawlab ingest-cv <path>`，再来开公司。")

    typer.echo("欢迎来到 ClawLab。下面开始为你搭建第一版虚拟研究公司。")
    founder_mission = typer.prompt("作为创始人，你想让这家公司帮你完成什么？")
    company_name = typer.prompt("给你的公司起个名字", default=f"{profile.name.split()[0]}'s Research Company")
    focus_area = typer.prompt("这家公司当前聚焦什么方向？", default=profile.discipline)
    current_business_type = typer.prompt("这家公司现在是什么类型？", default="Single-founder research company")

    active_project = load_project(config.active_project_id) if config.active_project_id else None
    if active_project is None:
        typer.echo("当前还没有 active project。我们现在顺手把第一个项目也建起来。")
        if typer.confirm("现在就创建第一个 active project？", default=True):
            project_brief, source_label = _collect_project_intake_from_prompt()
            current_goal = typer.prompt("这家公司当前最想推进这个项目的什么？")
            title_hint = typer.prompt("如果想手动指定项目标题，在这里输入；否则直接回车", default="")
            active_project = create_project_from_intake(
                profile,
                project_brief=project_brief,
                current_goal=current_goal,
                title_hint=title_hint,
                source_label=source_label,
            )
            project_path = save_project(active_project)
            typer.echo(f"- active project created: {active_project.title}")
            typer.echo(f"- saved project: {project_path}")
        else:
            typer.echo("你稍后仍可运行 `clawlab project create` 创建 active project。")

    recommend_small = typer.confirm("你想先用一个更精简的 starter team 吗？", default=False)
    recommended_roles = recommend_starter_team(profile, prefer_small_team=recommend_small)
    typer.echo(f"推荐 starter team: {', '.join(recommended_roles)}")
    use_recommended = typer.confirm("使用推荐团队？", default=True)
    if use_recommended:
        selected_roles = recommended_roles
    else:
        raw_roles = typer.prompt("请输入你想启用的员工角色，用逗号分隔")
        selected_roles = [role.strip() for role in raw_roles.split(",") if role.strip()]
        if not selected_roles:
            selected_roles = recommended_roles

    founder_profile = create_founder_profile(profile, founder_mission=founder_mission)
    company_profile = create_company_profile(
        company_name=company_name,
        mission=founder_mission,
        focus_area=focus_area,
        current_business_type=current_business_type,
        founder_profile_id=founder_profile.id,
        active_project_id=active_project.id if active_project else config.active_project_id,
    )
    team_config = create_team_config(company_id=company_profile.id, active_roles=selected_roles)

    founder_path = save_founder_profile(founder_profile)
    company_path = save_company_profile(company_profile)
    team_path = save_team_config(team_config)

    typer.echo("虚拟研究公司已初始化。")
    typer.echo(f"- founder: {founder_profile.display_name}")
    typer.echo(f"- company: {company_profile.company_name}")
    typer.echo(f"- team: {', '.join(team_config.active_roles)}")
    typer.echo(f"- saved founder: {founder_path}")
    typer.echo(f"- saved company: {company_path}")
    typer.echo(f"- saved team: {team_path}")
    if active_project:
        first_job_type = recommend_first_job_type(team_config.active_roles)
        suggested_goal = build_first_job_goal(
            mission=company_profile.mission,
            project_title=active_project.title,
            job_type=first_job_type,
        )
        typer.echo("- launch plan:")
        typer.echo(f"  recommended first job: {first_job_type}")
        typer.echo(f"  suggested goal: {suggested_goal}")
        if typer.confirm("现在就给公司派第一份工作？", default=False):
            input_path, input_label = _collect_job_input_source()
            typer.echo("现在直接执行下面这条命令即可：")
            typer.echo(
                build_first_job_command(
                    project_id=active_project.id,
                    input_path=str(input_path),
                    goal=suggested_goal,
                    job_type=first_job_type,
                )
            )
            typer.echo(f"- prepared input: {input_label}")
        else:
            typer.echo("你可以下一步直接复制这条命令开工：")
            typer.echo(
                build_first_job_command(
                    project_id=active_project.id,
                    input_path="PATH_TO_MATERIAL",
                    goal=suggested_goal,
                    job_type=first_job_type,
                )
            )
    else:
        typer.echo("- next: 先运行 `clawlab project create`，再给公司派第一份工作。")


@hire_app.command("recommend")
def hire_recommend() -> None:
    """Recommend a starter team for the founder."""
    profile = load_profile()
    if profile is None:
        _fail("No profile found. 先运行 `clawlab ingest-cv <path>`。")
    active_project = load_current_state().active_project
    full_team = recommend_starter_team(profile, prefer_small_team=False)
    lean_team = recommend_starter_team(profile, prefer_small_team=True)
    typer.echo("Starter team recommendation")
    typer.echo(f"- founder: {profile.name} | {profile.discipline}")
    if active_project:
        typer.echo(f"- active mission: {active_project.title}")
    typer.echo(f"- recommended full team: {', '.join(full_team)}")
    typer.echo(f"- recommended lean team: {', '.join(lean_team)}")


@team_app.command("list")
def team_list() -> None:
    """List the current team in company-facing language."""
    team_config = load_team_config()
    if team_config is None:
        _fail("团队尚未配置。先运行 `clawlab company init`。")
    typer.echo("Current team")
    for role in team_config.active_roles:
        spec = get_employee_spec(role)
        typer.echo(f"- {role}: {spec.display_name}")
        typer.echo(f"  {spec.description}")


@employee_app.command("brief")
def employee_brief(role: str) -> None:
    """Show one employee from the company operating view."""
    try:
        spec = get_employee_spec(role)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    jobs = load_jobs()
    recent_jobs = []
    received_from: set[str] = set()
    hands_to: set[str] = set()
    review_events = []
    reassign_events = []
    for job in jobs:
        plan = load_manager_plan(get_manager_plan_path(job.id))
        if plan and role in plan.selected_employees:
            recent_jobs.append(job)
        for handoff in load_handoffs(job.id):
            if handoff.to_role == role:
                received_from.add(handoff.from_role)
            if handoff.from_role == role:
                hands_to.add(handoff.to_role)
        for review in load_review_decisions(job.id):
            if role == "review_editor":
                review_events.append(review)
        for action in load_reassignment_actions(job.id):
            if action.reassigned_to == role:
                reassign_events.append(action)

    role_assets = [asset for asset in load_assets() if asset.employee_role == role]
    playbook_entries = load_employee_playbook(role)
    config = load_config()
    module_for_role = {
        "literature_analyst": "materials",
        "project_manager": "planning",
        "draft_writer": "drafts",
        "review_editor": "learning",
    }[role]
    llm_enabled, llm_reason = get_llm_runtime_status(config.llm, module_for_role)

    typer.echo(f"Employee brief: {role}")
    typer.echo(f"- display_name: {spec.display_name}")
    typer.echo(f"- responsibility: {spec.description}")
    typer.echo(f"- capabilities: {', '.join(spec.core_capabilities)}")
    typer.echo(f"- accessible_context: {', '.join(spec.accessible_context)}")
    typer.echo(f"- llm enhancement: {llm_enabled} ({module_for_role}: {llm_reason})")
    typer.echo(f"- receives handoff from: {', '.join(sorted(received_from)) or 'none'}")
    typer.echo(f"- hands off to: {', '.join(sorted(hands_to)) or 'none'}")
    if recent_jobs:
        typer.echo("- recent jobs:")
        for job in recent_jobs[:3]:
            typer.echo(f"  - {job.job_type}: {job.boss_goal}")
    else:
        typer.echo("- recent jobs: none")
    handoff_contracts = []
    for job in jobs:
        for handoff in load_handoffs(job.id):
            if handoff.from_role == role or handoff.to_role == role:
                handoff_contracts.append(f"{handoff.from_role}->{handoff.to_role}:{handoff.contract_type}")
    if handoff_contracts:
        typer.echo("- recent handoff contracts:")
        for contract in handoff_contracts[:5]:
            typer.echo(f"  - {contract}")
    if review_events:
        typer.echo(f"- recent review count: {len(review_events)}")
    if reassign_events:
        typer.echo(f"- recent reassignment count: {len(reassign_events)}")
    if role_assets:
        typer.echo("- learned role memory:")
        for asset in role_assets[:3]:
            typer.echo(f"  - {asset.asset_type}: {asset.title}")
        used_context_assets = [asset for asset in role_assets if asset.context_sources]
        if used_context_assets:
            typer.echo(f"- role memory used in enhanced chain: {used_context_assets[0].derivation_mode}")
    else:
        typer.echo("- learned role memory: none")
    if playbook_entries:
        typer.echo("- playbook/templates:")
        for path in playbook_entries[:5]:
            typer.echo(f"  - {path.relative_to(Path.cwd())}")
        typer.echo(f"- playbook referenced by enhanced chain: {'yes' if llm_enabled else 'not currently'}")
    else:
        typer.echo("- playbook/templates: none")


@handbook_app.command("show")
def handbook_show() -> None:
    """Show company handbook entries."""
    entries = load_company_handbook()
    typer.echo("Company handbook")
    if not entries:
        typer.echo("- no handbook entries yet")
        return
    for path in entries[:10]:
        typer.echo(f"- {path.relative_to(Path.cwd())}")


@employees_app.command("handbook")
def employees_handbook(role: str) -> None:
    """Show one employee playbook."""
    try:
        get_employee_spec(role)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    entries = load_employee_playbook(role)
    typer.echo(f"Employee handbook: {role}")
    if not entries:
        typer.echo("- no playbook entries yet")
        return
    for path in entries[:10]:
        typer.echo(f"- {path.relative_to(Path.cwd())}")


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
    for module_name in ("materials", "planning", "drafts", "learning"):
        _emit_llm_fallback_message(config, module_name)

    job, plan, work_orders = create_manager_plan(
        job_type=job_type,  # type: ignore[arg-type]
        boss_goal=goal,
        project=project_card,
        input_path=input_path,
        revised_path=revised,
        profile=profile,
        llm_settings=config.llm,
    )
    deliverables, handoffs, review_decisions, reassignments, final_status = dispatch_work_orders(
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
        handoffs=handoffs,
        review_decisions=review_decisions,
        reassignments=reassignments,
        final_status=final_status,
    )

    typer.echo("Manager job completed.")
    typer.echo(f"- job id: {job.id}")
    typer.echo(f"- job type: {job.job_type}")
    typer.echo(f"- employees: {' -> '.join(plan.selected_employees)}")
    typer.echo(f"- deliverables: {len(deliverables)}")
    typer.echo(f"- handoffs: {len(handoffs)}")
    typer.echo(f"- reviews: {len(review_decisions)}")
    typer.echo(f"- reassignments: {len(reassignments)}")
    typer.echo(f"- final status: {result.final_status}")
    typer.echo(f"- final output: {result.final_output_path}")


@job_app.command("show")
def job_show(job_id: str) -> None:
    """Show one job with collaboration trace."""
    job = load_company_job(job_id)
    if job is None:
        _fail(f"Job not found: {job_id}")
    plan = load_manager_plan(get_manager_plan_path(job.id))
    result = load_job_result(get_job_result_path(job.id))
    work_orders = load_work_orders(job.id)
    handoffs = load_handoffs(job.id)
    reviews = load_review_decisions(job.id)
    reassignments = load_reassignment_actions(job.id)

    typer.echo(f"Job: {job.id}")
    typer.echo(f"- type: {job.job_type}")
    typer.echo(f"- boss_goal: {job.boss_goal}")
    if plan:
        typer.echo(f"- employee chain: {' -> '.join(plan.selected_employees)}")
    if work_orders:
        typer.echo("- work orders:")
        for work_order in work_orders:
            typer.echo(f"  - {work_order.employee_role}: {work_order.status}")
    if handoffs:
        typer.echo("- handoffs:")
        for handoff in handoffs:
            typer.echo(
                f"  - {handoff.from_role} -> {handoff.to_role} "
                f"[{handoff.contract_type}/{handoff.status}]: {handoff.handoff_summary}"
            )
    if reviews:
        typer.echo("- reviews:")
        for review in reviews:
            typer.echo(
                f"  - {review.decision} [{review.issue_type}/{review.risk_level}]: "
                f"{review.rationale}"
            )
            for name, status in review.review_checks.items():
                typer.echo(f"    - {name}: {status}")
    if reassignments:
        typer.echo("- reassignments:")
        for action in reassignments:
            typer.echo(
                f"  - {action.reassigned_to} "
                f"[{action.intervention_policy or 'n/a'}]: {action.reason}"
            )
    if result:
        typer.echo(f"- final status: {result.final_status}")
        typer.echo(f"- final output: {result.final_output_path}")


if __name__ == "__main__":
    app()
