"""Backend-owned image generation templates.

The frontend may display template choices, but generation behaviour must come from
this backend registry. Template IDs are stable because they are stored on
generation jobs and generated assets.
"""
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class GenerationTemplate:
    id: str
    channel: str
    category: str
    name: str
    description: str
    prompt_instructions: str
    negative_prompt: str
    aspect_ratio: str
    reference_object_key: str | None = None
    version: int = 1
    applicable_subtypes: tuple[str, ...] = ()
    required_product_fields: tuple[str, ...] = ()
    optional_product_fields: tuple[str, ...] = ()
    prompt_format_rules: tuple[str, ...] = ()
    reference_mode: str = "product_only"
    output_presentation: str = "product_only"
    artwork_visibility: str = "reference_dependent"
    artwork_surface_mode: str = "flat"


TOPS_CLEAN_PRODUCT_SHOT: Final = GenerationTemplate(
    id="ecommerce-clean-product-shot",
    channel="ecommerce",
    category="tops",
    name="Clean Product Shot",
    description="The complete top isolated against a neutral background for clear ecommerce presentation.",
    prompt_instructions=(
        "Create a clean ecommerce product photograph of the complete top. "
        "Show the full garment centred in the frame, front-facing, with the "
        "entire silhouette visible from neckline to hem and both sleeves visible. "
        "Use a simple, evenly lit neutral background. Preserve the exact visible "
        "colour, pattern, neckline, sleeves, seams, fastenings, logos and other "
        "construction details from the reference images. Do not add a person or "
        "styling unless the source image clearly requires the garment to be worn."
    ),
    negative_prompt=(
        "Do not change the product colour, pattern, logo, shape, neckline, sleeves, "
        "hem or construction. Do not add extra garments, accessories, text, labels, "
        "watermarks, props or unrelated objects. Do not crop the garment, show a "
        "partial product, invent hidden details or create duplicate products."
    ),
    aspect_ratio="1:1",
)


TOPS_FRONT_VIEW: Final = GenerationTemplate(
    id="ecommerce-tops-front-view",
    channel="ecommerce",
    category="tops",
    name="Front View",
    description="A straight-on view showing the complete front of the top.",
    prompt_instructions=(
        "Create a straight-on ecommerce front view of the complete top as a "
        "product-only studio presentation. Present the garment clearly without "
        "regularising its observed silhouette, proportions, shoulder construction, "
        "sleeve width, wrinkles or surface wear. Use subtle volume and gentle "
        "contact shadows so it feels cleanly presented rather than like an overhead "
        "flat lay. Use a clean white background with a subtle light-grey studio shadow and even, soft "
        "lighting. Do not show a model, mannequin, body, head or support."
    ),
    negative_prompt=(
        "Do not fabricate or alter visible construction details, especially the "
        "neckline and collar. Do not change the product colour treatment, sleeve "
        "shape, proportions, shoulder construction, surface wear, graphic text, "
        "graphic scale, graphic geometry, component arrangement, linework, colour boundaries or graphic distress. Do not reinterpret visible artwork from its subject description. Do not smooth, clean up, sharpen or redraw the "
        "product. Do not add a model, accessories, extra garments, text, logos, "
        "labels, watermarks or props. Do not crop the product, use an overhead "
        "flat-lay composition or invent identity details that are not visible in "
        "the product references."
    ),
    aspect_ratio="1:1",
    # The text specification is used instead of a product-bearing reference image
    # so another garment cannot override the user's product identity.
    reference_object_key=None,
    applicable_subtypes=("jumper", "t-shirt", "shirt", "top", "tunic", "hoodie", "blouse", "crop-top", "polo", "vest", "tank-top"),
    required_product_fields=(
        "product_type", "colour_details", "global_details.materials",
        "global_details.construction", "category_details.neckline_type",
        "category_details.sleeve_type", "category_details.fit_and_silhouette",
    ),
    optional_product_fields=(
        "category_details.collar_type", "category_details.cuff_details",
        "category_details.pocket_details", "category_details.hood_details",
    ),
    prompt_format_rules=(
        "Product identity data must be presented before presentation instructions.",
        "The product reference image is the primary authority for every visible feature.",
        "Repeat identity-critical attributes as locked constraints.",
        "Use the template only for composition and presentation, never for product identity.",
        "Uncertainty applies only to genuinely hidden, obstructed, cropped or unassessable details.",
    ),
    reference_mode="product_only",
    output_presentation="front_studio_product",
    artwork_visibility="full",
    artwork_surface_mode="flat",
)


