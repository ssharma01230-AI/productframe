"""Evaluate whether source media supports a generation template."""
from typing import Any

from .generation_templates import GenerationTemplate


def evaluate_template(template: GenerationTemplate, evidence: list[dict[str, Any] | None]) -> dict[str, Any]:
    available: set[str] = set()
    for item in evidence:
        if not item:
            continue
        available.update(str(value) for value in item.get("views", []) or [])
        available.update(str(value) for value in item.get("evidence", []) or [])
    missing = [item for item in template.required_evidence if item not in available]
    return {
        "template_id": template.id,
        "status": "ready" if not missing else "needs_image",
        "required_evidence": list(template.required_evidence),
        "missing_evidence": missing,
    }
