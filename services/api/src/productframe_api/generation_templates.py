"""Backend-owned image generation templates.

The frontend may display template choices, but generation behaviour must come from
this backend registry. Template IDs are stable because they are stored on
generation jobs and generated assets.
"""
from dataclasses import dataclass, replace
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
    applicable_families: tuple[str, ...] = ()
    required_product_fields: tuple[str, ...] = ()
    optional_product_fields: tuple[str, ...] = ()
    prompt_format_rules: tuple[str, ...] = ()
    reference_mode: str = "product_only"
    output_presentation: str = "product_only"
    artwork_visibility: str = "reference_dependent"
    artwork_surface_mode: str = "flat"
    # Evidence groups describe the minimum visual coverage needed from the
    # user's source media. An empty tuple intentionally means no additional
    # media gate (currently used by Socks).
    required_evidence: tuple[str, ...] = ()


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

# Category-specific ecommerce templates mirrored by the frontend recipe choices.
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

_OUTERWEAR_SUBTYPES = ("coat", "jacket", "blazer", "waistcoat", "parka", "gilet", "bomber", "trench coat", "raincoat", "puffer", "hoodie", "sweatshirt", "fleece")
_FOOTWEAR_SUBTYPES = ("heels", "trainers", "sandals", "crocs", "boots", "loafers", "flats", "sliders", "mules")
_SOCKS_SUBTYPES = ("normal", "running", "ankle", "trainer", "crew", "knee-high", "stockings", "compression", "thermal")
_BOTTOMS_SUBTYPES = ("shorts", "skirt", "leggings", "trousers", "jeans", "cargo trousers", "joggers", "chinos")
_BOTTOMS_FAMILIES = ("structured_bottoms", "casual_bottoms", "leggings", "skirts")

BOTTOMS_FAMILY_POLICIES: Final[dict[str, str]] = {
    "structured_bottoms": (
        "Preserve the waistband, rise, closure, belt loops, pockets, pleats, darts, "
        "panels, leg shape, leg width and hem when visible. For construction details, "
        "prioritise the most distinctive supported pocket, panel, seam, closure or "
        "fastening; do not assume five-pocket denim construction."
    ),
    "casual_bottoms": (
        "Preserve elastic waistbands, drawcords, soft or stretch fabric, cuffs, "
        "casual fit and visible pockets or panels. Do not introduce belt loops, a "
        "rigid denim surface, a tailored crease or a trouser fly unless visible."
    ),
    "leggings": (
        "Preserve the close fit, stretch or compression appearance, waistband, seams, "
        "panels, gusset when visible, and ankle or cropped hem. Show a pocket or side "
        "construction detail only when supported. Do not assume a fly, belt loops, "
        "rigid denim, trouser seat or five-pocket construction."
    ),
    "skirts": (
        "Preserve the waistband, waist height, closure, silhouette, pleats, panels, "
        "drape, length, hem and slit when visible. Interpret lower construction as "
        "hem and lower-skirt detail. Do not use leg shape, leg width, trouser rise, "
        "seat or trouser-fly assumptions."
    ),
}

_GENERIC_BOTTOMS_FAMILY_POLICY = (
    "Use only visibly supported bottoms construction. Preserve the observed waistband, "
    "silhouette, proportions, closures, seams, pockets and hem. Do not assume whether "
    "the product is structured, elasticated, close-fitting or skirt-shaped."
)


def get_bottoms_family_policy(family: str | None) -> str:
    """Return the conservative or family-specific bottoms rendering policy."""
    return BOTTOMS_FAMILY_POLICIES.get(family or "", _GENERIC_BOTTOMS_FAMILY_POLICY)


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
        ("ecommerce-socks-three-quarter-on-feet", "Three-Quarter on Feet", "Two socks worn side-by-side with both feet flat on the ground.", "Match the reference composition: show both socks worn by an adult standing with both feet fully flat on the ground, side-by-side and close together, toes pointing in the same direction. Keep the feet parallel and weight distributed across both feet; do not lift, cross, bend or float either foot. Show no footwear and lower legs visible above the cuffs."),
        ("ecommerce-socks-rear-on-feet", "Rear on Feet", "A rear sock view showing heel construction.", "Show the rear of the socks worn by an adult, preserving heel shape and cuff height with no footwear."),
        ("ecommerce-socks-folded-product", "Folded Product", "Socks neatly folded on a plain surface.", "Present the socks folded on a plain surface while keeping colour, pattern and distinctive construction visible."),
        ("ecommerce-socks-flat-lay", "Flat Lay", "Socks arranged flat and photographed from above.", "Arrange the socks naturally in a flat lay showing complete shape, length and pattern."),
        ("ecommerce-socks-heel-detail", "Heel Detail", "A close sock heel and knit construction crop.", "Show a close-up of the actual heel shape, knit texture and supported construction."),
        ("ecommerce-socks-knit-texture", "Knit Texture", "A macro sock knit and surface detail.", "Create a macro view of the actual yarn, knit pattern, texture and finish."),
        ("ecommerce-socks-front-on-feet", "Front on Feet", "Socks worn in a front-facing stance.", "Show both socks worn by an adult from the front, with no footwear and the frame below the knees."),
        ("ecommerce-socks-heel-detail-on-foot", "Heel Detail on Foot", "A close rear three-quarter heel view on foot.", "Show a close rear three-quarter view of a sock on an adult foot, with no footwear and the lower leg visible."),
    )
)

