from __future__ import annotations

from clawlab.core.models import MaterialSummary, ProjectCard, ResearcherProfile, ReusableAsset, TaskPlan


def _material_bullets(items: list[str], limit: int = 6) -> str:
    items = items[:limit] if items else ["No material evidence extracted"]
    return "\n".join(f"- {item}" for item in items)


def render_literature_outline(
    profile: ResearcherProfile,
    project: ProjectCard,
    material_summaries: list[MaterialSummary],
    task_plan: TaskPlan,
    retrieved_assets: list[ReusableAsset],
) -> str:
    primary_material = material_summaries[0]
    material_lines = _material_bullets(primary_material.useful_snippets)
    methods = ", ".join(profile.methods) or "literature synthesis"
    topics = ", ".join(primary_material.key_topics[:5]) or "no dominant topics extracted"
    entities = ", ".join(primary_material.methods_or_entities[:6]) or "no strong methods or entities extracted"
    asset_lines = _material_bullets([f"{asset.asset_type}: {asset.title}" for asset in retrieved_assets], limit=4)
    plan_lines = _material_bullets(task_plan.key_points_to_cover, limit=5)
    structure_lines = _material_bullets(task_plan.recommended_structure, limit=6)
    return f"""# Literature Outline

## 1. Task Framing
- Researcher: {profile.name} ({profile.role})
- Project: {project.title}
- Research question: {project.research_question}
- Material title: {primary_material.title}
- Material summary: {primary_material.short_summary}
- Output strategy: {task_plan.output_strategy}

## 2. What The Review Must Clarify
- Which claims are already well supported in {profile.subfield}?
- Which disagreements or blind spots directly affect this project?
- Which evidence would most reduce the current blocker: {'; '.join(project.blockers) or 'no blocker listed'}?
- Which planned points must be covered:
{plan_lines}

## 3. Material-Derived Focus
- Key topics surfaced from the material: {topics}
- Methods or entities worth tracking: {entities}
- Relevance to the current project: {primary_material.relevance_to_project}

## 4. Suggested Review Structure
### Planned structure
{structure_lines}

### 4.1 Field baseline
- Summarize the accepted view in {profile.discipline}.
- Separate broad background from project-specific relevance.

### 4.2 Competing explanations
- Organize papers by mechanism, state transition logic, or analytical approach.
- Make disagreement explicit instead of listing studies sequentially.

### 4.3 Methods and evidence quality
- Track which methods recur across the literature: {methods}
- Note where evidence is descriptive versus causal.

### 4.4 Gap and project implication
- End each section by asking what remains unresolved for {project.title}.
- Tie the final gap statement to the project's current goal: {project.current_goal}

## 5. Useful Material Snippets
{material_lines}

## 6. Retrieved Assets To Reuse
{asset_lines}

## 7. Drafting Notes
- Prefer claim-first section openings.
- Keep evidence and limitations adjacent.
- Close with a short synthesis that points to the next experiment, analysis, or writing move.
"""


def render_paper_outline(
    profile: ResearcherProfile,
    project: ProjectCard,
    material_summaries: list[MaterialSummary],
    task_plan: TaskPlan,
    retrieved_assets: list[ReusableAsset],
) -> str:
    primary_material = material_summaries[0]
    material_lines = _material_bullets(primary_material.useful_snippets)
    blockers = "; ".join(project.blockers) or "No blockers specified"
    entities = ", ".join(primary_material.methods_or_entities[:6]) or "no strong methods or entities extracted"
    topics = ", ".join(primary_material.key_topics[:5]) or "no dominant topics extracted"
    asset_lines = _material_bullets([f"{asset.asset_type}: {asset.title}" for asset in retrieved_assets], limit=4)
    structure_lines = _material_bullets(task_plan.recommended_structure, limit=6)
    return f"""# Paper Outline

## 1. Working Title
- {project.title}

## 2. Problem Setup
- Field: {profile.discipline}
- Subfield: {profile.subfield}
- Core question: {project.research_question}
- Material title: {primary_material.title}
- Material summary: {primary_material.short_summary}
- Output strategy: {task_plan.output_strategy}

## 3. Gap
- The main missing logic or unresolved point is: {blockers}
- State why this matters for the project's current goal: {project.current_goal}

## 4. Material-Derived Evidence Plan
- Key topics from the material: {topics}
- Methods or entities emphasized in the material: {entities}
- Relevance to the project: {primary_material.relevance_to_project}

## 5. Central Storyline
- Claim 1: explain the scientific problem and stakes.
- Claim 2: show why existing work does not fully resolve it.
- Claim 3: position this project as a focused answer, not a generic survey.

## 6. Section Plan
### Recommended ordering
{structure_lines}

### 6.1 Introduction
- Define the problem.
- Narrow quickly to the project-specific question.

### 6.2 Related work and gap
- Group prior work by explanatory strategy rather than chronology.
- End with the exact gap this paper addresses.

### 6.3 Study design or analysis logic
- Explain why the planned methods fit the question.
- Make assumptions, constraints, and expected comparisons explicit.

### 6.4 Results or expected evidence
- List the strongest evidence already available.
- Separate observed results from planned validation.

### 6.5 Discussion
- Interpret significance.
- Note limitations.
- Point to the next concrete research step: {project.next_step}

## 7. Useful Material Snippets
{material_lines}

## 8. Retrieved Assets To Reuse
{asset_lines}

## 9. Immediate Writing Instructions
- Keep the storyline tighter than a generic review.
- Prefer explicit subsection headings.
- Make every section end with what it contributes to the paper argument.
"""
