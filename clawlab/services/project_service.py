from __future__ import annotations

import re

from clawlab.core.models import ProjectCard, ResearcherProfile, utc_now
from clawlab.utils.ids import create_id
from clawlab.utils.text import normalize_lines, split_csvish


QUESTION_PATTERNS = (
    r"(how|why|what|whether|can|does|do)\b.*\?",
    r"(investigate|understand|characterize|evaluate|identify|map)\b.{0,120}",
)
BLOCKER_HINTS = ("block", "stuck", "challenge", "missing", "need", "unclear", "卡", "难", "problem")


def _guess_title(project_brief: str, title_hint: str = "") -> str:
    if title_hint.strip():
        return title_hint.strip()

    lines = normalize_lines(project_brief)
    for line in lines[:8]:
        if 6 <= len(line) <= 120 and not line.endswith("."):
            return line
    if lines:
        return lines[0][:80]
    return "Active research project"


def _guess_research_question(project_brief: str, title: str) -> str:
    lines = normalize_lines(project_brief)
    lower_brief = project_brief.lower()
    for pattern in QUESTION_PATTERNS:
        match = re.search(pattern, lower_brief)
        if match:
            return project_brief[match.start():match.end()].strip().rstrip(".") + ("?" if "?" not in match.group(0) else "")

    for line in lines[:12]:
        if any(token in line.lower() for token in ("question", "goal", "aim", "objective", "hypothesis")):
            return line.strip().rstrip(".")

    return f"Clarify the core research question behind: {title}"


def _derive_blockers(current_goal: str, project_brief: str) -> list[str]:
    blocker_lines = []
    for source in [current_goal, project_brief]:
        for line in normalize_lines(source):
            if any(hint in line.lower() for hint in BLOCKER_HINTS):
                blocker_lines.append(line)
    return blocker_lines[:4] or ["Need clearer project framing for the next task."]


def _derive_materials(source_label: str | None, project_brief: str) -> list[str]:
    materials: list[str] = []
    if source_label:
        materials.append(source_label)

    lines = normalize_lines(project_brief)
    for line in lines[:4]:
        if 8 <= len(line) <= 100:
            materials.append(line)

    deduped: list[str] = []
    for item in materials:
        if item not in deduped:
            deduped.append(item)
    return deduped[:5] or ["Project description provided inline"]


def create_project_from_intake(
    profile: ResearcherProfile,
    *,
    project_brief: str,
    current_goal: str,
    title_hint: str = "",
    source_label: str | None = None,
) -> ProjectCard:
    timestamp = utc_now()
    title = _guess_title(project_brief, title_hint)
    research_question = _guess_research_question(project_brief, title)
    blockers = _derive_blockers(current_goal, project_brief)
    materials = _derive_materials(source_label, project_brief)

    return ProjectCard(
        id=create_id("project"),
        researcher_profile_id=profile.id,
        title=title,
        research_question=research_question,
        current_goal=current_goal.strip() or "Prepare a structured artifact for the next milestone.",
        current_stage="Focused intake",
        blockers=blockers,
        materials=materials,
        next_step=current_goal.strip() or "Translate the current materials into a usable draft.",
        created_at=timestamp,
        updated_at=timestamp,
    )


def create_project_from_answers(
    profile: ResearcherProfile,
    *,
    title: str,
    desired_outcome: str,
    blocker: str,
    materials: str,
) -> ProjectCard:
    combined_brief = "\n".join(
        [
            title.strip(),
            f"Blocker: {blocker.strip()}" if blocker.strip() else "",
            f"Materials: {materials.strip()}" if materials.strip() else "",
        ]
    ).strip()
    project = create_project_from_intake(
        profile,
        project_brief=combined_brief or title,
        current_goal=desired_outcome,
        title_hint=title or f"{profile.subfield} project",
        source_label=materials if materials.strip() else None,
    )
    if blocker.strip():
        project = project.model_copy(update={"blockers": split_csvish(blocker) or project.blockers})
    return project