_BOTTOMS_REQUIRED_FIELDS = (
    "product_type",
    "colour_details",
    "global_details.materials",
    "global_details.construction",
    "category_details",
    "category_details.waistband_type",
    "category_details.leg_shape",
    "category_details.fit_and_silhouette",
)
_BOTTOMS_OPTIONAL_FIELDS = (
    "category_details.waist_height",
    "category_details.fly_or_closure",
    "category_details.leg_width",
    "category_details.garment_length",
    "category_details.hem_details",
    "category_details.pocket_details",
    "category_details.pleats_or_darts",
    "category_details.belt_loops",
    "category_details.panel_or_seam_details",
    "category_details.visible_uncertainties",
)
_BOTTOMS_RULES = (
    "The product reference images are the primary authority for every visible feature.",
    "Product identity data must be presented before presentation instructions.",
    "Preserve the observed waistband, waist height, rise, leg shape, leg width, garment length, hem, pockets, closures, belt loops, pleats, darts, panels and seams.",
    "Use the template only for composition and presentation, never for product identity.",
    "Preserve visible graphics, logos, embroidery, appliques, patterns, washes and colour boundaries exactly as shown in the product references.",
    "For model-worn templates, use a real model and keep the framing limited to the waist or lower midsection downward; do not turn the output into a face-led or full-body portrait.",
    "For folded, flat-lay and construction-detail templates, show the product naturally supported by the specified surface rather than an invisible mannequin or floating garment.",
    "If a detail is hidden, obstructed or not present on the product, leave it uncertain or omit it rather than inventing a conventional replacement.",
)
_BOTTOMS_NEGATIVE = (
    "Do not change the product subtype, colour, material, rise, waistband, leg shape, leg width, length, fit, hem, pockets, closures, belt loops, pleats, darts, panels, seams or visible artwork. "
    "Do not turn trousers into shorts, a skirt into trousers or otherwise regularise the product into another bottoms type. "
    "Do not add extra products, competing garments, accessories, text, labels, watermarks or props. Do not invent hidden construction, duplicate the product or redraw visible artwork. "
    "Do not use an invisible mannequin when the template calls for a real model, and do not show a person when the template calls for a product-only surface presentation."
)


def _bottoms_template(
    *,
    template_id: str,
    name: str,
    description: str,
    instructions: str,
    required: tuple[str, ...] = (),
    artwork_visibility: str = "reference_dependent",
    artwork_surface_mode: str = "flat",
    output_presentation: str = "product_only",
) -> GenerationTemplate:
    return GenerationTemplate(
        id=template_id,
        channel="ecommerce",
        category="bottoms",
        name=name,
        description=description,
        prompt_instructions=instructions,
        negative_prompt=_BOTTOMS_NEGATIVE,
        aspect_ratio="1:1",
        applicable_subtypes=_BOTTOMS_SUBTYPES,
        required_product_fields=_BOTTOMS_REQUIRED_FIELDS + required,
        optional_product_fields=_BOTTOMS_OPTIONAL_FIELDS,
        prompt_format_rules=_BOTTOMS_RULES,
        reference_mode="product_only",
        output_presentation=output_presentation,
        artwork_visibility=artwork_visibility,
        artwork_surface_mode=artwork_surface_mode,
        applicable_families=_BOTTOMS_FAMILIES,
    )


