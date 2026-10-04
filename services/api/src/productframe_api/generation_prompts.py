"""Compile authoritative product data and a template into a provider-neutral prompt."""
from dataclasses import dataclass
from typing import Literal

from .category_registry import get_accessories_family_for_subtype, get_bottoms_family_for_subtype, get_outerwear_family_for_subtype, get_tailoring_family_for_subtype, validate_category_details
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
    template_reference_images: tuple[ReferenceImage, ...] = ()
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


def _format_public_details(value: object, *, indent: int = 0) -> list[str]:
    """Format recognised product facts while withholding analysis-only metadata."""
    details = _as_dict(value)
    if details is None:
        return ["- Not provided"]
    hidden = {"confidence", "confidence_details", "source_rotation_degrees", "analysis", "evidence"}
    lines: list[str] = []
    prefix = " " * indent
    for key, item in details.items():
        if key in hidden:
            continue
        label = key.replace("_", " ").capitalize()
        if isinstance(item, dict) or hasattr(item, "model_dump"):
            lines.append(f"{prefix}{label}:")
            lines.extend(_format_public_details(item, indent=indent + 2))
        elif isinstance(item, list):
            if item:
                lines.append(f"{prefix}{label}:")
                lines.extend(f"{prefix}  - {entry}" for entry in item)
        elif item not in (None, ""):
            lines.append(f"{prefix}{label}: {item}")
    return lines or [f"{prefix}- Not provided"]


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


def _secondary_styling_profile(product: ProductContext) -> str:
    """Return a deterministic, restrained profile shared by model outputs."""
    colours = str(product.colours or "").lower()
    patterned = any(token in colours for token in ("pattern", "print", "striped", "checked", "floral", "multicolour", "multi-colour"))
    light = any(token in colours for token in ("white", "cream", "ivory", "pale", "light", "beige"))
    dark = any(token in colours for token in ("black", "navy", "charcoal", "dark"))
    if patterned or (not light and not dark and not colours.strip()):
        return "Secondary styling profile: restrained mid-neutral top and lower garment (stone, taupe or charcoal, selected once for this run) with minimal neutral footwear; no competing saturated colour."
    if light:
        return "Secondary styling profile: a compatible light, mid-neutral or dark secondary palette selected for contrast and harmony with the light product; a medium-light grey lower garment may be used where compatible; do not default to white."
    if dark:
        return "Secondary styling profile: a compatible light, mid-neutral or dark secondary palette selected for contrast and harmony with the dark product; do not default to white."
    return "Secondary styling profile: conservative taupe, stone or charcoal neutrals selected deterministically for this product; colour is uncertain, so do not introduce saturation."


