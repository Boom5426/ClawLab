from __future__ import annotations

import re
from collections import defaultdict

from clawlab.core.models import MaterialSummary, ProjectCard, ResearcherProfile, ReusableAsset


def group_assets_by_scope(assets: list[ReusableAsset]) -> dict[str, list[ReusableAsset]]:
    grouped: dict[str, list[ReusableAsset]] = defaultdict(list)
    for asset in assets:
        grouped[asset.scope].append(asset)
    return dict(grouped)


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text)}


def _asset_relevance_score(
    asset: ReusableAsset,
    *,
    task_type: str,
    project: ProjectCard,
    profile: ResearcherProfile,
    material_summaries: list[MaterialSummary],
) -> int:
    score = 0
    project_tokens = _tokenize(" ".join([project.title, project.research_question, project.current_goal, *project.blockers]))
    profile_tokens = _tokenize(" ".join([profile.discipline, profile.subfield, *profile.methods, *profile.tools]))
    material_text_parts: list[str] = []
    for summary in material_summaries:
        material_text_parts.extend(
            [
                summary.title,
                summary.short_summary,
                " ".join(summary.key_topics),
                " ".join(summary.methods_or_entities),
            ]
        )
    material_tokens = _tokenize(" ".join(material_text_parts))
    asset_tokens = _tokenize(" ".join([asset.title, asset.content]))

    score += 5 if asset.task_type == task_type else 0
    score += 6 if asset.scope == "project" and asset.project_card_id == project.id else 0
    score += 2 if asset.scope == "global" else 0
    score += len(project_tokens & asset_tokens) * 3
    score += len(profile_tokens & asset_tokens)
    score += len(material_tokens & asset_tokens) * 2
    score += 1 if asset.asset_type == "writing_rule" else 0
    return score


def select_top_assets(assets: list[ReusableAsset], *, limit: int = 5) -> list[ReusableAsset]:
    return assets[:limit]


def retrieve_assets_for_task(
    *,
    task_type: str,
    project: ProjectCard,
    profile: ResearcherProfile,
    material_summaries: list[MaterialSummary],
    assets: list[ReusableAsset],
) -> list[ReusableAsset]:
    ranked = sorted(
        assets,
        key=lambda asset: (
            _asset_relevance_score(
                asset,
                task_type=task_type,
                project=project,
                profile=profile,
                material_summaries=material_summaries,
            ),
            asset.created_at,
        ),
        reverse=True,
    )
    filtered = [asset for asset in ranked if _asset_relevance_score(
        asset,
        task_type=task_type,
        project=project,
        profile=profile,
        material_summaries=material_summaries,
    ) > 0]
    return select_top_assets(filtered or ranked, limit=5)