BOTTOMS_ECOMMERCE_TEMPLATES: Final[tuple[GenerationTemplate, ...]] = (
    _bottoms_template(
        template_id="ecommerce-bottoms-front-view",
        name="Front View",
        description="A complete product-only front view showing the bottoms from waistband to hem.",
        instructions="Create a straight-on ecommerce front view of the complete bottoms as a product-only studio presentation. Show the full silhouette from waistband to hem with the actual rise, leg shape, leg width, pockets, closures, pleats or darts and hem visible where supported by the references. Use a clean neutral background, soft even lighting and minimal surrounding space. Present the garment naturally without a model, mannequin, body or support.",
        required=("category_details.waist_height", "category_details.leg_width", "category_details.garment_length", "category_details.hem_details"),
        artwork_visibility="full",
    ),
    _bottoms_template(
        template_id="ecommerce-bottoms-back-view",
        name="Back View",
        description="A complete product-only rear view showing the back silhouette, seat, seams and pockets.",
        instructions="Create a complete product-only rear view of the bottoms from waistband to hem. Preserve the actual back rise, seat shape, rear pockets, yoke or panel construction, seams, leg shape, leg width and hem. Use a clean neutral studio background and do not invent details that are hidden from the product references. Do not show a person, mannequin or support.",
        required=("category_details.waist_height", "category_details.leg_width", "category_details.garment_length", "category_details.hem_details"),
        artwork_visibility="reference_dependent",
        artwork_surface_mode="rear",
    ),
    _bottoms_template(
        template_id="ecommerce-bottoms-side-angle-product",
        name="Side / Three-Quarter Product",
        description="A waist-down three-quarter view of the bottoms worn by a model, showing front-side fit, rise, leg profile and full length.",
        instructions="Show the complete bottoms worn by a real adult model from a relaxed 30–45-degree side or three-quarter angle. Frame from the waist or lower midsection downward so the waistband, rise, fit, leg shape, garment length and hems remain clear; exclude the face, head, shoulders and chest. Keep styling neutral and secondary, and preserve the exact product construction.",
        required=("category_details.waist_height", "category_details.leg_width", "category_details.garment_length", "category_details.fit_and_silhouette"),
        artwork_visibility="partial",
        artwork_surface_mode="angled",
        output_presentation="worn_product",
    ),
    _bottoms_template(
        template_id="ecommerce-bottoms-folded-product-flat-lay",
        name="Folded Product Flat Lay",
        description="The bottoms neatly folded on a clean neutral surface while keeping important visible details readable.",
        instructions="Arrange the bottoms in a neat folded product flat lay photographed from directly above on a clean neutral surface. Choose a fold that keeps as much of the actual waistband, closure, pockets, fabric, seams, leg construction and distinctive visible details readable as the product allows. Make the garment visibly rest on the surface with natural folds and contact shadows. Preserve the product's colour, pattern, material appearance and construction. Do not add props, another product, styling items or invented details.",
        required=("global_details.materials",),
        artwork_visibility="partial",
        artwork_surface_mode="folded",
    ),
    _bottoms_template(
        template_id="ecommerce-bottoms-front-model",
        name="Front Model",
        description="A waist-down front view of the bottoms worn by a model, showing fit, leg shape and full length without a face.",
        instructions="Show the bottoms worn by a real adult model in a simple straight-on front-facing ecommerce pose. Frame from the waist or lower midsection downward to below the hem; exclude the face, head, shoulders and chest. Keep styling neutral and secondary so the actual waistband, rise, fit, leg shape, length, pockets and hem remain clear. Do not add another pair of bottoms or obscure the product.",
        required=("category_details.garment_length", "category_details.fit_and_silhouette"),
        artwork_visibility="full",
        artwork_surface_mode="worn",
        output_presentation="worn_product",
    ),
    _bottoms_template(
        template_id="ecommerce-bottoms-back-model",
        name="Back Model",
        description="A waist-down rear view of the bottoms worn by a model, showing the seat, back pockets, drape and full length.",
        instructions="Show the bottoms worn by a real adult model from the rear in a restrained straight-on ecommerce pose. Frame from the waist or lower midsection downward to below the hem; exclude the face, head, shoulders and chest. Preserve the actual back rise, seat, pockets, seams, leg shape, drape and hem, with no competing lower-body garment or styling that obscures the product.",
        required=("category_details.garment_length", "category_details.fit_and_silhouette"),
        artwork_visibility="reference_dependent",
        artwork_surface_mode="worn",
        output_presentation="worn_product",
    ),
    _bottoms_template(
        template_id="ecommerce-bottoms-waistband-closure-detail",
        name="Waistband & Closure Detail",
        description="A close model-worn waist-to-upper-thigh crop showing the waistband, closure, belt loops and upper pocket construction.",
        instructions="Create a close ecommerce detail of the upper section of the bottoms worn by a real adult model. Use a slight front-side angle similar to a premium construction reference and frame from the waist to the upper thigh, with no face, head, shoulders or chest. Show the actual waistband, waist height, rise, fly or closure, belt loops, drawcord, pleats or darts that are visible in the product references. Keep any plain neutral top edge and partial hand secondary; never obscure the product. If a listed feature is absent, focus on the other supported upper construction instead of inventing it.",
        required=("category_details.waist_height", "category_details.fly_or_closure", "category_details.belt_loops"),
        artwork_visibility="conditional",
        artwork_surface_mode="detail",
        output_presentation="worn_product",
    ),
    _bottoms_template(
        template_id="ecommerce-bottoms-pocket-panel-detail",
        name="Pocket Panel Detail",
        description="A tight diagonal flat-lay macro showing the pocket panel, center closure, seams, rivets and stitching.",
        instructions="Create a tight ecommerce construction macro with the bottoms laid completely flat on a clean neutral surface. Use a strong diagonal overhead angle. Make the most distinctive supported pocket or panel the clear subject while keeping the center front button, closed fly or zipper, central seam, adjacent belt loop and relevant stitching in view where present. Show natural flat-lay contact shadows and do not use a model, mannequin or support. If the product has no pocket, show another supported construction feature without inventing one.",
        required=("global_details.construction", "category_details.pocket_details", "category_details.panel_or_seam_details"),
        artwork_visibility="conditional",
        artwork_surface_mode="detail",
    ),
    _bottoms_template(
        template_id="ecommerce-bottoms-hem-leg-detail",
        name="Hem & Leg Detail",
        description="A diagonal flat-lay macro focused on the straight-leg seam, hem finish, leg opening and stitching.",
        instructions="Create a close ecommerce detail of the lower leg and hem with the bottoms lying completely flat on a clean neutral surface. Use a diagonal overhead angle and show the actual garment length, leg opening, hem finish, cuff, slit, raw edge and stitching supported by the product references. Preserve the real leg shape and fabric behaviour with natural contact shadows; do not show a model, mannequin or support and do not add a cuff, slit or finishing treatment that is not visible.",
        required=("category_details.garment_length", "category_details.leg_width", "category_details.hem_details"),
        artwork_visibility="conditional",
        artwork_surface_mode="detail",
    ),
)

