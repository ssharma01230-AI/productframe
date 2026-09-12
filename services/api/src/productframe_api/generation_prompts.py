"""Compile authoritative product data and a template into a provider-neutral prompt."""
from dataclasses import dataclass
from typing import Literal

from .category_registry import get_bottoms_family_for_subtype, validate_category_details
from .generation_templates import GenerationTemplate, get_bottoms_family_policy, validate_generation_template


ReferenceRole = Literal["product_reference", "template_reference"]


class PromptCompilationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProductContext:
    name: str
    category: str
    product_type: str
    colours: str
    materials: str
    features: tuple[str, ...]
    description: str
    colour_details: dict[str, object] | None = None
    category_details: dict[str, object] | None = None
    global_details: dict[str, object] | None = None
    confidence_details: dict[str, object] | None = None
    presentation: Literal["male", "female", "unisex"] = "unisex"
    fidelity_constraints: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReferenceImage:
    role: ReferenceRole
    object_key: str
    asset_id: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    template_id: str
    channel: str
    product: ProductContext
    product_reference_images: tuple[ReferenceImage, ...]
    strict: bool = False


@dataclass(frozen=True, slots=True)
class GenerationPrompt:
    prompt: str
    negative_prompt: str
    reference_images: tuple[ReferenceImage, ...]
    aspect_ratio: str
    template_id: str
    template_version: int
    artwork_regions: tuple[dict[str, object], ...] = ()
    artwork_visibility: str = "reference_dependent"
    artwork_surface_mode: str = "flat"
    reference_rotation_degrees: int = 0


