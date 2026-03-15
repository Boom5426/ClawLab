from __future__ import annotations

import re
import subprocess
import json
from collections import Counter
from pathlib import Path

from clawlab.core.models import LlmSettings, MaterialDocument, MaterialSummary, ProjectCard
from clawlab.prompts.materials import build_material_summary_prompts
from clawlab.services.llm_service import call_llm, is_llm_enabled
from clawlab.utils.ids import create_id
from clawlab.utils.text import normalize_lines

TEXT_SUFFIXES = {".txt": "txt", ".md": "md", ".rst": "md"}
PDF_SUFFIXES = {".pdf": "pdf"}
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "using",
    "study",
    "research",
    "project",
    "current",
    "which",
    "what",
    "have",
    "has",
    "were",
    "been",
    "analysis",
    "data",
    "results",
    "background",
    "because",
    "about",
    "through",
    "across",
    "their",
    "they",
    "them",
}
METHOD_ENTITY_PATTERNS = [
    "single-cell",
    "transcriptomics",
    "pathway",
    "graph",
    "model",
    "trajectory",
    "cluster",
    "resistance",
    "glioma",
    "gene",
    "spatial",
    "hypergraph",
    "diffusion",
    "histology",
    "python",
    "scanpy",
    "pytorch",
]


def detect_material_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return TEXT_SUFFIXES[suffix]
    if suffix in PDF_SUFFIXES:
        return PDF_SUFFIXES[suffix]
    if suffix == "":
        return "txt"
    raise ValueError(f"Unsupported material file type: {suffix}")


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    filtered: list[str] = []
    for line in lines:
        if not line:
            filtered.append("")
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if len(line) <= 3 and line.lower() in {"cv", "resume"}:
            continue
        filtered.append(line)
    cleaned = "\n".join(filtered)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    material_type = detect_material_type(path)
    if material_type in {"txt", "md"}:
        return _clean_text(path.read_text(encoding="utf-8"))

    if material_type == "pdf":
        result = subprocess.run(
            ["pdftotext", "-layout", "-nopgbrk", str(path), "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or "unknown pdftotext error"
            raise ValueError(f"Failed to extract text from PDF {path}: {stderr}")

        extracted = _clean_text(result.stdout)
        if not extracted:
            raise ValueError(
                f"Failed to extract text from PDF {path}: no textual content was returned. "
                "This MVP does not support OCR-only PDFs."
            )
        return extracted

    raise ValueError(f"Unsupported material file type: {path.suffix or '<no suffix>'}")


def read_material(path: Path) -> MaterialDocument:
    return MaterialDocument(
        path=str(path),
        material_type=detect_material_type(path),
        extracted_text=extract_text(path),
    )


def _pick_title(lines: list[str], path: Path) -> str:
    for line in lines[:12]:
        if 6 <= len(line) <= 140 and not line.endswith(":"):
            return line
    return path.stem.replace("_", " ").replace("-", " ").strip() or "Untitled material"


def _extract_topics(text: str, limit: int = 6) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text.lower())
    counts = Counter(token for token in tokens if token not in STOPWORDS)
    return [token for token, _ in counts.most_common(limit)]


def _extract_methods_or_entities(text: str, limit: int = 8) -> list[str]:
    lower_text = text.lower()
    found = [pattern for pattern in METHOD_ENTITY_PATTERNS if pattern in lower_text]
    acronyms = re.findall(r"\b[A-Z]{2,}[A-Z0-9\-]*\b", text)
    items = found + acronyms
    deduped: list[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return deduped[:limit]


def _paragraphs(text: str) -> list[str]:
    merged_lines: list[str] = []
    buffer: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            if buffer:
                merged_lines.append(" ".join(buffer))
                buffer = []
            continue
        buffer.append(stripped)
    if buffer:
        merged_lines.append(" ".join(buffer))

    parts = [part.strip() for part in merged_lines if part.strip()]
    normalized: list[str] = []
    for part in parts:
        part = re.sub(r"\s+", " ", part).strip()
        if len(part) >= 40:
            normalized.append(part)
    return normalized


def _project_terms(project: ProjectCard | None) -> set[str]:
    if project is None:
        return set()
    source = " ".join([project.title, project.research_question, project.current_goal, *project.blockers])
    return {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", source)}


def _score_paragraph(paragraph: str, project_terms: set[str]) -> int:
    lower = paragraph.lower()
    score = 0
    score += sum(2 for term in METHOD_ENTITY_PATTERNS if term in lower)
    score += sum(3 for term in project_terms if term in lower)
    score += 1 if any(marker in lower for marker in ("result", "finding", "evidence", "method", "gap", "question")) else 0
    return score


def _pick_useful_snippets(paragraphs: list[str], project: ProjectCard | None, limit: int = 4) -> list[str]:
    project_terms = _project_terms(project)
    ranked = sorted(paragraphs, key=lambda paragraph: (_score_paragraph(paragraph, project_terms), len(paragraph)), reverse=True)
    snippets: list[str] = []
    for paragraph in ranked:
        candidate = paragraph[:280].strip()
        if candidate not in snippets:
            snippets.append(candidate)
        if len(snippets) >= limit:
            break
    return snippets


def _relevance_to_project(summary_title: str, text: str, project: ProjectCard | None) -> str:
    if project is None:
        return "No active project context was provided when condensing this material."

    project_terms = _project_terms(project)
    overlap = [term for term in project_terms if term in text.lower() or term in summary_title.lower()]
    if overlap:
        return (
            f"This material overlaps with the active project through: {', '.join(sorted(overlap)[:6])}. "
            f"It is likely relevant to the current goal: {project.current_goal}"
        )
    return (
        f"This material does not strongly overlap by keyword with the active project, "
        f"but may still support the broader question: {project.research_question}"
    )


def condense_text_to_material_summary(
    text: str,
    source_type: str,
    source_path: str,
    project: ProjectCard | None = None,
    llm_settings: LlmSettings | None = None,
) -> MaterialSummary:
    if llm_settings and is_llm_enabled(llm_settings, "materials"):
        try:
            project_context = (
                f"title={project.title}; question={project.research_question}; goal={project.current_goal}"
                if project
                else "no active project"
            )
            system_prompt, user_prompt = build_material_summary_prompts(
                source_path=source_path,
                source_type=source_type,
                text=text,
                project_context=project_context,
            )
            content = call_llm(
                settings=llm_settings,
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=1200,
            )
            payload = json.loads(content)
            return MaterialSummary(
                id=create_id("material"),
                source_path=source_path,
                source_type=source_type,  # type: ignore[arg-type]
                title=payload["title"],
                short_summary=payload["short_summary"],
                key_topics=payload.get("key_topics", []),
                methods_or_entities=payload.get("methods_or_entities", []),
                useful_snippets=payload.get("useful_snippets", []),
                relevance_to_project=payload["relevance_to_project"],
                raw_text_excerpt=payload["raw_text_excerpt"],
            )
        except Exception:
            pass

    cleaned = _clean_text(text)
    lines = normalize_lines(cleaned)
    paragraphs = _paragraphs(cleaned)
    source = Path(source_path)
    title = _pick_title(lines, source)
    key_topics = _extract_topics(cleaned)
    methods_or_entities = _extract_methods_or_entities(cleaned)
    useful_snippets = _pick_useful_snippets(paragraphs or lines, project)

    summary_parts = []
    if title:
        summary_parts.append(f"Material focus: {title}.")
    if key_topics:
        summary_parts.append(f"Key topics include {', '.join(key_topics[:4])}.")
    if methods_or_entities:
        summary_parts.append(f"Methods or entities mentioned: {', '.join(methods_or_entities[:4])}.")
    if useful_snippets:
        summary_parts.append(f"Most useful snippet: {useful_snippets[0]}")
    short_summary = " ".join(summary_parts)[:420]

    return MaterialSummary(
        id=create_id("material"),
        source_path=source_path,
        source_type=source_type,  # type: ignore[arg-type]
        title=title,
        short_summary=short_summary,
        key_topics=key_topics,
        methods_or_entities=methods_or_entities,
        useful_snippets=useful_snippets[:6],
        relevance_to_project=_relevance_to_project(title, cleaned, project),
        raw_text_excerpt=cleaned[:600],
    )


def condense_material(
    path: Path,
    project: ProjectCard | None = None,
    llm_settings: LlmSettings | None = None,
) -> MaterialSummary:
    document = read_material(path)
    return condense_text_to_material_summary(
        document.extracted_text,
        source_type=document.material_type,
        source_path=document.path,
        project=project,
        llm_settings=llm_settings,
    )