def _compile_tie_prompt(
    request: GenerationRequest,
    template: GenerationTemplate,
    *,
    artwork_regions: tuple[dict[str, object], ...],
    reference_rotation_degrees: int,
) -> GenerationPrompt:
    """Compile the compact, reference-authoritative tie prompt format."""
    product = request.product
    colour = _as_dict(product.colour_details) or {}
    global_details = _as_dict(product.global_details) or {}
    materials = global_details.get("materials") if isinstance(global_details.get("materials"), dict) else {}
    construction = global_details.get("construction") if isinstance(global_details.get("construction"), dict) else {}
    branding = global_details.get("branding") if isinstance(global_details.get("branding"), dict) else {}
    gender = global_details.get("gender") if isinstance(global_details.get("gender"), dict) else {}
    category = _as_dict(product.category_details) or {}
    secondary = ", ".join(str(value) for value in (colour.get("secondary_colours") or [])) or "none recorded"
    construction_details = "; ".join(str(value) for value in (construction.get("construction_details") or [])) or "none recorded"
    functional_details = "; ".join(str(value) for value in (construction.get("functional_details") or [])) or "none visible"
    branding_items = ", ".join(str(value) for value in (category.get("visible_branding") or branding.get("logos") or [])) or "not visible"
    uncertainties = ", ".join(str(value) for value in (category.get("visible_uncertainties") or construction.get("visible_uncertainties") or [])) or "none recorded"
    product_facts = f"""PRODUCT FACTS

Identity:
- Category: {product.category}
- Family: {category.get('family') or 'ties'}
- Subtype: {category.get('subtype') or product.product_type}
- Product type: {product.product_type}
- Visual signature: {product.description}

Colour:
- Primary colour: {colour.get('primary_colour') or product.colours}
- Secondary colours: {secondary}
- Pattern: {colour.get('pattern') or 'not clearly visible'}
- Distribution: {colour.get('colour_distribution') or 'not clearly visible'}
- Finish: {colour.get('colour_finish') or 'not clearly visible'}
- Tonal variation: {colour.get('tonal_variation') or 'not clearly visible'}

Material:
- Appearance: {materials.get('appearance') or product.materials}
- Texture: {materials.get('texture') or 'not clearly visible'}
- Weight and thickness: {materials.get('weight') or 'not clearly visible'}; {materials.get('thickness') or 'not clearly visible'}
- Finish: {materials.get('finish') or 'not clearly visible'}
- Stretch or flexibility: {materials.get('stretch_or_flexibility') or 'not clearly visible'}
- Drape: {materials.get('drape_or_rigidity') or 'not clearly visible'}

Construction:
- Silhouette: {construction.get('silhouette') or category.get('shape') or 'not clearly visible'}
- Shape: {construction.get('shape') or category.get('shape') or 'not clearly visible'}
- Proportions: {construction.get('proportions') or category.get('length_and_width') or 'not clearly visible'}
- Visible construction: {construction_details}
- Functional details: {functional_details}
- Category details: {category.get('shape') or 'not clearly visible'}; {category.get('length_and_width') or 'not clearly visible'}; {category.get('edge_finish') or 'not visible'}

Artwork and branding:
- Pattern/artwork: {category.get('pattern_or_print') or colour.get('pattern') or 'not clearly visible'}
- Branding: {branding_items}
- Gender presentation: {gender.get('user_confirmed') or gender.get('assumed') or product.presentation}

Evidence and uncertainty:
- Supported source view: use only the supplied product reference images
- Unknown details: {uncertainties}
"""
    template_reference_section = """
IMAGE ROLES

- TEMPLATE REFERENCE controls composition, camera, crop, framing, lighting, background, and presentation structure.
- PRODUCT REFERENCE controls the uploaded tie’s identity, colour, pattern, material, proportions, construction, and branding.
- The template reference must not influence the uploaded tie’s identity or pattern.
""" if request.template_reference_images else """
IMAGE ROLES

- PRODUCT REFERENCE controls the uploaded tie’s identity, colour, pattern, material, proportions, construction, and branding.
- No template reference was supplied; do not invent one.
"""
    presentation = template.prompt_instructions.removeprefix("Create the requested ecommerce presentation of the uploaded tie. ").strip()
    output_details = template.output_details.strip()
    prompt = f"""TASK

Create one square 1:1 ecommerce image by performing a precise image edit.
{template_reference_section}
PRODUCT AUTHORITY

The uploaded product reference is the sole authority for the tie’s identity.
Preserve every clearly visible product feature on its original surface.
If the template and product references conflict, the uploaded product reference controls product identity.

{product_facts.strip()}

PRODUCT FIDELITY

Copy the uploaded tie’s visible pattern literally as a textile pattern.
Preserve motif geometry, scale, density, spacing, colour, orientation, weave,
sheen, edges, proportions, and continuity across visible surfaces.
Do not interpret the pattern semantically or replace it with a category default.

PRESENTATION

{presentation}

COMPOSITION LOCK

{output_details}

Match the template reference exactly.
Use the template reference only for composition and presentation structure.
Preserve its camera angle, crop, framing, lighting, background, surrounding clothing,
and product position while replacing only the template product with the uploaded tie.

REPLACEMENT TASK

Replace the template tie or tie arrangement with the uploaded tie.
Preserve the uploaded tie’s authentic colour, pattern, motif scale, density,
material, proportions, blade and tail widths, tip shape, edges, and visible construction.

UNCERTAINTY POLICY

Details hidden by the knot, fold, roll, crop, or surrounding clothing remain unknown.
Do not invent them.

STRICT EXCLUSIONS

Do not add unsupported products, duplicate ties, unrelated accessories, props,
text, labels, watermarks, collages, insets, split screens, or multiple views."""
    negative = " ".join((
        template.negative_prompt,
        "Match the template reference exactly for composition; do not alter its crop, camera, framing, lighting, background, or surrounding presentation.",
        "Do not copy the template tie’s identity, colour, pattern, material, texture, construction, proportions, or branding.",
        "Do not reinterpret, enlarge, simplify, sparsify, stylise, recolour, or redesign the uploaded tie.",
        "Do not invent details hidden by the knot, fold, roll, crop, or surrounding clothing.",
    ))
    return GenerationPrompt(
        prompt=prompt.strip(),
        negative_prompt=negative.strip(),
        reference_images=request.product_reference_images + request.template_reference_images,
        aspect_ratio=template.aspect_ratio,
        template_id=template.id,
        template_version=template.version,
        artwork_regions=artwork_regions,
        artwork_visibility=template.artwork_visibility,
        artwork_surface_mode=template.artwork_surface_mode,
        reference_rotation_degrees=reference_rotation_degrees,
    )