_UNDERWEAR_SUBTYPES = ("lingerie", "boxers", "briefs", "bikini briefs", "bra", "bralette", "vest", "undershirt")
_UNDERWEAR_REQUIRED_FIELDS = (
    "product_type",
    "colour_details",
    "global_details.materials",
    "global_details.construction",
    "category_details",
    "category_details.coverage",
    "category_details.waist_height",
    "category_details.rise",
    "category_details.elastic_details",
    "category_details.fit_and_silhouette",
)
_UNDERWEAR_OPTIONAL_FIELDS = (
    "global_details.branding",
    "category_details.support_details",
    "category_details.closure_details",
    "category_details.seam_details",
    "category_details.fabric_appearance",
    "category_details.visible_uncertainties",
)
_UNDERWEAR_RULES = (
    "The product reference images are the primary authority for every visible feature.",
    "Product identity data must be presented before presentation instructions.",
    "Preserve the observed coverage, waistband height, rise, pouch or cup construction, leg openings, seams, elastic and fabric behaviour.",
    "Use the template only for composition and presentation, never for product identity.",
    "Do not infer body measurements, size, comfort, performance or support level from appearance alone.",
    "Keep the garment non-sexualised and catalogue-focused when a model is required.",
    "If a detail is hidden or uncertain, preserve that uncertainty rather than inventing a conventional replacement.",
)
_UNDERWEAR_NEGATIVE = (
    "Do not change the product subtype, colour, pattern, waistband, rise, coverage, pouch or cup shape, leg openings, seams, elastic, fabric appearance or fit. "
    "Do not add a competing garment, extra product, branding, text, labels, watermarks or props. "
    "Do not infer body measurements, size, support, comfort or unseen construction. "
    "Do not sexualise the model, show a face or create a suggestive pose when the template calls for a product-focused crop."
)


def _underwear_template(
    *, template_id: str, name: str, description: str, instructions: str,
    required: tuple[str, ...] = (), artwork_visibility: str = "reference_dependent",
    artwork_surface_mode: str = "flat", output_presentation: str = "product_only",
) -> GenerationTemplate:
    return GenerationTemplate(
        id=template_id, channel="ecommerce", category="underwear", name=name,
        description=description, prompt_instructions=instructions,
        negative_prompt=_UNDERWEAR_NEGATIVE, aspect_ratio="1:1",
        applicable_subtypes=_UNDERWEAR_SUBTYPES,
        applicable_families=("lower_body_underwear",),
        required_product_fields=_UNDERWEAR_REQUIRED_FIELDS + required,
        optional_product_fields=_UNDERWEAR_OPTIONAL_FIELDS,
        prompt_format_rules=_UNDERWEAR_RULES, reference_mode="product_only",
        output_presentation=output_presentation,
        artwork_visibility=artwork_visibility, artwork_surface_mode=artwork_surface_mode,
    )


