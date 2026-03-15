from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
import json

from clawlab.core.models import LlmSettings, ProjectCard, ReusableAsset, TaskCard, utc_now
from clawlab.prompts.learning import build_learning_prompts
from clawlab.services.context_service import (
    get_company_handbook_context,
    get_employee_playbook_context,
    get_recent_protocol_context,
)
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


def _employee_role_for_asset(asset_type: str) -> str | None:
    if asset_type in {"writing_rule", "structure_template", "common_mistake", "sop_seed"}:
        return "draft_writer"
    if asset_type == "project_note":
        return "project_manager"
    return None


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
    role_memory_content: str | None = None
    revision_signals = _infer_revision_signals(generated_text, revised_text)
    company_handbook_excerpt, company_sources = get_company_handbook_context()
    playbook_excerpt, playbook_sources = get_employee_playbook_context("review_editor")
    protocol_excerpt, protocol_sources = get_recent_protocol_context(
        project_id=project.id,
        employee_role="review_editor",
    )
    context_sources = company_sources + playbook_sources + protocol_sources

    if llm_settings and is_llm_enabled(llm_settings, "learning"):
        try:
            system_prompt, user_prompt = build_learning_prompts(
                task=task,
                project=project,
                generated_text=generated_text,
                revised_text=revised_text,
                company_handbook_excerpt=company_handbook_excerpt,
                employee_playbook_excerpt=playbook_excerpt,
                recent_protocol_excerpt=protocol_excerpt,
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
            role_memory_content = payload.get("role_memory")
        except Exception:
            rules = None

    if rules is None:
        rules = _derive_writing_rules(generated_text, revised_text)

    assets: list[ReusableAsset] = []
    for index, rule in enumerate(rules, start=1):
        assets.append(
            ReusableAsset(
                id=create_id(f"asset_rule_{index}"),
                scope="company",
                asset_type="writing_rule",
                title=f"Writing rule {index}",
                content=rule,
                confidence=max(0.55, 0.78 - (index * 0.08)),
                source_task_id=task.id,
                project_card_id=project.id,
                employee_role="draft_writer",
                task_type=task.task_type,
                derivation_mode="llm" if llm_settings and is_llm_enabled(llm_settings, "learning") and rules is not None else "rule",
                context_sources=context_sources,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )

    assets.append(
        ReusableAsset(
            id=create_id("asset_template"),
            scope="employee",
            asset_type="structure_template",
            title="Outline template candidate",
            content=structure_template_content
            or "Use a five-part research draft flow: task framing, gap, argument structure, evidence plan, next move.",
            confidence=0.7,
            source_task_id=task.id,
            project_card_id=project.id,
            employee_role="draft_writer",
            task_type=task.task_type,
            derivation_mode="llm" if role_memory_content is not None or (llm_settings and is_llm_enabled(llm_settings, "learning") and rules is not None) else "rule",
            context_sources=context_sources,
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
            derivation_mode="llm" if project_note_content is not None else "rule",
            context_sources=context_sources,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )

    if "removed_generic_framing" in revision_signals or "compressed_expression" in revision_signals:
        assets.append(
            ReusableAsset(
                id=create_id("asset_mistake"),
                scope="employee",
                asset_type="common_mistake",
                title="Common drafting mistake",
                content="Avoid generic framing and repeated setup before making the project-specific claim.",
                confidence=0.72,
                source_task_id=task.id,
                project_card_id=project.id,
                employee_role="draft_writer",
                task_type=task.task_type,
                derivation_mode="rule",
                context_sources=context_sources,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )
    if "adjusted_structure" in revision_signals or "made_gap_explicit" in revision_signals:
        assets.append(
            ReusableAsset(
                id=create_id("asset_sop"),
                scope="company",
                asset_type="sop_seed",
                title="Draft review SOP seed",
                content="Before finalizing a draft, verify section hierarchy, explicit gap statement, and evidence placement.",
                confidence=0.74,
                source_task_id=task.id,
                project_card_id=project.id,
                employee_role="review_editor",
                task_type=task.task_type,
                derivation_mode="rule",
                context_sources=context_sources,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )
    if role_memory_content:
        assets.append(
            ReusableAsset(
                id=create_id("asset_role_memory"),
                scope="employee",
                asset_type="common_mistake",
                title="Review editor role memory",
                content=role_memory_content,
                confidence=0.71,
                source_task_id=task.id,
                project_card_id=project.id,
                employee_role="review_editor",
                task_type=task.task_type,
                derivation_mode="llm",
                context_sources=context_sources,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )

    updated_task = task.model_copy(
        update={
            "feedback_summary": (
                f"Extracted company, employee, and project memory updates. "
                f"Signals: {', '.join(revision_signals) or 'none'}."
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
