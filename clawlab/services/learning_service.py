from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher

from clawlab.core.models import ProjectCard, ReusableAsset, TaskCard, utc_now
from clawlab.utils.ids import create_id


def _derive_writing_rules(generated_text: str, revised_text: str) -> list[str]:
    rules: list[str] = []
    generated_lines = [line.strip() for line in generated_text.splitlines() if line.strip()]
    revised_lines = [line.strip() for line in revised_text.splitlines() if line.strip()]

    if len(revised_text) < len(generated_text):
        rules.append("Keep drafts tighter and remove repeated framing.")
    if revised_text.count("##") > generated_text.count("##"):
        rules.append("Use clearer hierarchical headings instead of long bullet runs.")
    if "evidence" in revised_text.lower() and "evidence" not in generated_text.lower():
        rules.append("Anchor claims with explicit evidence language earlier.")
    if any("gap" in line.lower() for line in revised_lines) and not any("gap" in line.lower() for line in generated_lines):
        rules.append("State the project-specific gap explicitly instead of implying it.")
    if Counter(line.startswith("- ") for line in revised_lines)[True] < Counter(line.startswith("- ") for line in generated_lines)[True]:
        rules.append("Prefer fewer bullets and more section-level synthesis when possible.")
    if not rules:
        ratio = SequenceMatcher(a=generated_text, b=revised_text).ratio()
        if ratio < 0.92:
            rules.append("Preserve structure, but adapt wording more aggressively to user style.")
    return rules[:3]


def derive_assets_from_revision(
    task: TaskCard,
    project: ProjectCard,
    *,
    generated_text: str,
    revised_text: str,
) -> tuple[TaskCard, ProjectCard, list[ReusableAsset]]:
    timestamp = utc_now()
    rules = _derive_writing_rules(generated_text, revised_text)

    assets: list[ReusableAsset] = []
    for index, rule in enumerate(rules, start=1):
        assets.append(
            ReusableAsset(
                id=create_id(f"asset_rule_{index}"),
                scope="profile",
                asset_type="writing_rule",
                title=f"Writing rule {index}",
                content=rule,
                confidence=max(0.55, 0.78 - (index * 0.08)),
                source_task_id=task.id,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )

    assets.append(
        ReusableAsset(
            id=create_id("asset_template"),
            scope="task",
            asset_type="structure_template",
            title="Outline template candidate",
            content="Use a five-part research draft flow: task framing, gap, argument structure, evidence plan, next move.",
            confidence=0.7,
            source_task_id=task.id,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
    assets.append(
        ReusableAsset(
            id=create_id("asset_note"),
            scope="project",
            asset_type="project_note",
            title="Project note update",
            content=(
                f"Recent revision for {project.title} emphasizes a tighter storyline that directly resolves the "
                f"current blocker: {'; '.join(project.blockers) or 'no blocker listed'}."
            ),
            confidence=0.76,
            source_task_id=task.id,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )

    updated_task = task.model_copy(
        update={
            "feedback_summary": (
                f"Extracted {len(rules)} writing rule(s), one structure template candidate, "
                "and one project note update."
            ),
            "updated_at": timestamp,
        }
    )
    updated_project = project.model_copy(
        update={
            "next_step": "Reuse learned writing rules and structure template in the next drafting cycle.",
            "updated_at": timestamp,
        }
    )
    return updated_task, updated_project, assets
