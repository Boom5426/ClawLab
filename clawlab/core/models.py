from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    expected_output: str
    generated_draft_path: str
    revised_draft_path: str | None = None
    feedback_summary: str = ""
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class ReusableAsset(BaseModel):
    id: str
    scope: Literal["global", "project", "task"]
    asset_type: Literal["writing_rule", "structure_template", "project_note"]
    title: str
    content: str
    confidence: float
    source_task_id: str
    project_card_id: str | None = None
    task_type: Literal["literature-outline", "paper-outline"] | None = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class LlmSettings(BaseModel):
    mode: Literal["local", "hybrid"] = "local"
    provider: Literal["none", "openai"] = "none"
    model: str = "gpt-4o-mini"
    use_llm_for_materials: bool = False
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
    created_at: str = Field(default_factory=utc_now)


class TaskPlan(BaseModel):
    task_type: Literal["literature-outline", "paper-outline"]
    task_goal: str
    output_strategy: str
    key_points_to_cover: list[str] = Field(default_factory=list)
    recommended_structure: list[str] = Field(default_factory=list)
    project_considerations: list[str] = Field(default_factory=list)
    selected_assets: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
