from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime

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
    if asset.asset_type == "project_note" and asset.project_card_id == project.id:
        score += 2
    return score


def _parse_created_at(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min


def select_top_assets(assets: list[ReusableAsset], *, limit: int = 5) -> list[ReusableAsset]:
    if not assets:
        return []

    selected: list[ReusableAsset] = []
    seen_types: set[str] = set()
    seen_scopes: set[str] = set()

    for asset in assets:
        if len(selected) >= limit:
            break
        if asset.scope == "project" and asset.scope not in seen_scopes:
            selected.append(asset)
            seen_scopes.add(asset.scope)
            seen_types.add(asset.asset_type)

    for asset in assets:
        if len(selected) >= limit:
            break
        if asset.id in {item.id for item in selected}:
            continue
        if asset.asset_type not in seen_types:
            selected.append(asset)
            seen_scopes.add(asset.scope)
            seen_types.add(asset.asset_type)

    for asset in assets:
        if len(selected) >= limit:
            break
        if asset.id not in {item.id for item in selected}:
            selected.append(asset)
            seen_scopes.add(asset.scope)
            seen_types.add(asset.asset_type)

    return selected[:limit]


def retrieve_assets_for_task(
    *,
    task_type: str,
    project: ProjectCard,
    profile: ResearcherProfile,
    material_summaries: list[MaterialSummary],
    assets: list[ReusableAsset],
) -> list[ReusableAsset]:
    scored_assets = [
        (
            asset,
            _asset_relevance_score(
                asset,
                task_type=task_type,
                project=project,
                profile=profile,
                material_summaries=material_summaries,
            ),
        )
        for asset in assets
    ]
    ranked = [
        asset
        for asset, _score in sorted(
            scored_assets,
            key=lambda item: (item[1], _parse_created_at(item[0].created_at)),
            reverse=True,
        )
    ]
    filtered = [asset for asset, score in scored_assets if score > 0]
    filtered = sorted(filtered, key=lambda asset: (
        _asset_relevance_score(
            asset,
            task_type=task_type,
            project=project,
            profile=profile,
            material_summaries=material_summaries,
        ),
        _parse_created_at(asset.created_at),
    ), reverse=True)
    return select_top_assets(filtered or ranked, limit=5)