_TOPS_REQUIRED_FIELDS = (
    "product_type", "colour_details", "global_details.materials",
    "global_details.construction", "category_details",
)
_TOPS_OPTIONAL_FIELDS = (
    "category_details.collar_type", "category_details.cuff_details",
    "category_details.pocket_details", "category_details.hood_details",
)
_TOPS_RULES = (
    "The product reference image is the primary authority for every visible feature.",
    "Product identity data must be presented before presentation instructions.",
    "Use only the product reference images for identity and preserve every visible product detail.",
    "Uncertainty applies only to genuinely hidden, obstructed, cropped or unassessable details.",
    "Preserve observed silhouette, proportions, shoulder construction, sleeve width, fabric behaviour and surface wear; do not regularise the garment.",
    "Preserve every print, illustration, logo, embroidery and appliqué as immutable artwork, including exact geometry, topology, component count, orientation, linework, internal detail, colour boundaries, text, placement, scale, spacing, fading and distress.",
    "Never substitute a newly drawn version of an artwork merely because it depicts the same subject.",
    "Treat uncertain attributes as uncertain; do not invent conventional replacements.",
)
_TOPS_NEGATIVE = (
    "Do not fabricate or alter visible construction details, especially the neckline "
    "and collar. Do not change the product colour treatment, sleeves, proportions, "
    "texture, pattern or graphics. Do not reinterpret, simplify, replace or redraw visible artwork. Do not smooth, sharpen, clean up or standardise "
    "the garment. Do not add text, logos, watermarks, props, extra garments or "
    "another product. Do not invent hidden details."
)


def _tops_template(*, template_id: str, name: str, description: str, instructions: str, required: tuple[str, ...] = (), artwork_visibility: str = "reference_dependent", artwork_surface_mode: str = "flat") -> GenerationTemplate:
    return GenerationTemplate(
        id=template_id,
        channel="ecommerce",
        category="tops",
        name=name,
        description=description,
        prompt_instructions=instructions,
        negative_prompt=_TOPS_NEGATIVE,
        aspect_ratio="1:1",
        applicable_subtypes=("jumper", "t-shirt", "shirt", "top", "tunic", "hoodie", "blouse", "crop-top", "polo", "vest", "tank-top"),
        required_product_fields=_TOPS_REQUIRED_FIELDS + required,
        optional_product_fields=_TOPS_OPTIONAL_FIELDS,
        prompt_format_rules=_TOPS_RULES,
        reference_mode="product_only",
        output_presentation="product_only",
        artwork_visibility=artwork_visibility,
        artwork_surface_mode=artwork_surface_mode,
    )