def _as_dict(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    return None


def _format_details(value: object, *, indent: int = 0) -> list[str]:
    details = _as_dict(value)
    if details is None:
        return ["- Not provided"]
    lines: list[str] = []
    prefix = " " * indent
    for key, item in details.items():
        label = key.replace("_", " ").capitalize()
        if isinstance(item, dict) or hasattr(item, "model_dump"):
            lines.append(f"{prefix}{label}:")
            lines.extend(_format_details(item, indent=indent + 2))
        elif isinstance(item, list):
            if item:
                lines.append(f"{prefix}{label}:")
                lines.extend(f"{prefix}  - {entry}" for entry in item)
            else:
                lines.append(f"{prefix}{label}: None visible")
        else:
            lines.append(f"{prefix}{label}: {item}")
    return lines


def _format_confidence(value: object) -> list[str]:
    details = _as_dict(value)
    if not details:
        return ["- No section confidence data was provided."]
    lines: list[str] = []
    for section, assessment in details.items():
        if not isinstance(assessment, dict):
            continue
        score = assessment.get("score")
        status = assessment.get("status", "unknown")
        lines.append(f"- {section.replace('_', ' ').capitalize()}: score={score}, status={status}")
        for uncertainty in assessment.get("uncertainties", []) or []:
            lines.append(f"  - Uncertainty: {uncertainty}")
    return lines or ["- No section confidence data was provided."]


def _path_exists(product: ProductContext, path: str) -> bool:
    if path == "product_type":
        return bool(product.product_type.strip())
    if path == "colour_details":
        return bool(product.colour_details)
    if path == "global_details":
        return bool(product.global_details)
    if path.startswith("category_details"):
        details = _as_dict(product.category_details)
        if not details:
            return False
        current: object = details
        for part in path.split(".")[1:]:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        return current not in (None, "", [])
    if path.startswith("global_details."):
        details = _as_dict(product.global_details)
        if not details:
            return False
        current: object = details
        for part in path.split(".")[1:]:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        return current not in (None, "", [])
    return True


def compile_generation_prompt(request: GenerationRequest) -> GenerationPrompt:
    """Compile a deterministic prompt with product identity taking priority."""
    product = request.product
    category_details = _as_dict(product.category_details) or {}
    subtype = category_details.get("subtype")
    product_family = category_details.get("family") or (get_bottoms_family_for_subtype(str(subtype)) if product.category == "bottoms" and subtype else None)
    template = validate_generation_template(
        request.template_id,
        category=product.category,
        channel=request.channel,
        subtype=str(subtype) if subtype else None,
        product_family=str(product_family) if product_family else None,
    )
    if not request.product_reference_images:
        raise PromptCompilationError("At least one product reference image is required")
    if any(image.role != "product_reference" for image in request.product_reference_images):
        raise PromptCompilationError("Generation requests may only contain product reference images")
    if request.strict:
        missing = [field for field in template.required_product_fields if not _path_exists(product, field)]
        if missing:
            raise PromptCompilationError("Missing required product fields: " + ", ".join(missing))

    features = "\n".join(f"- {feature}" for feature in product.features) or "- None recorded"
    global_lines = _format_details(product.global_details)
    colour_lines = _format_details(product.colour_details)
    category_lines = _format_details(product.category_details)
    confidence_lines = _format_confidence(product.confidence_details)
    prompt_rules = "\n".join(f"- {rule}" for rule in template.prompt_format_rules) or "- Follow the product identity priority rules."
    category_fidelity_rules = list(product.fidelity_constraints)
    branding = (_as_dict(product.global_details) or {}).get("branding", {})
    branding = branding if isinstance(branding, dict) else {}
    artwork_regions = tuple(region for region in branding.get("artwork_regions", []) if isinstance(region, dict))
    reference_rotation_degrees = int((_as_dict(product.global_details) or {}).get("source_rotation_degrees", 0) or 0)
    if product.category == "tops":
        category_fidelity_rules.extend([
            "Preserve observed colour treatment such as washing, fading, tonal variation, sheen, wear and natural wrinkles; do not clean or standardise the surface.",
            "Preserve the observed silhouette, body width, garment length, shoulder construction and sleeve width; do not regularise them into a generic top.",
            "Treat every visible print, illustration, logo, embroidery and appliqué as immutable product identity, not as a semantic suggestion.",
            "Copy the artwork exactly from the reference pixels: preserve its component count, geometry, topology, orientation, linework, internal details, colour boundaries, text, scale, placement, spacing, edge quality, fading and distress.",
            "Do not reinterpret, simplify, beautify, complete, replace or redraw artwork from its subject description. For example, identifying an animal or object does not permit drawing a different instance of it.",
            "Preserve visible seams, panels, hems, neck binding and construction irregularities even when they reduce symmetry.",
            "If a property is not observable, leave it uncertain rather than inventing a conventional ecommerce replacement.",
        ])
    fidelity_rules = "\n".join(f"- {rule}" for rule in category_fidelity_rules) or "- Preserve all observed product-specific details."
    family_policy = get_bottoms_family_policy(str(product_family) if product.category == "bottoms" and product_family else None) if product.category == "bottoms" else None
    family_policy_section = f"\nBOTTOMS FAMILY RENDERING POLICY\n- {family_policy}\n" if family_policy else ""

    prompt = f"""Create an ecommerce image using the supplied product reference image as the primary visual authority.

REFERENCE-FIRST RULES
- Inspect the product reference image before interpreting the text description.
- Reproduce every clearly visible construction detail directly from the reference image.
- Never replace a visible product feature with a generic category default.
- The reference image overrides generic template conventions and inferred schema defaults.
- Uncertainty applies only to details that are genuinely hidden, obstructed, cropped or impossible to assess from the reference.
- Do not treat a detail as uncertain merely because its exact measurement is unavailable.

PRODUCT IDENTITY — AUTHORITATIVE
- Name: {product.name}
- Category: {product.category}
- Product type: {product.product_type}
- Colour summary: {product.colours}
- Materials summary: {product.materials}
- Visible features:
{features}
- Description: {product.description}

DETAILED COLOUR DATA
{chr(10).join(colour_lines)}

GLOBAL PRODUCT DATA
{chr(10).join(global_lines)}

CATEGORY-SPECIFIC DATA — AUTHORITATIVE FOR CATEGORY CONSTRUCTION
{chr(10).join(category_lines)}

CONFIDENCE AND UNCERTAINTY
{chr(10).join(confidence_lines)}

PRODUCT FIDELITY PRESERVATION
{fidelity_rules}
{family_policy_section}
MODEL AND MANNEQUIN PRESENTATION
- For any visible model-worn composition, use a {product.presentation} model presentation. Preserve the garment identity and do not introduce body features that conflict with the requested presentation.
- For any visible, headless, or invisible mannequin composition, use a mannequin with a {product.presentation} gender presentation. The selected user presentation overrides any default or template wording; never substitute a male or female model/mannequin when the user selected the other gender. Product-only flat-lay and detail compositions must not add a person or mannequin.

TEMPLATE PRESENTATION
{template.prompt_instructions}

PROMPT FORMAT RULES
{prompt_rules}

IDENTITY PROTECTION
The product data and product reference images are the only source of truth for
product identity. Preserve the product's colour, material appearance, texture,
shape, proportions, construction and category-specific details. Do not allow the
template presentation to change the product. Treat uncertain attributes as
uncertain and do not invent replacements. Use the template only for composition,
framing, lighting and presentation."""

    return GenerationPrompt(
        prompt=prompt.strip(),
        negative_prompt=template.negative_prompt,
        reference_images=request.product_reference_images,
        aspect_ratio=template.aspect_ratio,
        template_id=template.id,
        template_version=template.version,
        artwork_regions=artwork_regions,
        artwork_visibility=template.artwork_visibility,
        artwork_surface_mode=template.artwork_surface_mode,
        reference_rotation_degrees=reference_rotation_degrees,
    )


def build_generation_prompt(request: GenerationRequest, *, template: GenerationTemplate | None = None) -> GenerationPrompt:
    """Backward-compatible entry point for the generation graph."""
    if template is not None and template.id != request.template_id:
        raise PromptCompilationError("The supplied template does not match the request")
    return compile_generation_prompt(request)