UNDERWEAR_ECOMMERCE_TEMPLATES: Final[tuple[GenerationTemplate, ...]] = (
    _underwear_template(
        template_id="ecommerce-underwear-front-model", name="Front with Model (No Face)",
        description="A waist-down front view worn by an adult model, showing the underwear's fit, rise and leg length without a face.",
        instructions="Show the underwear worn by an adult model in a restrained straight-on front-facing ecommerce pose. Frame from the lower abdomen to below the leg openings, exclude the face and keep the product clearly visible. Preserve the exact waistband, rise, pouch or cup construction, coverage, leg openings, seams and fabric appearance.",
        required=("category_details.coverage", "category_details.rise", "category_details.fit_and_silhouette"),
        artwork_visibility="full", artwork_surface_mode="worn", output_presentation="worn_product",
    ),
    _underwear_template(
        template_id="ecommerce-underwear-front-flat-lay", name="Front Flat Lay",
        description="A complete product-only front view of the underwear laid flat against a clean neutral surface.",
        instructions="Present the complete underwear laid flat and front-facing on a clean neutral studio surface. Keep the waistband, rise, pouch or cup construction, leg openings, seams and proportions readable with natural contact shadows. Do not show a model, mannequin, body or support.",
        required=("category_details.coverage", "category_details.rise"), artwork_visibility="full",
    ),
    _underwear_template(
        template_id="ecommerce-underwear-back-flat-lay", name="Back Flat Lay",
        description="A complete product-only rear view showing the underwear's back coverage, seams and leg openings.",
        instructions="Present the complete underwear laid flat and rear-facing on a clean neutral studio surface. Show the actual back coverage, rise, seat shape, seams, waistband and leg openings supported by the product references. Do not invent hidden construction or show a model, mannequin, body or support.",
        required=("category_details.coverage", "category_details.rise", "category_details.seam_details"),
        artwork_visibility="reference_dependent", artwork_surface_mode="rear",
    ),
    _underwear_template(
        template_id="ecommerce-underwear-rear-three-quarter", name="Rear Three-Quarter",
        description="An angled product-only rear view showing the underwear's side profile, back coverage and silhouette.",
        instructions="Show the underwear as a product-only rear three-quarter presentation on a clean neutral background. Make the side profile, back coverage, rise, waistband and leg openings clear while preserving the actual silhouette and fabric behaviour. Do not show a person, mannequin or invented support.",
        required=("category_details.coverage", "category_details.fit_and_silhouette"),
        artwork_visibility="reference_dependent", artwork_surface_mode="angled",
    ),
    _underwear_template(
        template_id="ecommerce-underwear-front-product", name="Front Product",
        description="A clean product-only front presentation showing the complete underwear silhouette and front construction.",
        instructions="Create a clean front-facing ecommerce product photograph of the complete underwear against a simple neutral background. Show the full silhouette and preserve the exact waistband, pouch or cup construction, rise, seams, leg openings, colour and fabric appearance. Do not add a person, mannequin, extra garment or props.",
        required=("category_details.coverage", "category_details.fit_and_silhouette"), artwork_visibility="full",
    ),
    _underwear_template(
        template_id="ecommerce-underwear-side-profile", name="Side Profile",
        description="A product-only side profile showing the underwear's depth, rise, coverage and leg silhouette.",
        instructions="Show the underwear in a clean product-only side profile against a neutral background. Preserve the actual rise, side seam, coverage, leg opening, depth and silhouette without regularising proportions or inventing hidden construction. Do not show a person, mannequin or support.",
        required=("category_details.coverage", "category_details.rise", "category_details.fit_and_silhouette"),
        artwork_visibility="reference_dependent", artwork_surface_mode="angled",
    ),
    _underwear_template(
        template_id="ecommerce-underwear-waistband-detail", name="Waistband & Fabric Detail",
        description="A close-up of the waistband, elastic construction, stitching and fabric texture.",
        instructions="Create a close ecommerce construction detail focused on the actual waistband, elastic, seam and fabric texture. Use a tight crop with soft even lighting and preserve the product's knit or jersey appearance, colour and stitching. Show only details supported by the product references; do not invent labels, branding or construction.",
        required=("global_details.materials", "category_details.elastic_details", "category_details.seam_details", "category_details.fabric_appearance"),
        artwork_visibility="conditional", artwork_surface_mode="detail",
    ),
)

# Minimum source-media coverage for templates whose output depends on a
# particular product surface. These are deliberately small capture groups,
# not one rigid upload requirement per template.
_FRONT_EVIDENCE = ("front_view",)
_REAR_EVIDENCE = ("rear_view",)
# Bottoms intentionally use only front/rear evidence for every family. More
# specialised evidence can be added later without changing template IDs.
_BOTTOMS_FRONT_EVIDENCE = ("front_view",)
_BOTTOMS_REAR_EVIDENCE = ("rear_view",)
_FRONT_REAR_EVIDENCE = ("front_view", "rear_view")
_UNDERWEAR_FRONT_EVIDENCE = ("front_view",)
_UNDERWEAR_REAR_EVIDENCE = ("rear_view",)


