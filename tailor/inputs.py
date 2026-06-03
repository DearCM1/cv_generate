"""
File loaders for job-description and company-profile inputs.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

from pathlib import Path


# =============================================================
# functions
# =============================================================

def load_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in {".md", ".txt", ""}:
        return path.read_text(encoding="utf-8")
    
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    
    raise ValueError(f"Unsupported input file type: {suffix} ({path})")
