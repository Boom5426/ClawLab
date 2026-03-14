from __future__ import annotations

from clawlab.core.models import ProjectCard, ResearcherProfile, utc_now
from clawlab.utils.ids import create_id
from clawlab.utils.text import split_csvish


def create_project_from_answers(
    profile: ResearcherProfile,
    *,
    title: str,
    desired_outcome: str,
    blocker: str,
    materials: str,
) -> ProjectCard:
    timestamp = utc_now()
    blocker_lines = split_csvish(blocker) or ["Need clearer task decomposition"]
    material_lines = split_csvish(materials) or ["No materials listed"]

    return ProjectCard(
        id=create_id("project"),
        researcher_profile_id=profile.id,
        title=title or f"{profile.subfield} project",
        research_question=title or "Clarify the active research question from the current project.",
        current_goal=desired_outcome or "Prepare a structured artifact for the next milestone.",
        current_stage="Blocked progress" if blocker_lines else "Scoping",
        blockers=blocker_lines,
        materials=material_lines,
        next_step=desired_outcome or "Translate the current materials into a usable draft.",
        created_at=timestamp,
        updated_at=timestamp,
    )