def _compile_belt_prompt(
    request: GenerationRequest,
    template: GenerationTemplate,
    *,
    artwork_regions: tuple[dict[str, object], ...],
    reference_rotation_degrees: int,
) -> GenerationPrompt:
    """Compile the reference-authoritative belt prompt format."""
    product = request.product
    colour = _as_dict(product.colour_details) or {}
    global_details = _as_dict(product.global_details) or {}
    materials = global_details.get("materials") if isinstance(global_details.get("materials"), dict) else {}
    construction = global_details.get("construction") if isinstance(global_details.get("construction"), dict) else {}
    category = _as_dict(product.category_details) or {}
    branding = global_details.get("branding") if isinstance(global_details.get("branding"), dict) else {}
    uncertainties = category.get("visible_uncertainties") or construction.get("visible_uncertainties") or []
    facts = f"""PRODUCT FACTS

Identity:
- Category: {product.category}
- Family: {category.get('family') or 'belts'}
- Subtype: {category.get('subtype') or product.product_type}
- Product type: {product.product_type}
- Visual signature: {product.description}

Colour:
- Primary colour: {colour.get('primary_colour') or product.colours}
- Secondary colours: {', '.join(str(value) for value in (colour.get('secondary_colours') or [])) or 'none recorded'}
- Pattern or finish: {colour.get('pattern') or colour.get('colour_finish') or 'not clearly visible'}
- Distribution: {colour.get('colour_distribution') or 'not clearly visible'}
- Tonal variation: {colour.get('tonal_variation') or 'not clearly visible'}

Material:
- Appearance: {materials.get('appearance') or product.materials}
- Texture and grain: {materials.get('texture') or 'not clearly visible'}
- Weight and thickness: {materials.get('weight') or 'not clearly visible'}; {materials.get('thickness') or 'not clearly visible'}
- Finish: {materials.get('finish') or 'not clearly visible'}
- Drape or rigidity: {materials.get('drape_or_rigidity') or 'not clearly visible'}

Construction:
- Belt type: {category.get('belt_type') or 'not clearly visible'}
- Strap width and length appearance: {category.get('strap_width') or 'not clearly visible'}; {category.get('strap_length_appearance') or 'not clearly visible'}
- Strap shape and closure: {category.get('strap_shape') or 'not clearly visible'}; {category.get('closure_type') or 'not clearly visible'}
- Buckle type: {category.get('buckle_type') or 'not clearly visible'}
- Buckle shape and material: {category.get('buckle_shape') or 'not clearly visible'}; {category.get('buckle_material_appearance') or 'not clearly visible'}
- Prong and hardware: {', '.join(str(value) for value in (category.get('hardware_details') or [])) or 'not clearly visible'}
- Keepers: {category.get('belt_loop_details') or 'not clearly visible'}
- Holes and tip: {category.get('hole_details') or category.get('tip_details') or 'not clearly visible'}
- Visible construction: {'; '.join(str(value) for value in (construction.get('construction_details') or [])) or 'none recorded'}
- Stitching and branding: {', '.join(str(value) for value in (category.get('branding_or_graphics') or branding.get('logos') or [])) or 'not visible'}

Evidence and uncertainty:
- Supported source view: use only the supplied product reference images
- Unknown details: {', '.join(str(value) for value in uncertainties) or 'none recorded'}
"""
    roles = """IMAGE ROLES

- TEMPLATE REFERENCE controls composition, camera, crop, framing, lighting, background, surrounding clothing, and belt position.
- PRODUCT REFERENCE controls the uploaded belt’s identity, colour, material, grain, hardware, proportions, holes, tip, stitching, and branding.
- The template reference must not influence the uploaded belt’s identity or construction.
""" if request.template_reference_images else """IMAGE ROLES

- PRODUCT REFERENCE controls the uploaded belt’s identity and all visible product details.
- No template reference was supplied; do not invent one.
"""
    presentation = template.prompt_instructions.removeprefix("Create the requested ecommerce presentation of the uploaded belt. ").strip()
    prompt = f"""TASK

Create one ecommerce image by performing a precise image edit.

{roles}
PRODUCT AUTHORITY

The uploaded product reference is the sole authority for belt identity.
If the template and product references conflict, the uploaded product reference controls product identity.

{facts.strip()}

BELT FIDELITY

Preserve the uploaded belt’s exact type, strap width and length, material,
colour, grain, edge finish, buckle frame, prong, hardware finish, keeper count,
hole count and spacing, tip shape, stitching, branding, wear, sheen, and tonal variation.
Do not normalise the belt into a generic benchmark product.

PRESENTATION

{presentation}

COMPOSITION LOCK

{template.output_details.strip()}

Match the template reference exactly.
Use the template reference only for composition and presentation structure.
Preserve its camera angle, crop, framing, lighting, background, surrounding clothing,
and belt position while replacing only the template belt with the uploaded product.

REPLACEMENT TASK

Replace the template belt or belt arrangement with the uploaded belt.
Keep the uploaded belt’s authentic product identity unchanged in every visible area.

UNCERTAINTY POLICY

Details hidden by folds, coils, crops, clothing, or the buckle remain unknown.
Do not invent them.

STRICT EXCLUSIONS

Do not add duplicate belts, unrelated accessories, props, text, labels,
watermarks, collages, insets, split screens, or multiple views."""
    negative = " ".join((
        template.negative_prompt,
        "Match the template reference exactly for composition; do not alter its crop, camera, framing, lighting, background, surrounding clothing, or belt position.",
        "Do not copy the template belt’s identity, colour, material, grain, hardware, holes, tip, stitching, or proportions.",
        "Do not invent hidden belt construction or add unsupported clothing, body parts, props, or accessories.",
    ))
    return GenerationPrompt(
        prompt=prompt.strip(), negative_prompt=negative.strip(),
        reference_images=request.product_reference_images + request.template_reference_images,
        aspect_ratio=template.aspect_ratio, template_id=template.id, template_version=template.version,
        artwork_regions=artwork_regions, artwork_visibility=template.artwork_visibility,
        artwork_surface_mode=template.artwork_surface_mode, reference_rotation_degrees=reference_rotation_degrees,
    )