TOPS_ECOMMERCE_TEMPLATES: Final[tuple[GenerationTemplate, ...]] = (
    _tops_template(
        template_id="ecommerce-tops-folded-view",
        name="Folded View",
        description="The top neatly folded on a clean studio surface, showing its colour, texture, thickness and distinctive visible details.",
        instructions="Present the top neatly folded as a product-only ecommerce image on a clean white studio surface. Arrange the fold deliberately so the product colour, material texture, apparent thickness, neckline or collar and distinctive construction details remain visible. Use soft lighting and a subtle contact shadow. Do not add props or another product.",
        required=("global_details.materials", "global_details.colour"),
        artwork_visibility="partial",
        artwork_surface_mode="folded",
    ),
    TOPS_FRONT_VIEW,
    _tops_template(
        template_id="ecommerce-tops-over-the-shoulder",
        name="Over-the-Shoulder (No Face)",
        description="A close rear three-quarter view showing the shoulder, neckline, material and upper-back construction without a visible face.",
        instructions="Show the top being worn in a close rear three-quarter view. Frame from below the head so no face is visible. Focus on the shoulder, neckline, upper back, material and construction while preserving the exact product identity.",
        required=("category_details.shoulder_shape",),
        artwork_visibility="none",
        artwork_surface_mode="rear",
    ),
    _tops_template(
        template_id="ecommerce-tops-full-body-model",
        name="Full Body with Model (No Face)",
        description="The top worn as part of a complete outfit, framed from the base of the neck to the feet to communicate fit and proportion.",
        instructions="Show the top worn by a model as part of a simple complete outfit. Frame from the base of the neck to the feet and exclude the face. Keep styling minimal so the top's colour, silhouette, length, sleeves and construction remain clear.",
        required=("category_details.fit_and_silhouette",),
        artwork_visibility="full",
        artwork_surface_mode="worn",
    ),
    _tops_template(
        template_id="ecommerce-tops-close-up",
        name="Close-Up",
        description="A detailed crop of a distinctive neckline, seam, fastening, pocket, cuff or other visible construction feature.",
        instructions="Create a detailed ecommerce close-up of the most distinctive visible construction feature of the top. Prioritise the feature supported by the product references, such as neckline, stitching, cuff, pocket, button or fabric structure. Do not invent a feature.",
        required=("global_details.construction",),
        artwork_visibility="conditional",
        artwork_surface_mode="detail",
    ),
    _tops_template(
        template_id="ecommerce-tops-back",
        name="Back",
        description="A complete product-only rear view showing the back silhouette, length, seams and construction.",
        instructions="Show the complete top from the rear as a product-only studio presentation. Keep the full back silhouette, shoulders, sleeves and hem visible with minimal surrounding space. Infer only details supported by the product references and analysis.",
        required=("category_details.fit_and_silhouette",),
        artwork_visibility="none",
        artwork_surface_mode="rear",
    ),
    _tops_template(
        template_id="ecommerce-tops-front-model",
        name="Front with Model (No Face)",
        description="A closer front view of the top being worn, framed around the garment without showing the model's face.",
        instructions="Show the top worn by a model in a close front-facing view, cropped below the face. Demonstrate the fit, neckline, sleeves and front details. Keep the pose and styling simple and do not obscure the garment.",
        required=("category_details.fit_and_silhouette",),
        artwork_visibility="full",
        artwork_surface_mode="worn",
    ),
    _tops_template(
        template_id="ecommerce-tops-back-model",
        name="Back with Model (No Face)",
        description="A closer rear view of the top being worn, showing how the back, shoulders, sleeves and hem fit and drape.",
        instructions="Show the top worn by a model from the rear, cropped below the head so no face is visible. Show the back, shoulders, sleeves and hem clearly, including the way the product fits and drapes.",
        required=("category_details.fit_and_silhouette",),
        artwork_visibility="none",
        artwork_surface_mode="rear",
    ),
    _tops_template(
        template_id="ecommerce-tops-side-angle-model",
        name="Side / Angled with Model (No Face)",
        description="A side or three-quarter view of the top being worn, showing depth, silhouette, structure and fit.",
        instructions="Show the top worn by a model from a side or three-quarter angle, cropped below the face. Make the garment's depth, silhouette, shoulder shape, sleeve shape and fit visible while keeping the product identity unchanged.",
        required=("category_details.shoulder_shape", "category_details.fit_and_silhouette"),
        artwork_visibility="partial",
        artwork_surface_mode="angled",
    ),
    _tops_template(
        template_id="ecommerce-tops-fabric",
        name="Fabric Shot",
        description="A macro view of the top's material, highlighting texture, weave, surface finish and colour.",
        instructions="Create a macro ecommerce detail of the product material. Show the actual visible texture, knit or weave, thickness appearance, surface finish and colour from the product references. Keep the detail faithful and do not invent a different fabric.",
        required=("global_details.materials", "global_details.colour"),
        artwork_visibility="conditional",
        artwork_surface_mode="detail",
    ),
)

# Category-specific ecommerce templates mirrored from the frontend recipe IDs.
# Their text controls presentation only; product identity always comes from the
# product reference images and category schema.
def _support_template(category: str, template_id: str, name: str, description: str, instruction: str, subtypes: tuple[str, ...]) -> GenerationTemplate:
    return GenerationTemplate(
        id=template_id,
        channel="ecommerce",
        category=category,
        name=name,
        description=description,
        prompt_instructions=instruction,
        negative_prompt=(
            "Do not fabricate or alter visible product construction, proportions, "
            "colour, texture, graphics, closures, hardware or material details. "
            "Do not invent hidden details, extra products, labels, logos or props."
        ),
        aspect_ratio="1:1",
        applicable_subtypes=subtypes,
        required_product_fields=("product_type", "global_details.colour", "global_details.materials", "global_details.construction", "category_details"),
        optional_product_fields=("category_details.visible_uncertainties",),
        prompt_format_rules=(
            "The product reference images are the primary authority for every visible feature.",
            "Use the template only for composition and presentation.",
            "Uncertainty applies only to genuinely hidden, obstructed, cropped or unassessable details.",
        ),
        reference_mode="product_only",
        output_presentation="product_only" if "model" not in template_id and "feet" not in template_id else "worn_product",
    )

