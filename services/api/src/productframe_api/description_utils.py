"""Deterministic, category-aware user-facing product descriptions."""
from typing import Any

from .category_registry import controlled_subtype_label

MAX_DESCRIPTION_LENGTH = 320


def _get(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _text(value: Any) -> str:
    if value in (None, "", [], {}, "not_visible", "not_applicable", "none visible", "not determinable"):
        return ""
    text = str(value).strip()
    # Never expose serialized schema/pseudo-code fragments to customers.
    if "=" in text:
        text = text.split("=", 1)[-1].strip(" '\"")
    return text.replace("_", " ").replace("`", "").strip(" .;,")


def _first_detail(details: Any, *names: str) -> str:
    for name in names:
        value = _text(_get(details, name))
        if value:
            return value
    return ""


def bound_description(text: str, *, limit: int = MAX_DESCRIPTION_LENGTH) -> str:
    """Bound user-facing prose without exceeding the database column limit."""
    value = " ".join(str(text or "").split()).strip(" .,;")
    if not value:
        return ""
    if len(value) >= limit:
        value = value[: max(1, limit - 1)].rsplit(" ", 1)[0].rstrip(" .,;")
    return value + "."


def concise_product_description(analysis: Any) -> str:
    """Build a short customer-facing description from controlled evidence only.

    The model-generated description is deliberately ignored. This prevents
    styling items, unsupported construction, long product_type prose and
    serialized field syntax from leaking into the catalogue description.
    """
    category = str(_get(analysis, "category", "product")).split(".")[-1].lower()
    details = _get(analysis, "category_details") or {}
    global_details = _get(analysis, "global_details") or {}
    colour_details = _get(analysis, "colour_details") or _get(global_details, "colour") or {}
    family = _text(_get(details, "family") or _get(analysis, "product_family")) or None
    subtype = _text(_get(details, "subtype")) or None
    label = controlled_subtype_label(category=category, family=family, subtype=subtype, product_type=None)
    colour = _first_detail(colour_details, "primary_colour") or _text(_get(analysis, "colours")) or "The product"
    material_details = _get(global_details, "materials") or {}
    material = _first_detail(material_details, "appearance", "texture", "finish") or _text(_get(analysis, "materials"))
    features = [_text(item) for item in (_get(analysis, "features") or [])]
    styling_terms = ("sock", "trainer", "sneaker", "shoe", "ballet flat", "t-shirt", "top", "model", "outfit")
    features = [item for item in features if item and not any(term in item.lower() for term in styling_terms)]

    sentences: list[str] = []
    if category == "footwear":
        toe = _first_detail(details, "toe_shape", "toe_width")
        heel = _first_detail(details, "heel_type", "heel_height_appearance")
        closure = _first_detail(details, "closure_type")
        finish = _first_detail(details, "surface_finish") or _first_detail(material_details, "finish")
        silhouette = _first_detail(_get(global_details, "construction"), "silhouette", "shape")
        sentences.append(f"{colour} {label.lower()} with a {toe or 'defined'} toe and {heel or 'visible'} heel.")
        if material or finish: sentences.append(f"The upper appears to be {material or 'the observed material'} with a {finish or 'visible'} finish.")
        if closure: sentences.append(f"The design has {closure} construction.")
        if silhouette: sentences.append(f"The silhouette is {silhouette.lower()}.")
        if features: sentences.append(f"Visible details include {', '.join(features[:3])}.")
    elif category == "bottoms":
        waist = _first_detail(details, "waist_height", "waistband_type")
        fit = _first_detail(details, "fit_and_silhouette", "leg_shape")
        length = _first_detail(details, "garment_length")
        seams = _get(details, "panel_or_seam_details") or []
        seam_text = ", ".join(_text(item) for item in seams if _text(item)) if isinstance(seams, list) else _text(seams)
        sentences.append(f"{colour} {label.lower()} with {waist or 'the observed waistband'} and {fit or 'the observed fit'}.")
        if material and length: sentences.append(f"The garment appears to use {material} material and is {length}.")
        elif material: sentences.append(f"The garment appears to use {material} material.")
        elif length: sentences.append(f"The garment is {length}.")
        if seam_text: sentences.append(f"Visible construction includes {seam_text}.")
        if features: sentences.append(f"Other visible details include {', '.join(features[:3])}.")
    elif category == "tops":
        neckline = _first_detail(details, "neckline_type", "collar_type")
        sleeve = _first_detail(details, "sleeve_length", "sleeve_type")
        fit = _first_detail(details, "fit_and_silhouette")
        sentences.append(f"{colour} {label.lower()} with {neckline or 'the observed neckline'} and {sleeve or 'the observed sleeves'}.")
        if fit or material: sentences.append(f"It has {fit or 'the observed fit'} and appears to use {material or 'the observed material'}.")
        if features: sentences.append(f"Visible details include {', '.join(features[:3])}.")
    else:
        sentences.append(f"{colour} {label.lower()} with {material or 'the observed material'}.")
        if features: sentences.append(f"Visible details include {', '.join(features[:4])}.")

    sentence = " ".join(sentences)
    sentence = bound_description(sentence)
    return sentence[0].upper() + sentence[1:]