def _evidence_for_template(template: GenerationTemplate) -> tuple[str, ...]:
    template_id = template.id
    if template.category == "socks":
        # A validated, correctly classified sock image is sufficient for every
        # current Socks output. Do not introduce an angle gate here.
        return ()
    if template.category == "footwear":
        if "sole" in template_id or "underside" in template_id:
            return ("sole_or_underside",)
        if "rear" in template_id:
            return ("rear_view",)
        return ("top_view",)
    if template.category == "outerwear":
        if "back" in template_id or "over-the-shoulder" in template_id:
            return _REAR_EVIDENCE
        return _FRONT_EVIDENCE
    if template.category == "bottoms":
        if "back" in template_id:
            return _BOTTOMS_REAR_EVIDENCE
        return _BOTTOMS_FRONT_EVIDENCE
    if template.category == "underwear":
        # The current pack is intentionally lower-body only. Its evidence
        # vocabulary stays limited to front/rear views; future family packs
        # can define their own rules without changing this mapping.
        if "back" in template_id or "rear" in template_id:
            return _UNDERWEAR_REAR_EVIDENCE
        return _UNDERWEAR_FRONT_EVIDENCE
    if template.category == "tops":
        if "back" in template_id or "over-the-shoulder" in template_id:
            return _REAR_EVIDENCE
        return _FRONT_EVIDENCE
    return ()


# The old generic choice remains resolvable for existing saved selections.
_BASE_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    template.id: replace(template, required_evidence=_evidence_for_template(template))
    for template in TOPS_ECOMMERCE_TEMPLATES + OUTERWEAR_ECOMMERCE_TEMPLATES + FOOTWEAR_ECOMMERCE_TEMPLATES + SOCKS_ECOMMERCE_TEMPLATES + BOTTOMS_ECOMMERCE_TEMPLATES + UNDERWEAR_ECOMMERCE_TEMPLATES
}

# Family packs are explicit compositions. The numeric suffix identifies the
# supplied preview asset; it must never be used to select a prompt primitive.
# Each entry below is reviewed against the asset inventory in
# docs/tops-template-inventory.md.
_TOPS_FAMILY_COMPOSITIONS: Final[dict[str, tuple[str, ...]]] = {
    "shirts": ("seated_model", "front_model", "folded", "flat_product", "front_model", "seated_model", "construction_detail", "fabric_detail", "front_mannequin", "construction_detail", "construction_detail", "angled_model", "angled_product", "rear_product", "rear_model"),
    "t-shirts-casual-tops": ("front_mannequin", "hem_detail", "folded", "front_model", "angled_product", "rear_model", "flat_product", "rear_product", "fabric_detail", "rear_model"),
    "sleeveless-tops": ("rear_model", "front_model", "angled_product", "front_mannequin", "angled_mannequin", "flat_product", "styled_model"),
    "knitwear": ("folded", "neckline_detail", "front_model", "flat_product", "rear_angled_model", "fabric_detail", "seated_model", "flat_product", "rear_mannequin", "front_mannequin", "styled_model"),
    "hoodies": ("flat_product", "front_mannequin", "rear_mannequin", "angled_mannequin", "front_model", "rear_model", "angled_model", "rear_action", "front_action", "front_model", "seated_angled_model", "full_length_model"),
}

_TOPS_FAMILY_PROFILE_BASES: Final[dict[str, str]] = {
    "folded": "ecommerce-tops-folded-view",
    "flat_product": "ecommerce-tops-front-view",
    "front_product": "ecommerce-tops-front-view",
    "front_mannequin": "ecommerce-tops-front-view",
    "rear_product": "ecommerce-tops-back",
    "rear_mannequin": "ecommerce-tops-back",
    "front_model": "ecommerce-tops-front-model",
    "styled_model": "ecommerce-tops-front-model",
    "seated_model": "ecommerce-tops-full-body-model",
    "seated_angled_model": "ecommerce-tops-side-angle-model",
    "full_length_model": "ecommerce-tops-full-body-model",
    "rear_model": "ecommerce-tops-back-model",
    "rear_angled_model": "ecommerce-tops-back-model",
    "angled_model": "ecommerce-tops-side-angle-model",
    "angled_product": "ecommerce-tops-front-view",
    "angled_mannequin": "ecommerce-tops-front-view",
    "front_action": "ecommerce-tops-front-model",
    "rear_action": "ecommerce-tops-back-model",
    "construction_detail": "ecommerce-tops-close-up",
    "hem_detail": "ecommerce-tops-close-up",
    "neckline_detail": "ecommerce-tops-close-up",
    "fabric_detail": "ecommerce-tops-fabric",
}