_OUTERWEAR_SUBTYPES = ("coat", "jacket", "blazer", "waistcoat", "parka", "gilet", "bomber", "trench coat", "raincoat", "puffer")
_FOOTWEAR_SUBTYPES = ("heels", "trainers", "sandals", "crocs", "boots", "loafers", "flats", "sliders", "mules")
_SOCKS_SUBTYPES = ("normal", "running", "ankle", "trainer", "crew", "knee-high", "stockings", "compression", "thermal")

OUTERWEAR_ECOMMERCE_TEMPLATES: Final[tuple[GenerationTemplate, ...]] = tuple(
    _support_template("outerwear", template_id, name, description, instruction, _OUTERWEAR_SUBTYPES)
    for template_id, name, description, instruction in (
        ("ecommerce-outerwear-front-close", "Front Close", "A tight upper-front crop showing collar and front construction.", "Show a close front crop of the outerwear's visible upper construction, preserving collar, lapel, closures and material.") ,
        ("ecommerce-outerwear-front-medium", "Front Medium", "The complete outerwear piece shown from the front.", "Show the complete outerwear from the front with sleeves and hem visible and its true volume preserved."),
        ("ecommerce-outerwear-over-the-shoulder", "Over-the-Shoulder (No Face)", "A rear three-quarter view focused on shoulder and upper-back construction.", "Show the outerwear worn in a rear three-quarter crop without a visible face; preserve shoulder, collar and upper-back details."),
        ("ecommerce-outerwear-full-body-model", "Full Body with Model (No Face)", "The outerwear worn as part of a complete outfit.", "Show the outerwear worn in a restrained full-body outfit from neck to feet without showing the face; keep the product clear."),
        ("ecommerce-outerwear-close-up", "Close-Up", "A close crop of a fastening, seam or construction detail.", "Create a close-up of the most distinctive supported outerwear construction detail, such as a fastening, seam, pocket or hardware."),
        ("ecommerce-outerwear-back", "Back", "A complete product-only rear view.", "Show the complete rear silhouette and construction of the outerwear as a product-only image."),
        ("ecommerce-outerwear-front-model", "Front with Model (No Face)", "A front view of the outerwear being worn.", "Show the outerwear worn from the front, cropped below the face, with fit and construction unobscured."),
        ("ecommerce-outerwear-back-model", "Back with Model (No Face)", "A rear view of the outerwear being worn.", "Show the outerwear worn from the rear, cropped below the head, preserving fit and drape."),
        ("ecommerce-outerwear-side-angle-model", "Side / Angled with Model (No Face)", "A side or three-quarter worn view.", "Show a side or three-quarter view worn by a model without a visible face, preserving depth and silhouette."),
        ("ecommerce-outerwear-fabric", "Fabric Shot", "A macro view of outerwear material and surface finish.", "Create a macro material detail showing the actual texture, weight appearance and surface finish without inventing a different fabric."),
    )
)

FOOTWEAR_ECOMMERCE_TEMPLATES: Final[tuple[GenerationTemplate, ...]] = tuple(
    _support_template("footwear", template_id, name, description, instruction, _FOOTWEAR_SUBTYPES)
    for template_id, name, description, instruction in (
        ("ecommerce-footwear-three-quarter-product", "Three-Quarter Product", "An angled product-only footwear view.", "Show the footwear from a three-quarter product-only angle, preserving toe, side, upper and sole shape."),
        ("ecommerce-footwear-outer-side", "Outer Side", "A complete outer-side profile.", "Show the footwear's outer-side profile with its complete silhouette, upper construction and sole."),
        ("ecommerce-footwear-inner-side", "Inner Side", "A complete inner-side profile.", "Show the footwear's inner-side profile and visible medial construction without inventing hidden details."),
        ("ecommerce-footwear-front-view", "Front View", "A head-on footwear product view.", "Show the footwear head-on, preserving toe shape, front proportions and upper details."),
        ("ecommerce-footwear-rear-view", "Rear View", "A straight-on rear footwear view.", "Show the rear heel construction and sole thickness without inventing unseen details."),
        ("ecommerce-footwear-top-view", "Top View", "A direct overhead footwear view.", "Show the footwear from above, preserving toe-to-heel shape, opening and visible fastenings."),
        ("ecommerce-footwear-sole-view", "Sole View", "A complete underside view.", "Show the actual outsole, tread and visible construction from heel to toe."),
        ("ecommerce-footwear-material-and-detail", "Material and Detail", "A close material and construction crop.", "Create a close crop of actual footwear material, stitching and supported construction details."),
        ("ecommerce-footwear-front-on-feet", "Front on Feet", "Footwear worn in a front-facing stance.", "Show the footwear worn by an adult from the front, cropped below the knees, with no extra footwear."),
        ("ecommerce-footwear-side-on-feet", "Side on Feet", "Footwear worn in a side stance.", "Show the footwear worn by an adult from the side, cropped below the knees, preserving fit and profile."),
    )
)