def _compile_glove_prompt(
    request: GenerationRequest,
    template: GenerationTemplate,
    *,
    artwork_regions: tuple[dict[str, object], ...],
    reference_rotation_degrees: int,
) -> GenerationPrompt:
    """Compile the reference-authoritative glove prompt without uncertainty prose."""
    product = request.product
    colour = _as_dict(product.colour_details) or {}
    global_details = _as_dict(product.global_details) or {}
    materials = global_details.get("materials") if isinstance(global_details.get("materials"), dict) else {}
    category = _as_dict(product.category_details) or {}
    facts = f"""PRODUCT FACTS

Identity:
- Category: {product.category}
- Family: {category.get('family') or 'gloves'}
- Subtype: {category.get('subtype') or product.product_type}
- Product type: {product.product_type}
- Pair or count: {category.get('pair_or_count') or 'pair unless product evidence shows otherwise'}

Appearance:
- Primary colour: {colour.get('primary_colour') or product.colours}
- Secondary colours: {', '.join(str(value) for value in (colour.get('secondary_colours') or [])) or 'none recorded'}
- Material: {category.get('material_appearance') or materials.get('appearance') or product.materials}
- Texture and finish: {materials.get('texture') or 'not clearly visible'}; {materials.get('finish') or 'not clearly visible'}

Construction:
- Glove type: {category.get('glove_type') or 'not clearly visible'}
- Finger configuration: {category.get('finger_configuration') or 'not clearly visible'}
- Finger length: {category.get('finger_length') or 'not clearly visible'}
- Cuff length and details: {category.get('cuff_length') or 'not clearly visible'}; {category.get('cuff_details') or 'not clearly visible'}
- Closure details: {', '.join(str(value) for value in (category.get('closure_details') or [])) or 'none visible'}
- Palm details: {', '.join(str(value) for value in (category.get('palm_details') or [])) or 'none visible'}
- Grip features: {', '.join(str(value) for value in (category.get('grip_features') or [])) or 'none visible'}
- Seams and stitching: {', '.join(str(value) for value in (category.get('seam_details') or [])) or 'not clearly visible'}
- Lining or insulation: {category.get('lining_or_insulation') or 'not clearly visible'}
"""
    roles = """IMAGE ROLES

- TEMPLATE REFERENCE controls composition, pose, crop, camera, framing, lighting, background and clothing or hand context.
- PRODUCT REFERENCE controls the uploaded gloves' identity, pair count, colour, material, texture, finger construction, cuffs, seams and visible details.
- The template reference must not influence glove identity or construction.
""" if request.template_reference_images else """IMAGE ROLES

- PRODUCT REFERENCE controls the uploaded gloves' identity and all visible product details.
- No template reference was supplied; do not invent one.
"""
    presentation = template.prompt_instructions.removeprefix("Create the requested ecommerce presentation of the uploaded gloves. ").strip()
    prompt = f"""TASK

Create one ecommerce image by performing a precise image edit.

{roles}
PRODUCT AUTHORITY

The uploaded product reference is the sole authority for glove identity and construction.
If the template and product references conflict, the uploaded product reference controls product identity.

{facts.strip()}

GLOVE FIDELITY

Preserve the uploaded gloves' exact pair count, hand orientation, finger configuration, thumb construction,
material, colour, grain, texture, stitching, seams, cuff shape, cuff trim, lining and visible construction.
Do not normalise the gloves into a generic product or transfer template glove details.

PRESENTATION

{presentation}

COMPOSITION LOCK

{template.output_details.strip()}

Match the template reference exactly.
Use the template reference only for composition and presentation structure.

REPLACEMENT TASK

Replace the template gloves with the uploaded gloves while preserving the uploaded product identity.

STRICT EXCLUSIONS

Do not add unsupported hands, arms, faces, bodies, clothing, props, duplicate gloves, extra fingers,
extra cuffs, text, labels, watermarks, collages, insets or split views."""
    negative = " ".join((template.negative_prompt, "Do not copy the template gloves' identity, colour, material or construction."))
    return GenerationPrompt(
        prompt=prompt.strip(), negative_prompt=negative.strip(),
        reference_images=request.product_reference_images + request.template_reference_images,
        aspect_ratio=template.aspect_ratio, template_id=template.id, template_version=template.version,
        artwork_regions=artwork_regions, artwork_visibility=template.artwork_visibility,
        artwork_surface_mode=template.artwork_surface_mode, reference_rotation_degrees=reference_rotation_degrees,
    )


