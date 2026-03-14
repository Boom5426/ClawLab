from __future__ import annotations

from clawlab.core.models import ProjectCard, ResearcherProfile


def _material_bullets(input_materials: list[str], limit: int = 6) -> str:
    items = input_materials[:limit] if input_materials else ["No materials provided"]
    return "\n".join(f"- {item}" for item in items)


def render_literature_outline(
    profile: ResearcherProfile,
    project: ProjectCard,
    input_summary: str,
    input_materials: list[str],
) -> str:
    material_lines = _material_bullets(input_materials)
    methods = ", ".join(profile.methods) or "literature synthesis"
    return f"""# Literature Outline

## 1. Task Framing
- Researcher: {profile.name} ({profile.role})
- Project: {project.title}
- Research question: {project.research_question}
- Immediate task: {input_summary}

## 2. What The Review Must Clarify
- Which claims are already well supported in {profile.subfield}?
- Which disagreements or blind spots directly affect this project?
- Which evidence would most reduce the current blocker: {'; '.join(project.blockers) or 'no blocker listed'}?

## 3. Suggested Review Structure
### 3.1 Field baseline
- Summarize the accepted view in {profile.discipline}.
- Separate broad background from project-specific relevance.

### 3.2 Competing explanations
- Organize papers by mechanism, state transition logic, or analytical approach.
- Make disagreement explicit instead of listing studies sequentially.

### 3.3 Methods and evidence quality
- Track which methods recur across the literature: {methods}
- Note where evidence is descriptive versus causal.

### 3.4 Gap and project implication
- End each section by asking what remains unresolved for {project.title}.
- Tie the final gap statement to the project's current goal: {project.current_goal}

## 4. Materials Extracted For This Draft
{material_lines}

## 5. Drafting Notes
- Prefer claim-first section openings.
- Keep evidence and limitations adjacent.
- Close with a short synthesis that points to the next experiment, analysis, or writing move.
"""


def render_paper_outline(
    profile: ResearcherProfile,
    project: ProjectCard,
    input_summary: str,
    input_materials: list[str],
) -> str:
    material_lines = _material_bullets(input_materials)
    blockers = "; ".join(project.blockers) or "No blockers specified"
    return f"""# Paper Outline

## 1. Working Title
- {project.title}

## 2. Problem Setup
- Field: {profile.discipline}
- Subfield: {profile.subfield}
- Core question: {project.research_question}
- Immediate drafting objective: {input_summary}

## 3. Gap
- The main missing logic or unresolved point is: {blockers}
- State why this matters for the project's current goal: {project.current_goal}

## 4. Central Storyline
- Claim 1: explain the scientific problem and stakes.
- Claim 2: show why existing work does not fully resolve it.
- Claim 3: position this project as a focused answer, not a generic survey.

## 5. Section Plan
### 5.1 Introduction
- Define the problem.
- Narrow quickly to the project-specific question.

### 5.2 Related work and gap
- Group prior work by explanatory strategy rather than chronology.
- End with the exact gap this paper addresses.

### 5.3 Study design or analysis logic
- Explain why the planned methods fit the question.
- Make assumptions, constraints, and expected comparisons explicit.

### 5.4 Results or expected evidence
- List the strongest evidence already available.
- Separate observed results from planned validation.

### 5.5 Discussion
- Interpret significance.
- Note limitations.
- Point to the next concrete research step: {project.next_step}

## 6. Materials To Ground The Draft
{material_lines}

## 7. Immediate Writing Instructions
- Keep the storyline tighter than a generic review.
- Prefer explicit subsection headings.
- Make every section end with what it contributes to the paper argument.
"""
