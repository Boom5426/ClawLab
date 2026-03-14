from __future__ import annotations

import subprocess
from pathlib import Path

from clawlab.core.models import MaterialDocument

TEXT_SUFFIXES = {".txt": "txt", ".md": "md", ".rst": "md"}
PDF_SUFFIXES = {".pdf": "pdf"}


def detect_material_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return TEXT_SUFFIXES[suffix]
    if suffix in PDF_SUFFIXES:
        return PDF_SUFFIXES[suffix]
    if suffix == "":
        return "txt"
    raise ValueError(f"Unsupported material file type: {suffix}")


def extract_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    material_type = detect_material_type(path)
    if material_type in {"txt", "md"}:
        return path.read_text(encoding="utf-8")

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

        extracted = result.stdout.strip()
        if not extracted:
            raise ValueError(
                f"Failed to extract text from PDF {path}: no textual content was returned. "
                "This MVP does not support OCR-only PDFs."
            )
        return extracted

    raise ValueError(f"Unsupported material file type: {path.suffix or '<no suffix>'}")


def read_material(path: Path) -> MaterialDocument:
    extracted_text = extract_text(path)
    return MaterialDocument(
        path=str(path),
        material_type=detect_material_type(path),
        extracted_text=extracted_text,
    )


def read_cv_text(path: Path) -> str:
    return extract_text(path)
