from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


EmployeeRole = Literal["literature_analyst", "project_manager", "draft_writer", "review_editor"]
JobType = Literal["literature-brief", "paper-outline", "project-brief"]


class ResearcherProfile(BaseModel):
    id: str
    name: str
    role: str
    discipline: str
    subfield: str
    methods: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    common_tasks: list[str] = Field(default_factory=list)
    writing_preferences: list[str] = Field(default_factory=list)
    collaboration_preferences: list[str] = Field(default_factory=list)
    source_cv_text: str
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class ProjectCard(BaseModel):
    id: str
    researcher_profile_id: str
    title: str
    research_question: str
    current_goal: str
    current_stage: str
    blockers: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    next_step: str
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class TaskCard(BaseModel):
    id: str
    project_card_id: str
    task_type: Literal["literature-outline", "paper-outline"]
    input_summary: str
    input_materials: list[str] = Field(default_factory=list)
    input_material_paths: list[str] = Field(default_factory=list)
    input_material_types: list[str] = Field(default_factory=list)
    material_summary_path: str | None = None
    material_summary_title: str | None = None
    material_summary_count: int = 0
    retrieved_asset_ids: list[str] = Field(default_factory=list)
    task_plan_path: str | None = None
    draft_mode: Literal["rule", "llm"] = "rule"
    draft_context_sources: list[str] = Field(default_factory=list)
    expected_output: str
    generated_draft_path: str
    revised_draft_path: str | None = None
    feedback_summary: str = ""
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class ReusableAsset(BaseModel):
    id: str
    scope: Literal["company", "employee", "project", "task"]
    asset_type: Literal["writing_rule", "structure_template", "project_note", "common_mistake", "sop_seed"]
    title: str
    content: str
    confidence: float
    source_task_id: str
    project_card_id: str | None = None
    employee_role: EmployeeRole | None = None
    task_type: Literal["literature-outline", "paper-outline"] | None = None
    derivation_mode: Literal["rule", "llm"] = "rule"
    context_sources: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class LlmSettings(BaseModel):
    mode: Literal["local", "hybrid"] = "local"
    provider: Literal["none", "openai"] = "none"
    model: str = "gpt-4o-mini"
    use_llm_for_materials: bool = False
    use_llm_for_planning: bool = False
    use_llm_for_drafts: bool = False
    use_llm_for_learning: bool = False
    openai_base_url: str = "https://api.openai.com/v1"


class WorkspaceConfig(BaseModel):
    workspace_root: str = "workspace"
    active_project_id: str | None = None
    llm: LlmSettings = Field(default_factory=LlmSettings)


class WorkspaceState(BaseModel):
    profile: ResearcherProfile | None = None
    active_project: ProjectCard | None = None
    tasks: list[TaskCard] = Field(default_factory=list)
    assets: list[ReusableAsset] = Field(default_factory=list)


class MaterialDocument(BaseModel):
    path: str
    material_type: Literal["txt", "md", "pdf"]
    extracted_text: str


class MaterialSummary(BaseModel):
    id: str
    source_path: str
    source_type: Literal["txt", "md", "pdf"]
    title: str
    short_summary: str
    key_topics: list[str] = Field(default_factory=list)
    methods_or_entities: list[str] = Field(default_factory=list)
    useful_snippets: list[str] = Field(default_factory=list)
    relevance_to_project: str
    raw_text_excerpt: str
    generation_mode: Literal["rule", "llm"] = "rule"
    context_sources: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class TaskPlan(BaseModel):
    task_type: Literal["literature-outline", "paper-outline"]
    task_goal: str
    output_strategy: str
    key_points_to_cover: list[str] = Field(default_factory=list)
    recommended_structure: list[str] = Field(default_factory=list)
    project_considerations: list[str] = Field(default_factory=list)
    selected_assets: list[str] = Field(default_factory=list)
    planning_mode: Literal["rule", "llm"] = "rule"
    context_sources: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class EmployeeSpec(BaseModel):
    id: str
    role_name: EmployeeRole
    display_name: str
    description: str
    core_capabilities: list[str] = Field(default_factory=list)
    supported_task_types: list[str] = Field(default_factory=list)
    accessible_context: list[str] = Field(default_factory=list)
    default_templates: list[str] = Field(default_factory=list)
    memory_scope: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class WorkOrder(BaseModel):
    id: str
    employee_role: EmployeeRole
    project_card_id: str
    task_type: Literal["literature-outline", "paper-outline"] | None = None
    task_goal: str
    input_context_refs: list[str] = Field(default_factory=list)
    expected_output: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    created_at: str = Field(default_factory=utc_now)


