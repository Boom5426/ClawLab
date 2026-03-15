from pathlib import Path

from clawlab.services.material_service import detect_material_type, extract_text, read_material


def read_cv_text(path: Path) -> str:
    return extract_text(path)