def _compile_scarf_prompt(request: GenerationRequest, template: GenerationTemplate, *, artwork_regions: tuple[dict[str, object], ...], reference_rotation_degrees: int) -> GenerationPrompt:
    product = request.product
    colour = _as_dict(product.colour_details) or {}
    category = _as_dict(product.category_details) or {}
    global_details = _as_dict(product.global_details) or {}
    materials = global_details.get("materials") if isinstance(global_details.get("materials"), dict) else {}
    facts = f"""PRODUCT FACTS

Identity:
- Category: {product.category}
- Family: {category.get('family') or 'scarves'}
- Subtype: {category.get('subtype') or product.product_type}
- Product type: {product.product_type}

Appearance and construction:
- Primary colour: {colour.get('primary_colour') or product.colours}
- Secondary colours: {', '.join(str(v) for v in (colour.get('secondary_colours') or [])) or 'none recorded'}
- Material: {category.get('fabric_appearance') or materials.get('appearance') or product.materials}
- Texture and finish: {materials.get('texture') or 'not clearly visible'}; {materials.get('finish') or 'not clearly visible'}
- Shape: {category.get('scarf_shape') or 'not clearly visible'}
- Length and width: {category.get('scarf_length') or 'not clearly visible'}; {category.get('scarf_width') or 'not clearly visible'}
- Thickness and drape: {category.get('thickness') or 'not clearly visible'}; {category.get('drape') or 'not clearly visible'}
- Pattern and print: {category.get('pattern') or 'not clearly visible'}; {category.get('print') or 'none visible'}
- Edge and fringe: {category.get('edge_finish') or 'not clearly visible'}; {category.get('fringe_details') or 'not clearly visible'}
- Fastening or wear details: {', '.join(str(v) for v in (category.get('fastening_or_wear_details') or [])) or 'none visible'}
"""
    roles = """IMAGE ROLES

- TEMPLATE REFERENCE controls composition, pose, crop, camera, framing, lighting, background and model or clothing context.
- PRODUCT REFERENCE controls the uploaded scarf's identity, colour, material, pattern, shape, dimensions, edges, fringe and drape.
- The template reference must not influence scarf identity or construction.
""" if request.template_reference_images else """IMAGE ROLES

- PRODUCT REFERENCE controls the uploaded scarf's identity and visible product details.
- No template reference was supplied; do not invent one.
"""
    presentation = template.prompt_instructions.removeprefix("Create the requested ecommerce presentation of the uploaded scarf. ").strip()
    prompt = f"""TASK

Create one ecommerce image by performing a precise image edit.

{roles}
PRODUCT AUTHORITY

The uploaded product reference is the sole authority for scarf identity and construction.

{facts.strip()}

SCARF FIDELITY

Preserve the uploaded scarf's exact colour, weave, pattern scale, shape, length, width, thickness,
edge finish, fringe, folds and drape. Do not transfer template scarf details.

PRESENTATION

{presentation}

COMPOSITION LOCK

{template.output_details.strip()}

Match the template reference exactly.
Use the template reference only for composition and presentation structure.

REPLACEMENT TASK

Replace the template scarf with the uploaded scarf while preserving its product identity.

STRICT EXCLUSIONS

Do not add duplicate scarves, unsupported folds, altered fringe, unrelated accessories, text, watermark,
collage, inset or split view."""
    negative = " ".join((template.negative_prompt, "Do not copy the template scarf's identity, colour, pattern or construction."))
    return GenerationPrompt(prompt=prompt.strip(), negative_prompt=negative.strip(), reference_images=request.product_reference_images + request.template_reference_images, aspect_ratio=template.aspect_ratio, template_id=template.id, template_version=template.version, artwork_regions=artwork_regions, artwork_visibility=template.artwork_visibility, artwork_surface_mode=template.artwork_surface_mode, reference_rotation_degrees=reference_rotation_degrees)