class Deliverable(BaseModel):
    id: str
    employee_role: EmployeeRole
    source_task_id: str | None = None
    source_work_order_id: str | None = None
    title: str
    summary: str
    output_path: str
    created_at: str = Field(default_factory=utc_now)


class Handoff(BaseModel):
    id: str
    from_role: EmployeeRole
    to_role: EmployeeRole
    source_deliverable_id: str
    contract_type: Literal["material_brief", "planning_brief", "draft_review", "manager_recovery", "generic"] = "generic"
    handoff_summary: str
    payload: dict[str, object] = Field(default_factory=dict)
    expected_use: str
    status: Literal["created", "consumed"] = "created"
    created_at: str = Field(default_factory=utc_now)


class ReviewDecision(BaseModel):
    id: str
    reviewer_role: EmployeeRole
    target_deliverable_id: str
    decision: Literal["accept", "revise", "escalate"]
    rationale: str
    issue_type: Literal["none", "material_insufficiency", "structure_problem", "project_context_gap"] = "none"
    risk_level: Literal["low", "medium", "high"] = "low"
    review_checks: dict[str, str] = Field(default_factory=dict)
    suggested_revisions: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class ReassignmentAction(BaseModel):
    id: str
    job_id: str
    manager_plan_id: str
    original_work_order_id: str
    reassigned_to: EmployeeRole
    reason: str
    trigger_review_decision_id: str | None = None
    follow_up_work_order_id: str | None = None
    intervention_policy: str | None = None
    resolution_note: str | None = None
    created_at: str = Field(default_factory=utc_now)


class CompanyJob(BaseModel):
    id: str
    job_type: JobType
    project_card_id: str
    boss_goal: str
    input_path: str | None = None
    revised_path: str | None = None
    created_at: str = Field(default_factory=utc_now)


class ManagerPlan(BaseModel):
    id: str
    job_type: JobType
    boss_goal: str
    selected_employees: list[EmployeeRole] = Field(default_factory=list)
    work_order_sequence: list[str] = Field(default_factory=list)
    expected_deliverables: list[str] = Field(default_factory=list)
    final_output_strategy: str
    created_at: str = Field(default_factory=utc_now)


class JobResult(BaseModel):
    id: str
    job_id: str
    manager_plan_id: str
    project_card_id: str
    final_output_path: str
    participating_employees: list[EmployeeRole] = Field(default_factory=list)
    deliverable_ids: list[str] = Field(default_factory=list)
    handoff_ids: list[str] = Field(default_factory=list)
    review_decision_ids: list[str] = Field(default_factory=list)
    reassignment_ids: list[str] = Field(default_factory=list)
    final_status: Literal["accepted_directly", "revised_then_accepted", "escalated_with_risk"] = "accepted_directly"
    summary: str
    created_at: str = Field(default_factory=utc_now)


class FounderProfile(BaseModel):
    id: str
    researcher_profile_id: str
    display_name: str
    founder_title: str
    founder_mission: str
    created_at: str = Field(default_factory=utc_now)


class CompanyProfile(BaseModel):
    id: str
    company_name: str
    mission: str
    focus_area: str
    current_business_type: str
    founder_profile_id: str
    active_project_id: str | None = None
    created_at: str = Field(default_factory=utc_now)


class TeamConfig(BaseModel):
    company_id: str
    active_roles: list[EmployeeRole] = Field(default_factory=list)
    role_descriptions: dict[str, str] = Field(default_factory=dict)
    manager_enabled: bool = True
    defaults: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
