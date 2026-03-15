from __future__ import annotations

from clawlab.core.models import ResearcherProfile, utc_now
from clawlab.utils.ids import create_id
from clawlab.utils.text import normalize_lines

ROLE_KEYWORDS = [
    "PhD Candidate",
    "PhD",
    "Doctoral Researcher",
    "Master",
    "MSc",
    "Research Assistant",
    "Postdoc",
]
DISCIPLINE_KEYWORDS = [
    "Computational Biology",
    "Bioinformatics",
    "Computer Science",
    "Biology",
    "Machine Learning",
    "Physics",
]
METHOD_KEYWORDS = [
    "differential expression",
    "graph-based modeling",
    "pathway enrichment",
    "literature synthesis",
    "causal inference",
    "statistics",
    "simulation",
    "single-cell",
]
TOOL_KEYWORDS = [
    "Python",
    "R",
    "Scanpy",
    "PyTorch",
    "Seurat",
    "Git",
    "LaTeX",
    "MATLAB",
    "TensorFlow",
]


def _extract_first_match(text: str, keywords: list[str], fallback: str) -> str:
    lower_text = text.lower()
    for keyword in keywords:
        if keyword.lower() in lower_text:
            return keyword
    return fallback


def _extract_matches(text: str, keywords: list[str]) -> list[str]:
    lower_text = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lower_text]


def parse_cv_to_profile(cv_text: str) -> ResearcherProfile:
    lines = normalize_lines(cv_text)
    lower_text = cv_text.lower()
    timestamp = utc_now()

    name = lines[0] if lines else "Unknown Researcher"
    role = _extract_first_match(cv_text, ROLE_KEYWORDS, "Graduate Researcher")
    discipline = _extract_first_match(cv_text, DISCIPLINE_KEYWORDS, "Interdisciplinary Research")
    methods = _extract_matches(cv_text, METHOD_KEYWORDS) or ["literature synthesis"]
    tools = _extract_matches(cv_text, TOOL_KEYWORDS) or ["text notes"]

    if "single-cell" in lower_text:
        subfield = "Single-cell analysis"
    elif "genomics" in lower_text:
        subfield = "Genomics"
    elif "systems" in lower_text:
        subfield = "Systems research"
    else:
        subfield = "Focused research track"

    common_tasks = [
        "Literature review" if "review" in lower_text else "Research synthesis",
        "Paper outlining" if "outline" in lower_text else "Structured drafting",
        "Meeting preparation" if "presentation" in lower_text or "meeting" in lower_text else "Advisor updates",
    ]

    writing_preferences = [
        "Prefer concise academic tone",
        "Use explicit section structure" if "latex" in lower_text else "Keep logic visible",
    ]
    collaboration_preferences = [
        "Summarize assumptions before drafting",
        "Keep next actions explicit",
    ]

    return ResearcherProfile(
        id=create_id("profile"),
        name=name,
        role=role,
        discipline=discipline,
        subfield=subfield,
        methods=methods,
        tools=tools,
        common_tasks=common_tasks,
        writing_preferences=writing_preferences,
        collaboration_preferences=collaboration_preferences,
        source_cv_text=cv_text,
        created_at=timestamp,
        updated_at=timestamp,
    )


def create_profile_from_founder_intake(
    *,
    name: str,
    role: str,
    discipline: str,
    subfield: str = "",
) -> ResearcherProfile:
    timestamp = utc_now()
    clean_name = name.strip() or "Unknown Researcher"
    clean_role = role.strip() or "Independent Researcher"
    clean_discipline = discipline.strip() or "Interdisciplinary Research"
    clean_subfield = subfield.strip() or "Focused research track"
    source_text = "\n".join(
        [
            clean_name,
            clean_role,
            clean_discipline,
            clean_subfield,
        ]
    )

    return ResearcherProfile(
        id=create_id("profile"),
        name=clean_name,
        role=clean_role,
        discipline=clean_discipline,
        subfield=clean_subfield,
        methods=["literature synthesis"],
        tools=["text notes"],
        common_tasks=["Research synthesis", "Structured drafting", "Advisor updates"],
        writing_preferences=["Prefer concise academic tone", "Keep logic visible"],
        collaboration_preferences=["Summarize assumptions before drafting", "Keep next actions explicit"],
        source_cv_text=source_text,
        created_at=timestamp,
        updated_at=timestamp,
    )
