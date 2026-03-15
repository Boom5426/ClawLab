from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
import json

from clawlab.core.models import LlmSettings, ProjectCard, ReusableAsset, TaskCard, utc_now
from clawlab.prompts.learning import build_learning_prompts
from clawlab.services.llm_service import call_llm, is_llm_enabled
from clawlab.utils.ids import create_id


def _infer_revision_signals(generated_text: str, revised_text: str) -> list[str]:
    signals: list[str] = []
    generated_lines = [line.strip() for line in generated_text.splitlines() if line.strip()]
    revised_lines = [line.strip() for line in revised_text.splitlines() if line.strip()]

    if len(revised_text) < len(generated_text):
        signals.append("compressed_expression")
    if len(revised_lines) > len(generated_lines):
        signals.append("added_background")
    if revised_text.count("##") != generated_text.count("##"):
        signals.append("adjusted_structure")
    generic_markers = ("broad", "general", "overview", "important", "helpful", "useful")
    generated_generic = sum(marker in generated_text.lower() for marker in generic_markers)
    revised_generic = sum(marker in revised_text.lower() for marker in generic_markers)
    if revised_generic < generated_generic:
        signals.append("removed_generic_framing")
    if "gap" in revised_text.lower() and "gap" not in generated_text.lower():
        signals.append("made_gap_explicit")
    return signals


def _derive_writing_rules(generated_text: str, revised_text: str) -> list[str]:
    rules: list[str] = []
    signals = _infer_revision_signals(generated_text, revised_text)
    generated_lines = [line.strip() for line in generated_text.splitlines() if line.strip()]
    revised_lines = [line.strip() for line in revised_text.splitlines() if line.strip()]

    if "compressed_expression" in signals:
        rules.append("Keep drafts tighter and remove repeated framing.")
    if "added_background" in signals:
        rules.append("Add missing project-specific background only when it changes the argument.")
    if "adjusted_structure" in signals and revised_text.count("##") > generated_text.count("##"):
        rules.append("Use clearer hierarchical headings instead of long bullet runs.")
    if "evidence" in revised_text.lower() and "evidence" not in generated_text.lower():
        rules.append("Anchor claims with explicit evidence language earlier.")
    if "made_gap_explicit" in signals:
        rules.append("State the project-specific gap explicitly instead of implying it.")
    if "removed_generic_framing" in signals or Counter(line.startswith("- ") for line in revised_lines)[True] < Counter(line.startswith("- ") for line in generated_lines)[True]:
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
    llm_settings: LlmSettings | None = None,
) -> tuple[TaskCard, ProjectCard, list[ReusableAsset]]:
    timestamp = utc_now()
    rules: list[str] | None = None
    structure_template_content: str | None = None
    project_note_content: str | None = None
    revision_signals = _infer_revision_signals(generated_text, revised_text)

    if llm_settings and is_llm_enabled(llm_settings, "learning"):
        try:
            system_prompt, user_prompt = build_learning_prompts(
                task=task,
                project=project,
                generated_text=generated_text,
                revised_text=revised_text,
            )
            content = call_llm(
                settings=llm_settings,
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=1200,
            )
            payload = json.loads(content)
            rules = payload.get("writing_rules", [])[:3]
            structure_template_content = payload.get("structure_template")
            project_note_content = payload.get("project_note")
        except Exception:
            rules = None

    if rules is None:
        rules = _derive_writing_rules(generated_text, revised_text)

    assets: list[ReusableAsset] = []
    for index, rule in enumerate(rules, start=1):
        assets.append(
            ReusableAsset(
                id=create_id(f"asset_rule_{index}"),
                scope="global",
                asset_type="writing_rule",
                title=f"Writing rule {index}",
                content=rule,
                confidence=max(0.55, 0.78 - (index * 0.08)),
                source_task_id=task.id,
                project_card_id=project.id,
                task_type=task.task_type,
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
            content=structure_template_content
            or "Use a five-part research draft flow: task framing, gap, argument structure, evidence plan, next move.",
            confidence=0.7,
            source_task_id=task.id,
            project_card_id=project.id,
            task_type=task.task_type,
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
            content=project_note_content
            or (
                f"Recent revision for {project.title} emphasizes a tighter storyline that directly resolves the "
                f"current blocker: {'; '.join(project.blockers) or 'no blocker listed'}. "
                f"Observed revision signals: {', '.join(revision_signals) or 'no dominant signal'}."
            ),
            confidence=0.76,
            source_task_id=task.id,
            project_card_id=project.id,
            task_type=task.task_type,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )

    updated_task = task.model_copy(
        update={
            "feedback_summary": (
                f"Extracted {len(rules)} writing rule(s), one structure template candidate, "
                f"and one project note update. Signals: {', '.join(revision_signals) or 'none'}."
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
