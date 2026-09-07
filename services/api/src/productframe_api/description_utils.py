"""Compact, evidence-preserving ecommerce descriptions."""
from typing import Any

MAX_DESCRIPTION_LENGTH = 320


def _value(source: Any, name: str, default: str = "") -> str:
    value = source.get(name) if isinstance(source, dict) else getattr(source, name, None)
    return str(value).strip() if value not in (None, "", []) else default


def concise_product_description(analysis: Any) -> str:
    """Return a complete, prioritised summary rather than slicing text blindly."""
    original = _value(analysis, "description")
    if len(original) <= MAX_DESCRIPTION_LENGTH:
        return original

    category = getattr(analysis, "category_details", None) or (analysis.get("category_details") if isinstance(analysis, dict) else None)
    global_details = getattr(analysis, "global_details", None) or (analysis.get("global_details") if isinstance(analysis, dict) else None)
    features = getattr(analysis, "features", None) or (analysis.get("features") if isinstance(analysis, dict) else None)
    feature_values = features if isinstance(features, list) else []
    product_type = _value(analysis, "product_type", "product")
    colours = _value(analysis, "colours")
    material = _value(analysis, "materials")
    fit = _value(category, "fit_and_silhouette")
    hem = _value(category, "hem_shape")
    appearance = _value(category, "material_appearance") or _value(global_details, "materials")
    finish = _value(category, "surface_finish")

    clauses = [
        f"{colours} {product_type}.",
        f"Visible features include {', '.join(feature_values[:3])}." if feature_values else "",
        f"{fit.capitalize()} with {hem}." if fit and hem else (f"{fit.capitalize()}." if fit else ""),
        f"Material appears {appearance}." if appearance else (f"{material}." if material else ""),
        f"{finish.capitalize()} finish." if finish else "",
    ]
    result = " ".join(clause for clause in clauses if clause)
    if len(result) <= MAX_DESCRIPTION_LENGTH:
        return result

    # Preserve whole clauses first; only the final fallback uses a word boundary.
    result = " ".join(clause for clause in clauses if clause)
    shortened = result[:MAX_DESCRIPTION_LENGTH].rsplit(" ", 1)[0].rstrip(" .,;")
    return shortened + "."