SOCKS_ECOMMERCE_TEMPLATES: Final[tuple[GenerationTemplate, ...]] = tuple(
    _support_template("socks", template_id, name, description, instruction, _SOCKS_SUBTYPES)
    for template_id, name, description, instruction in (
        ("ecommerce-socks-three-quarter-on-feet", "Three-Quarter on Feet", "Socks worn in a three-quarter stance.", "Show both socks worn by an adult in a three-quarter stance with no footwear and lower legs visible above the cuffs."),
        ("ecommerce-socks-rear-on-feet", "Rear on Feet", "A rear sock view showing heel construction.", "Show the rear of the socks worn by an adult, preserving heel shape and cuff height with no footwear."),
        ("ecommerce-socks-folded-product", "Folded Product", "Socks neatly folded on a plain surface.", "Present the socks folded on a plain surface while keeping colour, pattern and distinctive construction visible."),
        ("ecommerce-socks-flat-lay", "Flat Lay", "Socks arranged flat and photographed from above.", "Arrange the socks naturally in a flat lay showing complete shape, length and pattern."),
        ("ecommerce-socks-heel-detail", "Heel Detail", "A close sock heel and knit construction crop.", "Show a close-up of the actual heel shape, knit texture and supported construction."),
        ("ecommerce-socks-knit-texture", "Knit Texture", "A macro sock knit and surface detail.", "Create a macro view of the actual yarn, knit pattern, texture and finish."),
        ("ecommerce-socks-front-on-feet", "Front on Feet", "Socks worn in a front-facing stance.", "Show both socks worn by an adult from the front, with no footwear and the frame below the knees."),
        ("ecommerce-socks-heel-detail-on-foot", "Heel Detail on Foot", "A close rear three-quarter heel view on foot.", "Show a close rear three-quarter view of a sock on an adult foot, with no footwear and the lower leg visible."),
    )
)

# The old generic choice remains resolvable for existing saved selections.
_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    template.id: template
    for template in TOPS_ECOMMERCE_TEMPLATES + OUTERWEAR_ECOMMERCE_TEMPLATES + FOOTWEAR_ECOMMERCE_TEMPLATES + SOCKS_ECOMMERCE_TEMPLATES
}
_LEGACY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {TOPS_CLEAN_PRODUCT_SHOT.id: TOPS_CLEAN_PRODUCT_SHOT}


def get_generation_template(template_id: str) -> GenerationTemplate | None:
    """Return a template by its stable ID, or ``None`` when it is unknown."""
    return _TEMPLATES.get(template_id) or _LEGACY_TEMPLATES.get(template_id)


def validate_generation_template(template_id: str, *, category: str, channel: str, subtype: str | None = None) -> GenerationTemplate:
    """Load a template and ensure it is valid for the requested product."""
    template = get_generation_template(template_id)
    if template is None:
        raise ValueError(f"Unknown generation template: {template_id}")
    if template.category != category.strip().lower():
        raise ValueError(f"Template {template_id} is not available for category {category}")
    if template.channel != channel.strip().lower():
        raise ValueError(f"Template {template_id} is not available for channel {channel}")
    if subtype is not None and template.applicable_subtypes:
        normalized_subtype = subtype.strip().lower()
        # Recognition often preserves useful qualifiers (for example
        # "short-sleeve V-neck T-shirt"). Match the canonical garment subtype
        # without discarding those qualifiers from the prompt.
        matches = normalized_subtype in template.applicable_subtypes or any(
            allowed in normalized_subtype for allowed in template.applicable_subtypes
        )
        if not matches:
            raise ValueError(f"Template {template_id} is not available for subtype {subtype}")
    return template


def list_generation_templates(*, category: str | None = None, channel: str | None = None, subtype: str | None = None) -> list[GenerationTemplate]:
    """List active templates, optionally filtered by category and channel."""
    templates = list(_TEMPLATES.values())
    if category is not None:
        templates = [template for template in templates if template.category == category.strip().lower()]
    if channel is not None:
        templates = [template for template in templates if template.channel == channel.strip().lower()]
    if subtype is not None:
        normalized_subtype = subtype.strip().lower()
        templates = [template for template in templates if not template.applicable_subtypes or normalized_subtype in template.applicable_subtypes]
    return templates