_TOPS_FAMILY_NAMES: Final[dict[str, tuple[str, ...]]] = {
    "shirts": ("Seated Lifestyle", "Styled Front Model", "Folded Shirt", "Flat-Lay Shirt", "Front Model", "Seated Model", "Cuff Detail", "Fabric Texture Detail", "Front Invisible Mannequin", "Collar & Button Placket Detail", "Cuff Adjustment Detail", "Side / Three-Quarter Model", "Side / Three-Quarter Product", "Rear Product", "Rear Model"),
    "t-shirts-casual-tops": ("Front Invisible Mannequin", "Hem & Fit Detail", "Folded T-Shirt", "Front Model", "Side / Three-Quarter Product", "Rear Model", "Front Product", "Rear Product", "Fabric Texture Detail", "Rear Model"),
    "sleeveless-tops": ("Rear Model", "Front Model", "Three-Quarter Product", "Front Invisible Mannequin", "Three-Quarter Invisible Mannequin", "Front Product", "Styled Model"),
    "knitwear": ("Folded Knitwear", "Neckline Detail", "Front Model", "Front Product", "Rear Three-Quarter Model", "Knit Fabric Detail", "Seated Styled Model", "Flat-Lay Knitwear", "Rear Invisible Mannequin", "Front Invisible Mannequin", "Styled Model"),
    "hoodies": ("Flat Product", "Front Invisible Mannequin", "Rear Invisible Mannequin", "Three-Quarter Invisible Mannequin", "Front Model", "Rear Model", "Three-Quarter Model", "Rear Model Adjusting Hood", "Front Model Adjusting Hood", "Model with Hands in Pockets", "Seated Three-Quarter Model", "Full-Length Model"),
}

_TOPS_FAMILY_PROFILE_INSTRUCTIONS: Final[dict[str, str]] = {
    "folded": "Present the top neatly folded as a product-only ecommerce image. Arrange the fold so the visible colour, material, neckline or collar and distinctive construction remain clear.",
    "flat_product": "Present the complete top as a product-only studio image, front-facing and fully visible from neckline to hem. Do not show a person, mannequin or body.",
    "front_product": "Present the complete front of the top as a product-only studio image. Keep the full silhouette, neckline, sleeves and hem visible.",
    "front_mannequin": "Present the complete front of the top on an invisible or headless mannequin. Keep the garment's silhouette and construction clear; do not show a face or visible body.",
    "rear_product": "Present the complete rear of the top as a product-only studio image. Keep the back silhouette, shoulders, sleeves and hem fully visible.",
    "rear_mannequin": "Present the complete rear of the top on an invisible or headless mannequin. Do not show a face or visible body.",
    "front_model": "Show the top worn by a model in a simple front-facing studio presentation, cropped below the face. Keep styling minimal and make the garment fit, neckline, sleeves and hem clear.",
    "styled_model": "Show the top worn by a minimally styled model with the face excluded. Keep the garment as the visual subject and preserve its complete visible silhouette.",
    "seated_model": "Show the top worn by a seated model with the face excluded. Keep the pose simple and ensure the garment's neckline, silhouette, sleeves and visible length remain clear.",
    "seated_angled_model": "Show the top worn by a seated model from a three-quarter angle, with the face excluded. Keep styling minimal and make the garment's depth and fit clear.",
    "full_length_model": "Show the top worn by a model in a full-length composition, excluding the face. Keep the entire garment visible and styling minimal.",
    "rear_model": "Show the top worn by a model from the rear, cropped to exclude the face. Clearly show the back, shoulders, sleeves and hem.",
    "rear_angled_model": "Show the top worn by a model from a rear three-quarter angle, excluding the face. Clearly show the back construction, shoulder shape and drape.",
    "angled_model": "Show the top worn by a model from a side or three-quarter angle, cropped below the face. Make the garment's depth, silhouette and fit clear.",
    "angled_product": "Present the complete top as a product-only side or three-quarter studio view. Keep the silhouette, neckline, sleeves and hem visible.",
    "angled_mannequin": "Present the top on a headless or invisible mannequin from a three-quarter angle. Keep the garment's construction and silhouette clear without showing a face.",
    "front_action": "Show the top worn by a model from the front, cropped below the face, while the model naturally adjusts the hood. Keep the garment unobscured and preserve the hood construction.",
    "rear_action": "Show the top worn by a model from the rear, excluding the face, while the model naturally adjusts the hood. Keep the back and hood construction visible.",
    "construction_detail": "Create a tight ecommerce detail of the visible construction feature shown by the template, such as a cuff, collar, placket or fastening. Do not invent a feature.",
    "hem_detail": "Create a close ecommerce detail showing the top's hem, fit and lower construction on the product or a model cropped to exclude the face. Do not lose the product identity.",
    "neckline_detail": "Create a tight ecommerce detail of the neckline and surrounding knit or construction. Preserve the exact shape, material and visible texture.",
    "fabric_detail": "Create a macro ecommerce detail of the actual fabric or knit texture. Preserve the product's true colour, weave, thickness and surface finish.",
}


