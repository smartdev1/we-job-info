"""Template registry for rendering backgrounds."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


@dataclass(frozen=True)
class RenderTemplate:
    id: str
    name: str
    kind: str  # "emploi" | "stage"
    background: Path


TEMPLATES: list[RenderTemplate] = [
    RenderTemplate(id="emploi", name="Offre emploi", kind="emploi", background=TEMPLATES_DIR / "offre-emploi.jpeg"),
    RenderTemplate(id="stage", name="Offre stage", kind="stage", background=TEMPLATES_DIR / "offre-stage.jpeg"),
]


def get_template(template_id: str) -> RenderTemplate:
    for t in TEMPLATES:
        if t.id == template_id:
            return t
    raise KeyError(f"unknown template: {template_id}")


def list_templates() -> list[RenderTemplate]:
    return list(TEMPLATES)