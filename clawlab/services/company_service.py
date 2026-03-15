from __future__ import annotations

from clawlab.core.models import CompanyProfile, FounderProfile, ResearcherProfile, TeamConfig
from clawlab.services.employee_service import get_employee_spec
from clawlab.utils.ids import create_id


DEFAULT_STARTER_TEAM = [
    "literature_analyst",
    "project_manager",
    "draft_writer",
    "review_editor",
]


def create_founder_profile(
    researcher_profile: ResearcherProfile,
    *,
    founder_mission: str,
) -> FounderProfile:
    return FounderProfile(
        id=create_id("founder"),
        researcher_profile_id=researcher_profile.id,
        display_name=researcher_profile.name,
        founder_title=researcher_profile.role or "Founder",
        founder_mission=founder_mission.strip() or f"Build a focused research company around {researcher_profile.discipline}.",
    )


def recommend_starter_team(
    researcher_profile: ResearcherProfile,
    *,
    prefer_small_team: bool = False,
) -> list[str]:
    if prefer_small_team:
        if "Literature review" in researcher_profile.common_tasks:
            return ["literature_analyst", "draft_writer", "review_editor"]
        return ["project_manager", "draft_writer", "review_editor"]
    return DEFAULT_STARTER_TEAM.copy()


def create_company_profile(
    *,
    company_name: str,
    mission: str,
    focus_area: str,
    current_business_type: str,
    founder_profile_id: str,
    active_project_id: str | None = None,
) -> CompanyProfile:
    return CompanyProfile(
        id=create_id("company"),
        company_name=company_name.strip() or "ClawLab Research Co.",
        mission=mission.strip() or "Turn research intent into reusable workflow output.",
        focus_area=focus_area.strip() or "Focused research operations",
        current_business_type=current_business_type.strip() or "Single-founder research company",
        founder_profile_id=founder_profile_id,
        active_project_id=active_project_id,
    )


def create_team_config(
    *,
    company_id: str,
    active_roles: list[str],
    manager_enabled: bool = True,
) -> TeamConfig:
    role_descriptions = {
        role: get_employee_spec(role).description
        for role in active_roles
    }
    return TeamConfig(
        company_id=company_id,
        active_roles=active_roles,  # type: ignore[arg-type]
        role_descriptions=role_descriptions,
        manager_enabled=manager_enabled,
        defaults={
            "starter_mode": "full" if len(active_roles) >= 4 else "lean",
            "default_job_type": "literature-brief",
        },
    )