def compile_generation_prompt(request: GenerationRequest) -> GenerationPrompt:
    """Compile a deterministic prompt with product identity taking priority."""
    product = request.product
    category_details = _as_dict(product.category_details) or {}
    subtype = category_details.get("subtype")
    persisted_family = category_details.get("family")
    if isinstance(persisted_family, str) and persisted_family.strip().lower() in {"", "unclassified", "unknown", "none", "null"}:
        persisted_family = None
    product_family = persisted_family or (
        "belts" if product.category in {"belt", "belts"} else
        get_accessories_family_for_subtype(str(subtype)) if product.category in {"accessories", "glove", "gloves"} and subtype else
        get_bottoms_family_for_subtype(str(subtype)) if product.category == "bottoms" and subtype else
        get_outerwear_family_for_subtype(str(subtype)) if product.category == "outerwear" and subtype else
        get_tailoring_family_for_subtype(str(subtype)) if product.category == "tailoring" and subtype else
        None
    )
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
        raise PromptCompilationError("Product references must use the product_reference role")
    if any(image.role != "template_reference" for image in request.template_reference_images):
        raise PromptCompilationError("Template references must use the template_reference role")
    if request.strict:
        missing = [field for field in template.required_product_fields if not _path_exists(product, field)]
        if missing:
            raise PromptCompilationError("Missing required product fields: " + ", ".join(missing))

    features = "\n".join(f"- {feature}" for feature in product.features) or "- None recorded"
    global_lines = _format_public_details(product.global_details)
    colour_lines = _format_public_details(product.colour_details)
    category_lines = _format_public_details(product.category_details)
    prompt_rules = "\n".join(f"- {rule}" for rule in template.prompt_format_rules) or "- Follow the product identity priority rules."
    category_fidelity_rules = list(product.fidelity_constraints)
    branding = (_as_dict(product.global_details) or {}).get("branding", {})
    branding = branding if isinstance(branding, dict) else {}
    artwork_regions = tuple(region for region in branding.get("artwork_regions", []) if isinstance(region, dict))
    reference_rotation_degrees = int((_as_dict(product.global_details) or {}).get("source_rotation_degrees", 0) or 0)
    if product.category in {"accessories", "neckwear"} and product_family in {"ties", "ties-neckwear"}:
        return _compile_tie_prompt(
            request,
            template,
            artwork_regions=artwork_regions,
            reference_rotation_degrees=reference_rotation_degrees,
        )
    if product.category == "accessories" and product_family == "belts":
        return _compile_belt_prompt(
            request,
            template,
            artwork_regions=artwork_regions,
            reference_rotation_degrees=reference_rotation_degrees,
        )
    if product.category in {"accessories", "glove", "gloves"} and product_family == "gloves":
        return _compile_glove_prompt(
            request,
            template,
            artwork_regions=artwork_regions,
            reference_rotation_degrees=reference_rotation_degrees,
        )
    if product.category in {"accessories", "scarf", "scarves"} and product_family == "scarves":
        return _compile_scarf_prompt(request, template, artwork_regions=artwork_regions, reference_rotation_degrees=reference_rotation_degrees)
    category_fidelity_rules.extend([
        "Preserve fine material evidence such as knit/weave scale, yarn loops, ribbing, nap, grain, stitch density, surface irregularity, sheen and natural wear; do not replace it with generic AI-generated texture.",
        "Every clearly visible construction detail in the product reference is mandatory, including neckline stitching, rib edges, seam lines, hems, closures and stitch lines; do not omit or simplify it.",
    ])
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
    elif product.category == "dresses":
        category_fidelity_rules.extend([
            "Preserve the observed dress silhouette, length, neckline, sleeves or straps, waist placement, seams, closures, drape and hem; do not regularise the garment into a generic dress.",
            "Preserve visible pattern, artwork, embroidery, lace, trim, hardware and surface texture exactly; do not transfer details from a template reference.",
            "If the rear, underside, lining or closure is not visible in the product references, leave it uncertain rather than inventing conventional dress construction.",
        ])
    elif product.category == "footwear" and product_family in {"shoes", "trainers", "flats-loafers", "sandals-open-shoes"}:
        category_fidelity_rules.append(
            "Preserve the uploaded footwear's actual toe shape, vamp/opening, heel height, arch, sole thickness, upper material, colour, patina, stitching, ornaments, hardware and branding. Do not add tassels, apron stitching, a raised heel or any other benchmark-specific feature unless visible in the product references."
        )
    elif product.category == "footwear" and product_family == "heels":
        category_fidelity_rules.append(
            "Preserve the uploaded heel's actual heel type, height and geometry, pitch, toe shape, opening, upper coverage, straps, fastening, platform, arch, sole, lining, finish, seams, hardware and branding. Do not infer numeric heel height or transfer a pointed closed pump, red lacquer, tan lining or heel tip from the benchmark unless visible in the product references."
        )
    elif product.category == "tailoring" and product_family == "waistcoats":
        category_fidelity_rules.extend([
            "Preserve the waistcoat as a sleeveless tailored waist garment. Do not add sleeves, jacket lapels, a jacket hem, outerwear padding or a coordinated jacket.",
            "Preserve the uploaded neckline, front points, closure count and placement, welt or flap pockets, darts, seams, armholes, lining edges, back construction and adjuster only where evidenced.",
            "Matching trousers and a neutral shirt may appear only as secondary model styling; they must not imply that an uploaded standalone waistcoat is a verified full suit.",
        ])
    fidelity_rules = "\n".join(f"- {rule}" for rule in category_fidelity_rules) or "- Preserve all observed product-specific details."
    styling_profile = _secondary_styling_profile(product)
    family_policy = get_bottoms_family_policy(str(product_family) if product.category == "bottoms" and product_family else None) if product.category == "bottoms" else None
    family_policy_section = f"\nBOTTOMS FAMILY RENDERING POLICY\n- {family_policy}\n" if family_policy else ""
    mode_rules = {
        "model": f"- Use one adult model with the requested gender presentation. Follow the specified pose and framing, keep styling restrained, and do not obscure the product. Do not use a mannequin. The face, facial features, eyes, nose, mouth, hair and top of the head must not be visible; crop at or below the base of the neck as required by the template. {styling_profile} Keep this exact secondary styling profile consistent across every model-worn output in the generation run.",
        "mannequin": "- Use a visible headless mannequin with the requested gender presentation. The torso and relevant support may remain visible, but the head and face must not be shown. Do not use an invisible mannequin or human model.",
        "invisible_mannequin": "- Use a completely invisible mannequin form with the requested gender presentation. No torso, neck, head, body or support may be visible. Do not use a visible headless mannequin or human model.",
        "garment": "- Show only the garment. Do not use a human model or mannequin. Follow the specified folded, flat-lay, hanging, draped or surface-supported presentation.",
    }
    mode_negative_rules = {
        "model": "Do not show a mannequin, mannequin support, extra person, face or body features that obscure the product.",
        "mannequin": "Do not show a human model, mannequin head or face, or an invisible mannequin; the headless mannequin torso may remain visible.",
        "invisible_mannequin": "Do not show a human model, visible mannequin, headless mannequin torso, neck, body or support.",
        "garment": "Do not show a human model, mannequin, body, hanger or visible support.",
    }
    compiled_negative_prompt = template.negative_prompt
    template_reference_section = ""
    if request.template_reference_images:
        template_reference_section = """\nTEMPLATE REFERENCE\n- Use the supplied template reference image as a locked composition and presentation reference only.\n- Preserve its camera angle, framing, pose, product position, scale, lighting, background and presentation structure.\n- Replace the template garment completely with the product shown in the product reference images.\n- Do not copy the template garment's colour, material, texture, construction, artwork, branding, buttons, pockets, seams or proportions.\n- Treat secondary clothing and footwear in the template as composition references only: preserve their category, placement and visual scale, but adapt their colours and materials to the shared neutral styling profile.\n- Do not let secondary styling compete with, recolour or determine the uploaded product.\n"""
    if template.presentation_mode and template.output_details:
        presentation_negative_prompt = template.presentation_negative_prompt or mode_negative_rules[template.presentation_mode]
        if template.presentation_mode == "model":
            compiled_negative_prompt += " Never show a face, facial features, eyes, nose, mouth, hair or top of the head."
        compiled_negative_prompt += " " + presentation_negative_prompt
        secondary_styling_override = (
            f"- SECONDARY STYLING OVERRIDE / POLICY: Any secondary clothing or footwear colours and materials named in the template specification or visible in the template reference are non-authoritative. Preserve only their category, placement and scale. {styling_profile} Select this profile once per product/run and keep it consistent across every model-worn output; never alter the uploaded product to match it."
            if template.presentation_mode == "model" else ""
        )
        presentation_sections = f"""PRESENTATION MODE
{mode_rules[template.presentation_mode]}

OUTPUT DETAILS
- {template.output_details}
{secondary_styling_override}"""
    else:
        presentation_sections = f"""MODEL AND MANNEQUIN PRESENTATION
- For any visible model-worn composition, use a {product.presentation} model presentation. Preserve the garment identity and do not introduce body features that conflict with the requested presentation.
- For any visible, headless, or invisible mannequin composition, use a mannequin with a {product.presentation} gender presentation. The selected user presentation overrides any default or template wording; never substitute a male or female model/mannequin when the user selected the other gender. Product-only flat-lay and detail compositions must not add a person or mannequin.

TEMPLATE PRESENTATION
{template.prompt_instructions}

PROMPT FORMAT RULES
{prompt_rules}"""

    identity_rules = "\n".join([
        "- Preserve the product's actual colour, material, texture, shape, proportions and visible construction.",
        "- Do not add, remove, simplify or redesign visible construction.",
        "- Preserve visible artwork, branding, hardware, seams, edges, closures and surface treatment exactly where present.",
        "- Do not transfer details from another product or composition reference.",
        "- Do not infer hidden construction, material composition, support performance or exact measurements.",
        "- Treat genuinely hidden, cropped or obstructed details as unknown rather than replacing them with a category default.",
    ])
    prompt = f"""Create one ecommerce image using the supplied product reference image as the primary authority for product identity. Use the output details only to control composition, camera angle, pose, framing, lighting and presentation. Preserve observed product features on their original surfaces and do not transfer them to another surface or view. If the requested view is not covered by the references, do not present inferred construction as verified; follow the stated evidence and uncertainty instructions.

REFERENCE-FIRST RULES
- Inspect the product reference image before interpreting the text description.
- Reproduce clearly visible construction detail directly from the product reference image.
- Never replace a visible product feature with a generic category default.
- The product reference overrides generic template conventions and inferred schema defaults.
- Uncertainty applies only to details that are genuinely hidden, obstructed, cropped or impossible to assess from the reference.
- Do not treat a detail as uncertain merely because its exact measurement is unavailable.

IDENTITY RULES
{identity_rules}

PRODUCT FIDELITY PRESERVATION
{fidelity_rules}
{family_policy_section}{template_reference_section}
{presentation_sections}

PRODUCT IDENTITY
Name: {product.name}
Category: {product.category}
Product type: {product.product_type}
Colour summary: {product.colours}
Materials summary: {product.materials}
Visible features:
{features}
Description: {product.description}

COLOUR DATA
{chr(10).join(colour_lines)}

MATERIAL, CONSTRUCTION AND CATEGORY DATA
{chr(10).join(category_lines)}

ADDITIONAL PRODUCT DATA
{chr(10).join(global_lines)}

NEGATIVE PROMPT
- {compiled_negative_prompt}
- The product reference images are the only source of truth for product identity. Do not let the template presentation change the product. Do not add a competing garment, extra product, branding, text, labels, watermarks or props."""

    return GenerationPrompt(
        prompt=prompt.strip(),
        negative_prompt=compiled_negative_prompt,
        reference_images=request.product_reference_images + request.template_reference_images,
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