_TOPS_FAMILY_WORN_PROFILES: Final[frozenset[str]] = frozenset({
    "front_model", "styled_model", "seated_model", "seated_angled_model",
    "full_length_model", "rear_model", "rear_angled_model", "angled_model",
    "front_action", "rear_action",
})
_TOPS_FAMILY_DETAIL_PROFILES: Final[frozenset[str]] = frozenset({
    "construction_detail", "hem_detail", "neckline_detail", "fabric_detail",
})
_TOPS_FAMILY_REAR_PROFILES: Final[frozenset[str]] = frozenset({
    "rear_product", "rear_mannequin", "rear_model", "rear_angled_model", "rear_action",
})
_TOPS_FAMILY_ANGLED_PROFILES: Final[frozenset[str]] = frozenset({
    "seated_angled_model", "rear_angled_model", "angled_model", "angled_product", "angled_mannequin",
})


def _tops_family_template(family: str, index: int, profile: str) -> GenerationTemplate:
    base = _BASE_TEMPLATES[_TOPS_FAMILY_PROFILE_BASES[profile]]
    artwork_surface_mode = (
        "detail" if profile in _TOPS_FAMILY_DETAIL_PROFILES
        else "folded" if profile == "folded"
        else "rear" if profile in _TOPS_FAMILY_REAR_PROFILES
        else "angled" if profile in _TOPS_FAMILY_ANGLED_PROFILES
        else "worn" if profile in _TOPS_FAMILY_WORN_PROFILES
        else "flat"
    )
    return replace(
        base,
        id=f"ecommerce-tops-{family}-{index + 1:02d}",
        name=_TOPS_FAMILY_NAMES[family][index],
        description=f"Family-specific Ecommerce presentation for {family.replace('-', ' ')} ({profile.replace('_', ' ')}).",
        prompt_instructions=_TOPS_FAMILY_PROFILE_INSTRUCTIONS[profile],
        applicable_families=(family,),
        output_presentation="worn_product" if profile in _TOPS_FAMILY_WORN_PROFILES else "product_only",
        artwork_surface_mode=artwork_surface_mode,
        required_evidence=("rear_view",) if profile in _TOPS_FAMILY_REAR_PROFILES else ("front_view",),
    )


_TOPS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    template.id: template
    for family, profiles in _TOPS_FAMILY_COMPOSITIONS.items()
    for index, profile in enumerate(profiles)
    for template in (_tops_family_template(family, index, profile),)
}
_TEMPLATES: Final[dict[str, GenerationTemplate]] = {**_BASE_TEMPLATES, **_TOPS_FAMILY_TEMPLATES}
_LEGACY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {TOPS_CLEAN_PRODUCT_SHOT.id: TOPS_CLEAN_PRODUCT_SHOT}


def get_generation_template(template_id: str) -> GenerationTemplate | None:
    """Return a template by its stable ID, or ``None`` when it is unknown."""
    return _TEMPLATES.get(template_id) or _LEGACY_TEMPLATES.get(template_id)


def validate_generation_template(template_id: str, *, category: str, channel: str, subtype: str | None = None, product_family: str | None = None) -> GenerationTemplate:
    """Load a template and ensure it is valid for the requested product."""
    template = get_generation_template(template_id)
    if template is None:
        raise ValueError(f"Unknown generation template: {template_id}")
    if template.category != category.strip().lower():
        raise ValueError(f"Template {template_id} is not available for category {category}")
    if template.channel != channel.strip().lower():
        raise ValueError(f"Template {template_id} is not available for channel {channel}")
    if template.applicable_families:
        # Bottoms templates are shared composition primitives, so an unknown
        # bottoms family may use the conservative generic policy. A known
        # family must still be one explicitly supported by the template.
        unknown_bottoms_family = template.category == "bottoms" and product_family is None
        if not unknown_bottoms_family and product_family not in template.applicable_families:
            raise ValueError(f"Template {template_id} is not available for product family {product_family or 'unclassified'}")
    # applicable_subtypes documents the taxonomy examples a template was
    # designed around; it is not a binary allow-list. Recognition strings are
    # descriptive and may contain new or qualified product types. Category and
    # channel remain the hard compatibility gates, while subtype is retained
    # for prompt context and future non-blocking ranking.
    return template


def list_generation_templates(*, category: str | None = None, channel: str | None = None, subtype: str | None = None, product_family: str | None = None) -> list[GenerationTemplate]:
    """List active templates, optionally filtered by category, channel, and family."""
    templates = list(_TEMPLATES.values())
    if category is not None:
        templates = [template for template in templates if template.category == category.strip().lower()]
    if channel is not None:
        templates = [template for template in templates if template.channel == channel.strip().lower()]
    if product_family is not None:
        family = product_family.strip().lower()
        # Once a family is known, expose only the locked family pack. Generic
        # category templates remain available when family is unconfirmed.
        templates = [template for template in templates if template.applicable_families and family in template.applicable_families]
    # subtype is intentionally not used to hide templates; it is descriptive
    # context for prompt compilation and future ranking.
    return templates
