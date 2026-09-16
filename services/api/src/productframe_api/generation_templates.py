"""Backend-owned image generation templates.

The frontend may display template choices, but generation behaviour must come from
this backend registry. Template IDs are stable because they are stored on
generation jobs and generated assets.
"""
from dataclasses import dataclass, replace
from typing import Final, Literal


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
    # Explicit presentation contract used by the structured prompt compiler.
    # Empty values preserve compatibility with legacy category templates.
    presentation_mode: Literal["", "model", "mannequin", "invisible_mannequin", "garment"] = ""
    output_details: str = ""
    presentation_negative_prompt: str = ""
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
    "When a template specifies an invisible mannequin, the mannequin must be fully invisible; a visible torso is a headless mannequin and is not interchangeable with an invisible mannequin.",
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
    "another product. Do not invent hidden details. Do not create a collage, grid, "
    "split-screen, montage, inset, duplicate view or multiple panels; output one "
    "single photograph only."
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
        instructions=(
            "Create ONE single-frame photorealistic macro ecommerce photograph of the "
            "actual top fabric. Fill the entire frame with one continuous area of the "
            "material, showing its true knit or weave, fibre scale, thickness, surface "
            "finish and colour from the product reference. Use a tight close-up with "
            "shallow natural depth of field; do not show the full t-shirt, model, "
            "mannequin, garment layout or separate fabric samples. This is a material "
            "texture photograph, not a presentation board or set of views."
        ),
        required=("global_details.materials", "global_details.colour"),
        artwork_visibility="conditional",
        artwork_surface_mode="detail",
    ),
)

# Category-specific ecommerce templates mirrored by the frontend recipe choices.
# Their text controls presentation only; product identity always comes from the
# product reference images and category schema.
def _support_required_evidence(category: str, template_id: str) -> tuple[str, ...]:
    if category != "footwear":
        return ()
    if "sole" in template_id:
        return ("sole_or_underside",)
    if "rear" in template_id:
        return ("rear_view",)
    if "top" in template_id:
        return ("top_view",)
    if any(token in template_id for token in ("outer-side", "inner-side", "three-quarter", "side-on-feet")):
        return ("side_view",)
    return ("front_view",)


_FOOTWEAR_COMMON_PRESENTATION = (
    "Create one finished ecommerce photograph, not a design board or contact sheet. "
    "Use the supplied product reference image as the sole authority for the footwear's "
    "identity, colour, material, construction, proportions and visible details. "
    "Preserve the exact product while changing only the requested viewpoint and presentation. "
    "Use a clean warm-white or very light neutral studio background, soft diffuse directional "
    "lighting, realistic contact shadow and restrained product-photography styling. Keep the "
    "footwear as the only subject and make it large, sharp and clearly readable in the frame. "
    "Do not add props, labels, logos, extra footwear or invented construction. "
    "Output one continuous full-frame photograph only: no collage, grid, split screen, montage, "
    "contact sheet, inset, panel, duplicate product or alternate views."
)


def _support_template(category: str, template_id: str, name: str, description: str, instruction: str, subtypes: tuple[str, ...]) -> GenerationTemplate:
    if category == "footwear":
        instruction = _FOOTWEAR_COMMON_PRESENTATION + " " + instruction
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
            + (
                " Output exactly one single-frame photograph only. Do not create "
                "multiple images, collages, grids, split screens, montages, "
                "contact sheets, insets, panels or multiple views in one output."
                if category == "footwear" else ""
            )
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
        required_evidence=_support_required_evidence(category, template_id),
    )

_OUTERWEAR_SUBTYPES = ("coat", "jacket", "blazer", "waistcoat", "parka", "gilet", "bomber", "trench coat", "raincoat", "puffer", "hoodie", "sweatshirt", "fleece")
_FOOTWEAR_SUBTYPES = ("shoes", "heels", "trainers", "sandals", "crocs", "boots", "ankle boots", "knee-high boots", "tall boots", "heeled boots", "loafers", "flats", "sliders", "mules", "clogs", "formal shoes")
_SOCKS_SUBTYPES = ("normal", "running", "ankle", "trainer", "crew", "knee-high", "stockings", "compression", "thermal")
_BOTTOMS_SUBTYPES = ("shorts", "skirt", "leggings", "trousers", "jeans", "cargo trousers", "joggers", "chinos")
_BOTTOMS_FAMILIES = ("structured_bottoms",)

BOTTOMS_FAMILY_POLICIES: Final[dict[str, str]] = {
    "structured_bottoms": (
        "Preserve the waistband, rise, closure, belt loops, pockets, pleats, darts, "
        "panels, leg shape, leg width and hem when visible. For construction details, "
        "prioritise the most distinctive supported pocket, panel, seam, closure or "
        "fastening; do not assume five-pocket denim construction."
    ),
    "shorts": (
        "Preserve the waistband, rise, leg opening, inseam length, pockets, closure, "
        "panels and hem of the shorts. Do not extend them into trousers or assume "
        "a specific cargo, denim or tailored construction unless visible. Whenever "
        "a Shorts template includes a model, the model must wear a plain grey "
        "crew-neck T-shirt covering the torso; never render the model shirtless or "
        "with an exposed bare upper body."
    ),
    "casual_bottoms": (
        "Preserve elastic waistbands, drawcords, soft or stretch fabric, relaxed or "
        "tapered legs, ribbed cuffs and visible pockets or panels. Do not introduce "
        "belt loops, a rigid denim surface, a tailored crease, cargo pockets, a "
        "trouser fly or a different cuff construction unless visible."
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
    )
)

# Jackets is the first Outerwear family with a reviewed benchmark pack.
_JACKETS_TEMPLATE_REFERENCE_PATHS: Final[tuple[str, ...]] = (
    'apps/web/public/output-examples/outerwear/01-front-close.png',
    'apps/web/public/output-examples/outerwear/02-front-medium.png',
    'apps/web/public/output-examples/outerwear/03-over-the-shoulder-no-face.png',
    'apps/web/public/output-examples/outerwear/04-full-body-model-no-face.png',
    'apps/web/public/output-examples/outerwear/05-construction-close-up.png',
    'apps/web/public/output-examples/outerwear/06-back-product.png',
    'apps/web/public/output-examples/outerwear/07-front-model-no-face.png',
    'apps/web/public/output-examples/outerwear/08-back-model-no-face.png',
    'apps/web/public/output-examples/outerwear/09-side-angle-model-no-face.png',
)

_JACKETS_PRESENTATION_MODES: Final[tuple[str, ...]] = ('garment', 'garment', 'model', 'model', 'garment', 'garment', 'model', 'model', 'model')
_JACKETS_REQUIRED_EVIDENCE: Final[tuple[tuple[str, ...], ...]] = (('front_view',), ('front_view',), ('rear_view',), ('front_view',), ('front_view',), ('rear_view',), ('front_view',), ('rear_view',), ('side_view',))
_JACKETS_OUTPUT_DETAILS: Final[tuple[str, ...]] = (
    "- Subject: Upper front of uploaded outerwear. - Presentation: Product-only collar/front opening detail, without a person or support. - Camera angle: Straight-on close view. - View orientation: Front. - Framing: Collar and upper torso. - Crop: Sides and lower body intentionally clipped; no hem or cuffs. - Product position: Collar centred above front opening. - Product scale: Detail fills frame. - Silhouette: Actual collar and upper-front outline. - Visible construction: Actual neckline, front edges, nearby seams and fastenings only. - Garment volume: Natural material thickness and folds. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One product detail, no accessories. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text.",
    "- Subject: Complete uploaded outerwear. - Presentation: Upright product-only front; sleeves lowered, front opening arranged naturally. - Camera angle: Straight-on. - View orientation: Front. - Framing: Whole garment. - Crop: Include both cuffs, collar and hem. - Product position: Centred vertically. - Product scale: Large with modest margins. - Silhouette: Preserve actual length and sleeve/body proportions. - Visible construction: Actual front construction, pockets and closures where present. - Garment volume: Gentle supported shape without a visible body. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One garment, no model, hanger or stand. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text.",
    "- Subject: Upper rear shoulder of uploaded outerwear while worn. - Presentation: Adult model turned away; near shoulder foregrounded. - Camera angle: Close rear three-quarter. - View orientation: Rear-oblique. - Framing: Neck base, collar, shoulder and upper back. - Crop: Exclude face, hands, cuffs and hem. - Product position: Near shoulder at image left, back extending right. - Product scale: Shoulder detail fills frame. - Silhouette: Actual shoulder contour. - Visible construction: Actual collar, shoulder seam and upper-back panel boundaries. - Garment volume: Natural worn shoulder curvature. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One worn shoulder detail, not a full rear shot. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text.",
    "- Subject: Uploaded outerwear worn in a complete outfit. - Presentation: Standing adult, arms relaxed; restrained light underlayer, dark trousers and boots. - Camera angle: Level front view. - View orientation: Front. - Framing: Neck base through complete feet. - Crop: Exclude face/head; retain shoes and floor margin. - Product position: Centred upright figure. - Product scale: Whole outfit fits with narrow border. - Silhouette: Actual garment length relative to body. - Visible construction: Actual garment construction; opening may reveal underlayer only if supported. - Garment volume: Natural standing fit. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One model; supporting clothes secondary, no props. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text.",
    "- Subject: A visible construction detail of uploaded outerwear. - Presentation: Product-only macro of an actual seam/edge/fastening junction. - Camera angle: Close oblique macro. - View orientation: Local front construction detail. - Framing: Small connected construction region. - Crop: Garment extends beyond all edges. - Product position: Detail junction centred with diagonal edges. - Product scale: Stitching and real surface enlarged, not invented. - Silhouette: Local edges only. - Visible construction: Use an existing detail; benchmark snap/lapel/zipper is not mandatory. - Garment volume: Actual edge thickness and surface relief. - Background: No exposed background; the product detail fills the frame. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One continuous macro, no background or inset. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text.",
    "- Subject: Complete rear of uploaded outerwear. - Presentation: Upright product-only rear, sleeves down. - Camera angle: Straight-on. - View orientation: Rear. - Framing: Whole garment. - Crop: Keep collar, sleeves and hem inside frame. - Product position: Centred vertical. - Product scale: Large with modest border. - Silhouette: Actual rear silhouette. - Visible construction: Actual back seams/panels and hem; do not invent benchmark centre seam. - Garment volume: Natural supported volume. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One garment without person or visible support. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text.",
    "- Subject: Uploaded outerwear on adult model. - Presentation: Standing, arms relaxed; light underlayer and dark trousers. - Camera angle: Torso-height straight-on. - View orientation: Front. - Framing: Base of neck through upper thighs. - Crop: Exclude face and feet; retain both hands and garment hem. - Product position: Torso centred. - Product scale: Garment dominates. - Silhouette: Actual worn fit. - Visible construction: Actual front seams, closure, cuffs and hem. - Garment volume: Natural elbow and torso folds. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One model, restrained styling. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text.",
    "- Subject: Rear of uploaded outerwear on adult model. - Presentation: Standing away with arms relaxed beside hips. - Camera angle: Torso-height straight-on. - View orientation: Rear. - Framing: Nape to upper thighs. - Crop: No head/face or feet; retain hands and hem. - Product position: Back centred. - Product scale: Garment dominates. - Silhouette: Actual worn rear fit. - Visible construction: Actual rear construction, sleeve seams and hem. - Garment volume: Natural back and sleeve drape. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One model in dark trousers. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text.",
    "- Subject: Uploaded outerwear on adult model. - Presentation: Standing at shallow angle with both arms lowered. - Camera angle: Torso-height front three-quarter. - View orientation: Front-oblique, not rear. - Framing: Neck base through upper thighs. - Crop: Face and feet excluded; hands and hem visible. - Product position: Near side foregrounded, torso centred. - Product scale: Garment fills most of frame. - Silhouette: Actual depth and side silhouette. - Visible construction: Actual front, near side, sleeve and collar construction. - Garment volume: Natural worn folds. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One model with simple underlayer and dark trousers. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text.",
)

_JACKETS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    template.id: template
    for index, base in enumerate(OUTERWEAR_ECOMMERCE_TEMPLATES)
    for template in (replace(
        base,
        applicable_families=("jackets",),
        reference_object_key=_JACKETS_TEMPLATE_REFERENCE_PATHS[index],
        presentation_mode=_JACKETS_PRESENTATION_MODES[index],
        output_presentation="worn_product" if _JACKETS_PRESENTATION_MODES[index] == "model" else "product_only",
        output_details=_JACKETS_OUTPUT_DETAILS[index],
        required_evidence=_JACKETS_REQUIRED_EVIDENCE[index],
        version=2,
    ),)
}


# Coats is a reviewed Outerwear family with its own benchmark pack.
_COATS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    'ecommerce-outerwear-coats-01': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[0], id='ecommerce-outerwear-coats-01', name='Front Product', applicable_families=("coats",), reference_object_key='docs/coats-output-details/references/01_front_product.png', presentation_mode='invisible_mannequin', output_presentation='product_only', output_details="- Subject: Uploaded coat, using the `invisible_mannequin` presentation defined above. - Camera angle and orientation: Front, straight-on at garment mid-height. - Framing and crop: Whole coat, collar through hem and both cuffs, with modest margins. - Product position and pose: Centred upright coat with sleeves lowered and slightly separated from body. - Product scale: Match the benchmark framing while preserving actual garment/body proportions. - Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape. - Visible construction: Front closure, collar/lapels, chest and hip pockets where present. - Garment volume: Gentle shoulder/chest volume and hollow neck opening; no visible support. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no location scenery or unrelated props. - Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening. - Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat. - Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery. - Secondary styling: No person, skin, underlayer, trousers, footwear, hanger or visible support. - Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.", required_evidence=('front_view',), version=2),
    'ecommerce-outerwear-coats-02': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[1], id='ecommerce-outerwear-coats-02', name='Collar and Lapel Detail', applicable_families=("coats",), reference_object_key='docs/coats-output-details/references/02_collar_detail.png', presentation_mode='invisible_mannequin', output_presentation='product_only', output_details="- Subject: Uploaded coat, using the `invisible_mannequin` presentation defined above. - Camera angle and orientation: Straight-on front close-up. - Framing and crop: Collar, shoulder roots and upper front; sleeves and lower coat clipped. Benchmark includes top buttons and partially clipped lower buttons/pocket edges. - Product position and pose: Neck opening centred high in frame; lapel overlap extends diagonally downward. - Product scale: Local detail fills the frame at the benchmark scale. - Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape. - Visible construction: Actual neckline, lapels, front edge, nearby buttons and chest pocket only where present. - Garment volume: Natural collar roll and edge thickness, softly shaped upper chest. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no location scenery or unrelated props. - Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening. - Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat. - Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery. - Secondary styling: No person, skin, underlayer, trousers, footwear, hanger or visible support. - Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.", required_evidence=('front_view',), version=2),
    'ecommerce-outerwear-coats-03': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[2], id='ecommerce-outerwear-coats-03', name='Rear Shoulder Detail — No Face', applicable_families=("coats",), reference_object_key='docs/coats-output-details/references/03_rear_shoulder_detail.png', presentation_mode='model', output_presentation='worn_product', output_details="- Subject: Uploaded coat, using the `model` presentation defined above. - Camera angle and orientation: Close rear three-quarter, near shoulder at image left. - Framing and crop: Nape, collar, shoulder and upper back fill frame; exclude face, hands, cuffs and hem. - Product position and pose: Shoulder curves across left foreground; back extends to right edge. - Product scale: Local detail fills the frame at the benchmark scale. - Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape. - Visible construction: Actual rear collar, shoulder seams and upper-back construction. - Garment volume: Natural worn shoulder curvature and upper-sleeve drape. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no location scenery or unrelated props. - Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening. - Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat. - Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery. - Secondary styling: Use a restrained light neutral underlayer and simple trousers; where shoes are in frame, use understated footwear consistent with the selected styling. Match framing and pose, not benchmark model identity. Hands stay outside pockets. - Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.", required_evidence=('rear_view',), version=2),
    'ecommerce-outerwear-coats-04': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[3], id='ecommerce-outerwear-coats-04', name='Model Front Facing — Full Length', applicable_families=("coats",), reference_object_key='docs/coats-output-details/references/04_front_model_full_length.png', presentation_mode='model', output_presentation='worn_product', output_details="- Subject: Uploaded coat, using the `model` presentation defined above. - Camera angle and orientation: Level straight-on front view; avoid wide-angle distortion. - Framing and crop: Base of neck through complete shoes, with floor margin. Entire coat hem and hands visible; face excluded. - Product position and pose: Centred standing adult, arms down, hands outside pockets, feet naturally apart. - Product scale: Match the benchmark framing while preserving actual garment/body proportions. - Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape. - Visible construction: Actual collar, closures, pockets, sleeves, cuffs and full hem. - Garment volume: Natural standing fit; coat closed using its actual fastening construction. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no location scenery or unrelated props. - Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening. - Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat. - Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery. - Secondary styling: Use a restrained light neutral underlayer and simple trousers; where shoes are in frame, use understated footwear consistent with the selected styling. Match framing and pose, not benchmark model identity. Hands stay outside pockets. - Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.", required_evidence=('front_view',), version=2),
    'ecommerce-outerwear-coats-05': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[4], id='ecommerce-outerwear-coats-05', name='Fabric and Edge Detail', applicable_families=("coats",), reference_object_key='docs/coats-output-details/references/05_fabric_detail.png', presentation_mode='garment', output_presentation='product_only', output_details="- Subject: Uploaded coat, using the `garment` presentation defined above. - Camera angle and orientation: Very close oblique macro of a supported fabric edge. - Framing and crop: Fabric fills every edge of frame; no whole garment, model or backdrop visible. - Product position and pose: Folded edge corner occupies upper-left/centre, with another diagonal edge at right. - Product scale: Local detail fills the frame at the benchmark scale. - Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape. - Visible construction: Existing edge finish, stitching and surface texture only where supported by source detail. - Garment volume: Local fabric thickness, edge relief and soft contact shadow; no inflated volume. - Background: No exposed background; the material fills the frame. - Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening. - Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat. - Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery. - Secondary styling: No person, skin, underlayer, trousers, footwear, hanger or visible support. - Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.", required_evidence=('detail',), version=2),
    'ecommerce-outerwear-coats-06': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[5], id='ecommerce-outerwear-coats-06', name='Rear Product', applicable_families=("coats",), reference_object_key='docs/coats-output-details/references/06_rear_product.png', presentation_mode='invisible_mannequin', output_presentation='product_only', output_details="- Subject: Uploaded coat, using the `invisible_mannequin` presentation defined above. - Camera angle and orientation: Straight-on rear view at garment mid-height. - Framing and crop: Complete coat with collar, both cuffs and hem inside frame. - Product position and pose: Centred upright rear silhouette, sleeves lowered with slim gaps. - Product scale: Match the benchmark framing while preserving actual garment/body proportions. - Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape. - Visible construction: Actual back panels, seams, vents and sleeve construction where evidenced. - Garment volume: Softly supported back and shoulder volume with no visible mannequin. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no location scenery or unrelated props. - Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening. - Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat. - Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery. - Secondary styling: No person, skin, underlayer, trousers, footwear, hanger or visible support. - Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.", required_evidence=('rear_view',), version=2),
    'ecommerce-outerwear-coats-07': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[6], id='ecommerce-outerwear-coats-07', name='Model Front Facing — Cropped', applicable_families=("coats",), reference_object_key='docs/coats-output-details/references/07_front_model_cropped.png', presentation_mode='model', output_presentation='worn_product', output_details="- Subject: Uploaded coat, using the `model` presentation defined above. - Camera angle and orientation: Straight-on front at torso height. - Framing and crop: Base of neck through hands and lower torso; coat continues beyond bottom edge. Exclude face, feet and hem. - Product position and pose: Centred torso, arms relaxed down, hands visible outside pockets. - Product scale: Match the benchmark framing while preserving actual garment/body proportions. - Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape. - Visible construction: Actual front closure, collar, pockets and cuffs within crop. - Garment volume: Natural closed-coat fit with subtle elbow and torso folds. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no location scenery or unrelated props. - Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening. - Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat. - Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery. - Secondary styling: Use a restrained light neutral underlayer and simple trousers; where shoes are in frame, use understated footwear consistent with the selected styling. Match framing and pose, not benchmark model identity. Hands stay outside pockets. - Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.", required_evidence=('front_view',), version=2),
    'ecommerce-outerwear-coats-08': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[7], id='ecommerce-outerwear-coats-08', name='Model Rear — Cropped', applicable_families=("coats",), reference_object_key='docs/coats-output-details/references/08_rear_model.png', presentation_mode='model', output_presentation='worn_product', output_details="- Subject: Uploaded coat, using the `model` presentation defined above. - Camera angle and orientation: Straight-on rear at torso height. - Framing and crop: Nape through hands and upper vent area; lower coat and hem continue below frame. No face or feet. - Product position and pose: Centred back, shoulders level, arms relaxed down with hands visible. - Product scale: Match the benchmark framing while preserving actual garment/body proportions. - Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape. - Visible construction: Actual rear collar, seams, vent section and cuffs within crop. - Garment volume: Natural worn back drape and sleeve curvature. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no location scenery or unrelated props. - Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening. - Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat. - Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery. - Secondary styling: Use a restrained light neutral underlayer and simple trousers; where shoes are in frame, use understated footwear consistent with the selected styling. Match framing and pose, not benchmark model identity. Hands stay outside pockets. - Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.", required_evidence=('rear_view',), version=2),
    'ecommerce-outerwear-coats-09': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[8], id='ecommerce-outerwear-coats-09', name='Model Front Three-Quarter — Cropped', applicable_families=("coats",), reference_object_key='docs/coats-output-details/references/09_three_quarter_model.png', presentation_mode='model', output_presentation='worn_product', output_details="- Subject: Uploaded coat, using the `model` presentation defined above. - Camera angle and orientation: Front three-quarter, near shoulder and sleeve at image right; model turns slightly toward image left. - Framing and crop: Neck base through both hands; lower coat exits bottom edge, face and feet excluded. - Product position and pose: Torso centred with near side foregrounded, both arms down and hands outside pockets. - Product scale: Match the benchmark framing while preserving actual garment/body proportions. - Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape. - Visible construction: Actual front and near-side collar, fastenings, pockets and sleeve details. - Garment volume: Natural worn depth through shoulder, chest and near sleeve, no exaggerated twist. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no location scenery or unrelated props. - Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening. - Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat. - Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery. - Secondary styling: Use a restrained light neutral underlayer and simple trousers; where shoes are in frame, use understated footwear consistent with the selected styling. Match framing and pose, not benchmark model identity. Hands stay outside pockets. - Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.", required_evidence=('front_view', 'side_view'), version=2),
    'ecommerce-outerwear-coats-10': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[8], id='ecommerce-outerwear-coats-10', name='Front Invisible Mannequin', applicable_families=("coats",), reference_object_key='docs/coats-output-details/references/10_front_invisible_mannequin.png', presentation_mode='invisible_mannequin', output_presentation='product_only', output_details="- Subject: Uploaded coat, using the `invisible_mannequin` presentation defined above. - Camera angle and orientation: Direct straight-on front at garment mid-height. - Framing and crop: Entire collar, coat body, cuffs and hem visible with slim balanced margins. - Product position and pose: Centred vertical coat, arms hanging naturally with narrow separation. - Product scale: Match the benchmark framing while preserving actual garment/body proportions. - Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape. - Visible construction: Actual closed front, neckline, pockets, fastening arrangement and hem. - Garment volume: Clear three-dimensional chest and shoulder shape, hollow neck and cuffs, entirely invisible support. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no location scenery or unrelated props. - Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening. - Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat. - Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery. - Secondary styling: No person, skin, underlayer, trousers, footwear, hanger or visible support. - Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.", required_evidence=('front_view',), version=2),
    'ecommerce-outerwear-coats-11': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[8], id='ecommerce-outerwear-coats-11', name='Front Flat Lay — Overhead', applicable_families=("coats",), reference_object_key='docs/coats-output-details/references/11_front_flat_lay_overhead.png', presentation_mode='garment', output_presentation='product_only', output_details="- Subject: Uploaded coat, using the `garment` presentation defined above. - Camera angle and orientation: Camera directly overhead, sensor parallel to the horizontal surface, no perspective tilt. - Framing and crop: Whole coat from collar to hem and both cuffs, with clear surrounding surface. - Product position and pose: Front faces upward, closed and centred; sleeves arranged alongside body with small natural gaps. - Product scale: Match the benchmark framing while preserving actual garment/body proportions. - Silhouette: Preserve the uploaded coat's outline and fit within this crop; do not turn another coat into the benchmark's tailored double-breasted shape. - Visible construction: Actual front closure, pockets, lapels, seams and cuffs. - Garment volume: Coat lies on surface with flattened volume, modest folds and close contact shadows; no mannequin chest shape or floating hem. - Background: Light warm beige seamless studio surface, approximately #C8C1B6; no location scenery or unrelated props. - Lighting: Soft diffused directional studio light with gentle shadows; preserve real material sheen and surface relief. No hard flash, dramatic colour gels or exaggerated sharpening. - Colour treatment: Preserve source product colour and tonal variation. Do not copy the benchmark camel colour or introduce a beige cast into the coat. - Surface fidelity: Preserve evidenced texture scale. Several benchmark fronts show pronounced swirling surface detail; do not transfer this to a plain coat or invent fibres, ornament, weave or embroidery. - Secondary styling: No person, skin, underlayer, trousers, footwear, hanger or visible support. - Composition: One continuous portrait ecommerce photograph, approximately 4:5; one coat only. No collage, inset, duplicated view, added text, watermark or decorative accessories.", required_evidence=('front_view',), version=2),
}


# Gilets / Padded Vests is a reviewed Outerwear family with its own pack.
_GILETS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    'ecommerce-outerwear-gilets-padded-vests-01': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[0], id='ecommerce-outerwear-gilets-padded-vests-01', name='Front Product — Invisible Mannequin', applicable_families=("gilets-padded-vests",), reference_object_key='docs/gilets-output-details/references/01_front_product.png', presentation_mode='invisible_mannequin', output_presentation='product_only', output_details='- Subject: Uploaded gilet or padded vest, presented using `invisible_mannequin`. - Camera angle and orientation: Straight-on front, camera level with garment. - Framing and crop: Complete collar, both armholes and hem with balanced margins. - Product position and pose: Centred upright garment, front fastening closed to top as supported by its construction. - Product scale: Match benchmark occupancy while retaining actual garment proportions and the stated margins. - Silhouette: Preserve actual sleeveless outline, armhole depth, shoulder width, length and fit; never add sleeves or force a different gilet into this example silhouette. - Visible construction: Front closure, collar, armhole binding, panel seams and hem. - Garment volume: Softly shaped shoulders and chest, hollow neck and armholes; no visible body or support. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no lifestyle location, props or scenery. - Lighting: Soft diffused directional studio light and gentle shadows. Preserve actual finish and subtle highlights; no glossy plastic effect, hard flash or dramatic coloured lighting. - Colour treatment: Preserve source colours and tonal variation. Do not transfer navy from the benchmark or cast beige onto the product. - Surface fidelity: Retain real texture scale, stitching and padding relief. Do not multiply quilting channels, regularise uneven panels, invent microtexture or infer insulation material/performance from appearance. - Secondary styling: No model, skin, shirt, sleeves, trousers, hanger, stand or visible mannequin. - Output: One continuous portrait ecommerce photograph, approximately 4:5, showing one product. No collage, inset, duplicate views, added text or watermark.', required_evidence=('front_view',), version=2),
    'ecommerce-outerwear-gilets-padded-vests-02': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[1], id='ecommerce-outerwear-gilets-padded-vests-02', name='Collar and Fastening Detail', applicable_families=("gilets-padded-vests",), reference_object_key='docs/gilets-output-details/references/02_collar_detail.png', presentation_mode='invisible_mannequin', output_presentation='product_only', output_details='- Subject: Uploaded gilet or padded vest, presented using `invisible_mannequin`. - Camera angle and orientation: Close front view, slightly elevated to reveal inside neckline. - Framing and crop: Collar, shoulders and upper chest; lower torso and hem clipped, armhole edges partially visible at sides. - Product position and pose: Collar centred, upper fastening partially opened into a V; zipper pull below the opening in benchmark. - Product scale: Close detail fills the frame at the benchmark scale. - Silhouette: Preserve actual sleeveless outline, armhole depth, shoulder width, length and fit; never add sleeves or force a different gilet into this example silhouette. - Visible construction: Actual collar edge, zipper or other closure, nearby stitching, lining and upper panels. - Garment volume: Natural padded collar roll and upper-chest loft with visible interior; no person. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no lifestyle location, props or scenery. - Lighting: Soft diffused directional studio light and gentle shadows. Preserve actual finish and subtle highlights; no glossy plastic effect, hard flash or dramatic coloured lighting. - Colour treatment: Preserve source colours and tonal variation. Do not transfer navy from the benchmark or cast beige onto the product. - Surface fidelity: Retain real texture scale, stitching and padding relief. Do not multiply quilting channels, regularise uneven panels, invent microtexture or infer insulation material/performance from appearance. - Secondary styling: No model, skin, shirt, sleeves, trousers, hanger, stand or visible mannequin. - Output: One continuous portrait ecommerce photograph, approximately 4:5, showing one product. No collage, inset, duplicate views, added text or watermark.', required_evidence=('front_view', 'detail'), version=2),
    'ecommerce-outerwear-gilets-padded-vests-03': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[2], id='ecommerce-outerwear-gilets-padded-vests-03', name='Rear Shoulder Detail — No Face', applicable_families=("gilets-padded-vests",), reference_object_key='docs/gilets-output-details/references/03_rear_shoulder_detail.png', presentation_mode='model', output_presentation='worn_product', output_details='- Subject: Uploaded gilet or padded vest, presented using `model`. - Camera angle and orientation: Close rear three-quarter view, near shoulder at image left. - Framing and crop: Nape, back collar, shoulder, armhole and upper back fill frame; near underlayer sleeve and upper arm visible. Face, hands and hem excluded. - Product position and pose: Model faces away with near shoulder foregrounded; back extends to image right. - Product scale: Close detail fills the frame at the benchmark scale. - Silhouette: Preserve actual sleeveless outline, armhole depth, shoulder width, length and fit; never add sleeves or force a different gilet into this example silhouette. - Visible construction: Rear collar, shoulder/armhole finish and upper-back construction. - Garment volume: Natural shoulder curvature, padded back loft and slight gathers along actual seams. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no lifestyle location, props or scenery. - Lighting: Soft diffused directional studio light and gentle shadows. Preserve actual finish and subtle highlights; no glossy plastic effect, hard flash or dramatic coloured lighting. - Colour treatment: Preserve source colours and tonal variation. Do not transfer navy from the benchmark or cast beige onto the product. - Surface fidelity: Retain real texture scale, stitching and padding relief. Do not multiply quilting channels, regularise uneven panels, invent microtexture or infer insulation material/performance from appearance. - Secondary styling: Plain light neutral short-sleeved underlayer and simple dark trousers where visible; understated footwear only for full-length slot 04. Underlayer sleeves are separate garments, never gilet sleeves. Keep arms relaxed and hands outside pockets when visible; do not introduce hands into detail crops. - Output: One continuous portrait ecommerce photograph, approximately 4:5, showing one product. No collage, inset, duplicate views, added text or watermark.', required_evidence=('rear_view', 'side_view'), version=2),
    'ecommerce-outerwear-gilets-padded-vests-04': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[3], id='ecommerce-outerwear-gilets-padded-vests-04', name='Model Front Facing — Full Length', applicable_families=("gilets-padded-vests",), reference_object_key='docs/gilets-output-details/references/04_front_model_full_length.png', presentation_mode='model', output_presentation='worn_product', output_details='- Subject: Uploaded gilet or padded vest, presented using `model`. - Camera angle and orientation: Level straight-on front, natural perspective. - Framing and crop: Base of neck through complete footwear and floor margin; head/face excluded, hands and entire gilet visible. - Product position and pose: Standing adult centred, feet naturally apart, arms down and hands outside pockets. Fastened torso with upper collar slightly open. - Product scale: Match benchmark occupancy while retaining actual garment proportions and the stated margins. - Silhouette: Preserve actual sleeveless outline, armhole depth, shoulder width, length and fit; never add sleeves or force a different gilet into this example silhouette. - Visible construction: Front fastening, armholes, collar, panel seams and hem. - Garment volume: Natural worn fit and light compression where garment rests on torso. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no lifestyle location, props or scenery. - Lighting: Soft diffused directional studio light and gentle shadows. Preserve actual finish and subtle highlights; no glossy plastic effect, hard flash or dramatic coloured lighting. - Colour treatment: Preserve source colours and tonal variation. Do not transfer navy from the benchmark or cast beige onto the product. - Surface fidelity: Retain real texture scale, stitching and padding relief. Do not multiply quilting channels, regularise uneven panels, invent microtexture or infer insulation material/performance from appearance. - Secondary styling: Plain light neutral short-sleeved underlayer and simple dark trousers where visible; understated footwear only for full-length slot 04. Underlayer sleeves are separate garments, never gilet sleeves. Keep arms relaxed and hands outside pockets when visible; do not introduce hands into detail crops. - Output: One continuous portrait ecommerce photograph, approximately 4:5, showing one product. No collage, inset, duplicate views, added text or watermark.', required_evidence=('front_view',), version=2),
    'ecommerce-outerwear-gilets-padded-vests-05': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[4], id='ecommerce-outerwear-gilets-padded-vests-05', name='Fabric and Quilting Detail', applicable_families=("gilets-padded-vests",), reference_object_key='docs/gilets-output-details/references/05_fabric_detail.png', presentation_mode='garment', output_presentation='product_only', output_details='- Subject: Uploaded gilet or padded vest, presented using `garment`. - Camera angle and orientation: Oblique macro across supported material and intersecting seams. - Framing and crop: Fabric fills frame with no surrounding backdrop; whole garment, collar and hem absent. - Product position and pose: Broad panel occupies centre; diagonal quilting lines cross frame and meet a steeper seam toward image right. - Product scale: Close detail fills the frame at the benchmark scale. - Silhouette: Preserve actual sleeveless outline, armhole depth, shoulder width, length and fit; never add sleeves or force a different gilet into this example silhouette. - Visible construction: Evidenced material surface, stitches and panel junction; do not fabricate quilting on an unquilted product. - Garment volume: Actual local padding relief with shallow seam gathers and gentle contact shadows. - Background: No exposed background; material fills the frame. - Lighting: Soft diffused directional studio light and gentle shadows. Preserve actual finish and subtle highlights; no glossy plastic effect, hard flash or dramatic coloured lighting. - Colour treatment: Preserve source colours and tonal variation. Do not transfer navy from the benchmark or cast beige onto the product. - Surface fidelity: Retain real texture scale, stitching and padding relief. Do not multiply quilting channels, regularise uneven panels, invent microtexture or infer insulation material/performance from appearance. - Secondary styling: No model, skin, shirt, sleeves, trousers, hanger, stand or visible mannequin. - Output: One continuous portrait ecommerce photograph, approximately 4:5, showing one product. No collage, inset, duplicate views, added text or watermark.', required_evidence=('detail',), version=2),
    'ecommerce-outerwear-gilets-padded-vests-06': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[5], id='ecommerce-outerwear-gilets-padded-vests-06', name='Rear Product — Invisible Mannequin', applicable_families=("gilets-padded-vests",), reference_object_key='docs/gilets-output-details/references/06_rear_product.png', presentation_mode='invisible_mannequin', output_presentation='product_only', output_details='- Subject: Uploaded gilet or padded vest, presented using `invisible_mannequin`. - Camera angle and orientation: Straight-on rear at garment level. - Framing and crop: Whole rear including raised collar, both armhole outlines and hem with clear margins. - Product position and pose: Centred vertical garment, shoulders balanced and back unobstructed. - Product scale: Match benchmark occupancy while retaining actual garment proportions and the stated margins. - Silhouette: Preserve actual sleeveless outline, armhole depth, shoulder width, length and fit; never add sleeves or force a different gilet into this example silhouette. - Visible construction: Actual rear panels, collar, armholes, side edges and hem. - Garment volume: Soft supported back shape with natural padding loft, no visible mannequin. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no lifestyle location, props or scenery. - Lighting: Soft diffused directional studio light and gentle shadows. Preserve actual finish and subtle highlights; no glossy plastic effect, hard flash or dramatic coloured lighting. - Colour treatment: Preserve source colours and tonal variation. Do not transfer navy from the benchmark or cast beige onto the product. - Surface fidelity: Retain real texture scale, stitching and padding relief. Do not multiply quilting channels, regularise uneven panels, invent microtexture or infer insulation material/performance from appearance. - Secondary styling: No model, skin, shirt, sleeves, trousers, hanger, stand or visible mannequin. - Output: One continuous portrait ecommerce photograph, approximately 4:5, showing one product. No collage, inset, duplicate views, added text or watermark.', required_evidence=('rear_view',), version=2),
    'ecommerce-outerwear-gilets-padded-vests-07': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[6], id='ecommerce-outerwear-gilets-padded-vests-07', name='Model Front Facing — Cropped', applicable_families=("gilets-padded-vests",), reference_object_key='docs/gilets-output-details/references/07_front_model_cropped.png', presentation_mode='model', output_presentation='worn_product', output_details='- Subject: Uploaded gilet or padded vest, presented using `model`. - Camera angle and orientation: Straight-on front at torso height. - Framing and crop: Neck base through upper thighs; entire gilet hem and both hands visible, face and feet excluded. - Product position and pose: Centred torso, relaxed arms, hands outside pockets; upper fastening partly open. - Product scale: Match benchmark occupancy while retaining actual garment proportions and the stated margins. - Silhouette: Preserve actual sleeveless outline, armhole depth, shoulder width, length and fit; never add sleeves or force a different gilet into this example silhouette. - Visible construction: Actual front panels, closure, collar, armhole edges and hem. - Garment volume: Natural torso fit and modest padding compression; keep armholes clear. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no lifestyle location, props or scenery. - Lighting: Soft diffused directional studio light and gentle shadows. Preserve actual finish and subtle highlights; no glossy plastic effect, hard flash or dramatic coloured lighting. - Colour treatment: Preserve source colours and tonal variation. Do not transfer navy from the benchmark or cast beige onto the product. - Surface fidelity: Retain real texture scale, stitching and padding relief. Do not multiply quilting channels, regularise uneven panels, invent microtexture or infer insulation material/performance from appearance. - Secondary styling: Plain light neutral short-sleeved underlayer and simple dark trousers where visible; understated footwear only for full-length slot 04. Underlayer sleeves are separate garments, never gilet sleeves. Keep arms relaxed and hands outside pockets when visible; do not introduce hands into detail crops. - Output: One continuous portrait ecommerce photograph, approximately 4:5, showing one product. No collage, inset, duplicate views, added text or watermark.', required_evidence=('front_view',), version=2),
    'ecommerce-outerwear-gilets-padded-vests-08': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[7], id='ecommerce-outerwear-gilets-padded-vests-08', name='Model Rear — Cropped', applicable_families=("gilets-padded-vests",), reference_object_key='docs/gilets-output-details/references/08_rear_model.png', presentation_mode='model', output_presentation='worn_product', output_details='- Subject: Uploaded gilet or padded vest, presented using `model`. - Camera angle and orientation: Straight-on rear at torso height. - Framing and crop: Nape through upper thighs, both hands and complete gilet hem; head/face and feet excluded. - Product position and pose: Centred standing back, shoulders level, arms down. - Product scale: Match benchmark occupancy while retaining actual garment proportions and the stated margins. - Silhouette: Preserve actual sleeveless outline, armhole depth, shoulder width, length and fit; never add sleeves or force a different gilet into this example silhouette. - Visible construction: Actual rear collar, panel layout, armhole binding and hem. - Garment volume: Natural back drape, padding volume and fit over underlayer. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no lifestyle location, props or scenery. - Lighting: Soft diffused directional studio light and gentle shadows. Preserve actual finish and subtle highlights; no glossy plastic effect, hard flash or dramatic coloured lighting. - Colour treatment: Preserve source colours and tonal variation. Do not transfer navy from the benchmark or cast beige onto the product. - Surface fidelity: Retain real texture scale, stitching and padding relief. Do not multiply quilting channels, regularise uneven panels, invent microtexture or infer insulation material/performance from appearance. - Secondary styling: Plain light neutral short-sleeved underlayer and simple dark trousers where visible; understated footwear only for full-length slot 04. Underlayer sleeves are separate garments, never gilet sleeves. Keep arms relaxed and hands outside pockets when visible; do not introduce hands into detail crops. - Output: One continuous portrait ecommerce photograph, approximately 4:5, showing one product. No collage, inset, duplicate views, added text or watermark.', required_evidence=('rear_view',), version=2),
    'ecommerce-outerwear-gilets-padded-vests-09': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[8], id='ecommerce-outerwear-gilets-padded-vests-09', name='Model Front Three-Quarter — Cropped', applicable_families=("gilets-padded-vests",), reference_object_key='docs/gilets-output-details/references/09_three_quarter_model.png', presentation_mode='model', output_presentation='worn_product', output_details='- Subject: Uploaded gilet or padded vest, presented using `model`. - Camera angle and orientation: Front three-quarter, near shoulder/arm at image right, body turned slightly toward image left. - Framing and crop: Neck base through upper thighs; complete garment and both hands visible, face and feet excluded. - Product position and pose: Standing adult with arms relaxed and hands outside pockets; front fastening partly open at neckline. - Product scale: Match benchmark occupancy while retaining actual garment proportions and the stated margins. - Silhouette: Preserve actual sleeveless outline, armhole depth, shoulder width, length and fit; never add sleeves or force a different gilet into this example silhouette. - Visible construction: Front fastening, near armhole, collar, side construction and hem. - Garment volume: Natural depth through chest and near side; preserve padding thickness without inflating silhouette. - Background: Light warm beige seamless studio background, approximately #C8C1B6; no lifestyle location, props or scenery. - Lighting: Soft diffused directional studio light and gentle shadows. Preserve actual finish and subtle highlights; no glossy plastic effect, hard flash or dramatic coloured lighting. - Colour treatment: Preserve source colours and tonal variation. Do not transfer navy from the benchmark or cast beige onto the product. - Surface fidelity: Retain real texture scale, stitching and padding relief. Do not multiply quilting channels, regularise uneven panels, invent microtexture or infer insulation material/performance from appearance. - Secondary styling: Plain light neutral short-sleeved underlayer and simple dark trousers where visible; understated footwear only for full-length slot 04. Underlayer sleeves are separate garments, never gilet sleeves. Keep arms relaxed and hands outside pockets when visible; do not introduce hands into detail crops. - Output: One continuous portrait ecommerce photograph, approximately 4:5, showing one product. No collage, inset, duplicate views, added text or watermark.', required_evidence=('front_view', 'side_view'), version=2),
    'ecommerce-outerwear-gilets-padded-vests-10': replace(OUTERWEAR_ECOMMERCE_TEMPLATES[8], id='ecommerce-outerwear-gilets-padded-vests-10', name='Front Flat Lay — Overhead', applicable_families=("gilets-padded-vests",), reference_object_key='docs/gilets-output-details/references/10_front_flat_template.png', presentation_mode='garment', output_presentation='product_only', output_details='- Subject: Uploaded gilet or padded vest, presented using `garment`. - Camera angle and orientation: Directly overhead with camera sensor parallel to horizontal studio surface. - Framing and crop: Entire garment, collar, both armholes and hem inside frame with surrounding surface. - Product position and pose: Front upward, centred, body arranged flat, fastening mostly closed with small opening at neck. - Product scale: Match benchmark occupancy while retaining actual garment proportions and the stated margins. - Silhouette: Preserve actual sleeveless outline, armhole depth, shoulder width, length and fit; never add sleeves or force a different gilet into this example silhouette. - Visible construction: Actual front closure, collar, armhole binding, quilting if present and hem. - Garment volume: Surface-supported body with close contact shadows; retain real padding thickness and soft collar folds without artificial torso inflation. - Background: Light warm beige seamless studio surface, approximately #C8C1B6; no lifestyle location, props or scenery. - Lighting: Soft diffused directional studio light and gentle shadows. Preserve actual finish and subtle highlights; no glossy plastic effect, hard flash or dramatic coloured lighting. - Colour treatment: Preserve source colours and tonal variation. Do not transfer navy from the benchmark or cast beige onto the product. - Surface fidelity: Retain real texture scale, stitching and padding relief. Do not multiply quilting channels, regularise uneven panels, invent microtexture or infer insulation material/performance from appearance. - Secondary styling: No model, skin, shirt, sleeves, trousers, hanger, stand or visible mannequin. - Output: One continuous portrait ecommerce photograph, approximately 4:5, showing one product. No collage, inset, duplicate views, added text or watermark.', required_evidence=('front_view',), version=2),
}


FOOTWEAR_ECOMMERCE_TEMPLATES: Final[tuple[GenerationTemplate, ...]] = tuple(
    _support_template("footwear", template_id, name, description, instruction, _FOOTWEAR_SUBTYPES)
    for template_id, name, description, instruction in (
        ("ecommerce-footwear-three-quarter-product", "Three-Quarter Product", "An angled product-only footwear view.", "Show the footwear from a three-quarter product-only angle, preserving toe, side, upper and sole shape."),
        ("ecommerce-footwear-outer-side", "Outer Side", "A complete outer-side profile.", "Show the footwear's outer-side profile with its complete silhouette, upper construction and sole."),
        ("ecommerce-footwear-inner-side", "Inner Side", "A complete inner-side profile.", "Show the footwear's inner-side profile and visible medial construction without inventing hidden details."),
        ("ecommerce-footwear-front-view", "Front View", "A head-on footwear product view.", "Show the footwear head-on, preserving toe shape, front proportions and upper details."),
        ("ecommerce-footwear-rear-view", "Rear View", "A straight-on rear footwear view.", "Show a strictly straight-on rear view of the footwear. Place the camera directly behind the heel, centered on the heel axis, with the optical axis perpendicular to the rear heel plane. Keep the heel counter and outsole parallel to the image plane; show no outer or inner side profile, toe, front opening or three-quarter angle. Center the product symmetrically and show only the rear heel construction and sole thickness that are visible in the references, without inventing unseen details."),
        ("ecommerce-footwear-top-view", "Top View", "A direct overhead footwear view.", "Create one finished ecommerce photograph of the exact footwear from a true overhead camera angle, looking directly down at the product. Align the footwear vertically in the frame from toe to heel and show its complete top silhouette, opening, throat, visible fastening, upper panels and proportions supported by the reference. Keep the footwear centred on a clean light neutral studio surface with soft diffuse lighting and minimal shadow. Do not show a side or rear angle, add a second shoe, include a person or mannequin, or reveal the outsole."),
        ("ecommerce-footwear-sole-view", "Sole View", "A complete underside view.", "Create one straight-on underside product photograph of the exact footwear with the shoe rotated or positioned so the outsole faces the camera directly. Align the footwear from toe to heel and let the complete outsole fill most of the frame. Show the actual outsole shape, tread pattern, heel area, forefoot, edges and visible sole construction supported by the reference. Use a centred orthographic-looking camera angle with minimal perspective distortion, a clean light neutral studio background and soft controlled lighting. Do not show the upper, top view, side view, second shoe, person, mannequin or alternate angle."),
        ("ecommerce-footwear-front-on-feet", "Front on Feet", "Footwear worn in a front-facing stance.", "Show the footwear worn by an adult from the front, cropped below the knees, with no extra footwear."),
        ("ecommerce-footwear-side-on-feet", "Side on Feet", "Footwear worn in a side stance.", "Show the footwear worn by an adult from the side, cropped below the knees, preserving fit and profile."),
    )
)

# Trainers is the reviewed Footwear family with its own benchmark pack.
_TRAINERS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    'ecommerce-footwear-three-quarter-product': replace(FOOTWEAR_ECOMMERCE_TEMPLATES[0], applicable_families=("shoes",), reference_object_key='docs/trainers-output-details/references/01-three-quarter-product.png', presentation_mode='garment', output_presentation='product_only', output_details="- Subject: One uploaded shoe. - Presentation: Resting on its sole without visible support. - Camera angle: Slightly elevated front three-quarter. - View orientation: Toe toward lower left, heel upper right; outer side visible. - Framing: Complete shoe. - Crop: No clipped toe or heel. - Product position: Diagonal across lower-middle frame. - Product scale: Large with breathing space. - Silhouette: Actual toe, heel height and upper profile. - Visible construction: Actual upper, opening, fastenings and sole edge. - Product volume: Preserve actual shoe structure. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One shoe only, no feet. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text. - Aspect ratio: Portrait, approximately 4:5. - Secondary styling: No person, feet, socks, hands, visible stand, mannequin or shoe tree. Interior appears only where this angle reveals it.", required_evidence=('front_view', 'side_view'), version=2),
    'ecommerce-footwear-outer-side': replace(FOOTWEAR_ECOMMERCE_TEMPLATES[1], applicable_families=("shoes",), reference_object_key='docs/trainers-output-details/references/02-outer-side.png', presentation_mode='garment', output_presentation='product_only', output_details="- Subject: One uploaded shoe, outer side. - Presentation: Resting on its sole. - Camera angle: Level side profile. - View orientation: Lateral side; toe left, heel right. - Framing: Complete shoe. - Crop: No clipped toe, heel or shaft. - Product position: Horizontal across centre/lower frame. - Product scale: Shoe spans most of width. - Silhouette: Actual lateral outline and heel/sole geometry. - Visible construction: Real outer-side seams, panels and details. - Product volume: Actual upper volume. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One shoe; do not mirror medial details. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text. - Aspect ratio: Portrait, approximately 4:5. - Secondary styling: No person, feet, socks, hands, visible stand, mannequin or shoe tree. Interior appears only where this angle reveals it.", required_evidence=('side_view',), version=2),
    'ecommerce-footwear-inner-side': replace(FOOTWEAR_ECOMMERCE_TEMPLATES[2], applicable_families=("shoes",), reference_object_key='docs/trainers-output-details/references/03-inner-side.png', presentation_mode='garment', output_presentation='product_only', output_details="- Subject: One uploaded shoe, inner side. - Presentation: Resting on its sole. - Camera angle: Level side profile. - View orientation: Medial side; toe right, heel left. - Framing: Complete shoe. - Crop: No clipped ends or shaft. - Product position: Horizontal across centre/lower frame. - Product scale: Most of frame width. - Silhouette: Actual medial outline. - Visible construction: Real inner-side construction, not a flipped lateral substitute. - Product volume: Actual shoe volume. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One shoe only. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text. - Aspect ratio: Portrait, approximately 4:5. - Secondary styling: No person, feet, socks, hands, visible stand, mannequin or shoe tree. Interior appears only where this angle reveals it.", required_evidence=('side_view',), version=2),
    'ecommerce-footwear-front-view': replace(FOOTWEAR_ECOMMERCE_TEMPLATES[3], applicable_families=("shoes",), reference_object_key='docs/trainers-output-details/references/04-front-view.png', presentation_mode='garment', output_presentation='product_only', output_details="- Subject: One uploaded shoe from front. - Presentation: Resting upright on studio surface. - Camera angle: Head-on, slightly elevated enough to show upper. - View orientation: Toe toward camera, heel behind. - Framing: Complete projected front silhouette. - Crop: Retain toe and uppermost edge. - Product position: Centred on vertical axis. - Product scale: Moderate size with clear surrounding space. - Silhouette: Actual toe width and upper height. - Visible construction: Actual toe/upper and fastenings where visible. - Product volume: Natural depth behind toe. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One shoe, no foot or second shoe. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text. - Aspect ratio: Portrait, approximately 4:5. - Secondary styling: No person, feet, socks, hands, visible stand, mannequin or shoe tree. Interior appears only where this angle reveals it.", required_evidence=('front_view',), version=2),
    'ecommerce-footwear-rear-view': replace(FOOTWEAR_ECOMMERCE_TEMPLATES[4], applicable_families=("shoes",), reference_object_key='docs/trainers-output-details/references/05-rear-view.png', presentation_mode='garment', output_presentation='product_only', output_details="- Subject: One uploaded shoe from rear. - Presentation: Upright heel facing camera. - Camera angle: Centred rear view, slightly elevated. - View orientation: Rear with no deliberate side turn. - Framing: Complete projected rear silhouette. - Crop: Retain heel base and top edge. - Product position: Heel centred. - Product scale: Moderate with clear border. - Silhouette: Actual heel profile and height. - Visible construction: Actual rear seams, heel counter/straps and sole junction. - Product volume: Natural upper depth. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One shoe; do not replace its actual heel design with benchmark construction. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text. - Aspect ratio: Portrait, approximately 4:5. - Secondary styling: No person, feet, socks, hands, visible stand, mannequin or shoe tree. Interior appears only where this angle reveals it.", required_evidence=('rear_view',), version=2),
    'ecommerce-footwear-top-view': replace(FOOTWEAR_ECOMMERCE_TEMPLATES[5], applicable_families=("shoes",), reference_object_key='docs/trainers-output-details/references/06-top-view.png', presentation_mode='garment', output_presentation='product_only', output_details="- Subject: One uploaded shoe from above. - Presentation: Product-only overhead arrangement. - Camera angle: Direct overhead perpendicular to upper. - View orientation: Toe at top, heel at bottom. - Framing: Whole toe-to-heel outline. - Crop: Retain all edges. - Product position: Long axis vertical. - Product scale: Most of image height. - Silhouette: Actual top outline and opening. - Visible construction: Actual opening, insole and fastenings when visible. - Product volume: Natural cavity depth. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One shoe, no foot. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text. - Aspect ratio: Portrait, approximately 4:5. - Secondary styling: No person, feet, socks, hands, visible stand, mannequin or shoe tree. Interior appears only where this angle reveals it.", required_evidence=('top_view',), version=2),
    'ecommerce-footwear-sole-view': replace(FOOTWEAR_ECOMMERCE_TEMPLATES[6], applicable_families=("shoes",), reference_object_key='docs/trainers-output-details/references/07-sole-view.png', presentation_mode='garment', output_presentation='product_only', output_details="- Subject: Underside of one uploaded shoe. - Presentation: Sole facing camera, visually upright with heel near surface. - Camera angle: Perpendicular to sole plane. - View orientation: Toe top, heel bottom. - Framing: Complete underside. - Crop: Retain sole perimeter. - Product position: Centred vertical. - Product scale: Large with narrow border. - Silhouette: Actual outsole shape and heel geometry. - Visible construction: Only supported sole/tread details; do not invent benchmark herringbone. - Product volume: Real relief, arch and heel depth. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One underside, no hand or stand. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text. - Aspect ratio: Portrait, approximately 4:5. - Secondary styling: No person, feet, socks, hands, visible stand, mannequin or shoe tree. Interior appears only where this angle reveals it.", required_evidence=('sole_or_underside',), version=2),
    'ecommerce-footwear-front-on-feet': replace(FOOTWEAR_ECOMMERCE_TEMPLATES[6], applicable_families=("shoes",), reference_object_key='docs/trainers-output-details/references/09-front-on-feet.png', presentation_mode='model', output_presentation='worn_product', output_details="- Subject: Uploaded footwear worn as a pair. - Presentation: Adult standing front-facing, both feet on floor, dark trouser hems above shoes. - Camera angle: Low front view. - View orientation: Both toes facing camera. - Framing: Lower legs and complete shoes. - Crop: Below knees; no clipped toes. - Product position: Pair side-by-side with small gap. - Product scale: Shoes prominent below trouser hems. - Silhouette: Actual worn shape and heel height. - Visible construction: Actual uppers and closures; trousers must not hide key footwear design. - Product volume: Natural on-foot volume. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One pair on adult feet, no upper body. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text. - Aspect ratio: Portrait, approximately 4:5. - Secondary styling: Simple dark trouser hems above the shoes; no upper body. Keep footwear design unobscured and both feet naturally grounded. Maintain actual left/right shoe differences.", required_evidence=('front_view',), version=2),
    'ecommerce-footwear-side-on-feet': replace(FOOTWEAR_ECOMMERCE_TEMPLATES[7], applicable_families=("shoes",), reference_object_key='docs/trainers-output-details/references/10-side-on-feet.png', presentation_mode='model', output_presentation='worn_product', output_details="- Subject: Uploaded footwear worn as a pair. - Presentation: Side stance, near foot ahead; far shoe partly behind; dark trousers. - Camera angle: Low side view. - View orientation: Toes point left; near shoe profile dominant. - Framing: Lower legs and shoes. - Crop: Below knees; keep near shoe complete. - Product position: Near shoe lower-left, far heel farther right. - Product scale: Pair prominent. - Silhouette: Actual side profile and fit. - Visible construction: Near shoe side, heel and upper details. - Product volume: Natural foot-supported volume. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no unrelated props. - Lighting: Soft directional studio light with gentle shadows; preserve the uploaded material's actual sheen and fine detail without exaggerated grain or sharpening. - Colour treatment: Preserve source colour, tonal variation, surface finish and artwork; do not transfer benchmark colours or add a beige cast to the product. - Composition: One pair, partial far-shoe overlap allowed. - Output: One continuous high-fidelity ecommerce photograph; no collage, inset, duplicate views or added text. - Aspect ratio: Portrait, approximately 4:5. - Secondary styling: Simple dark trouser hems above the shoes; no upper body. Keep footwear design unobscured and both feet naturally grounded. Maintain actual left/right shoe differences.", required_evidence=('side_view', 'rear_view'), version=2),
}


# Flats / Loafers is a reviewed Footwear family with a dedicated eight-image
# benchmark pack. The pack applies to both flats and loafers without allowing
# the brown tassel-loafer identity in the references to leak into other products.
_FLATS_LOAFERS_CONSTRUCTION = (
    "Preserve the uploaded footwear's actual toe shape, vamp/opening, heel height, arch, sole thickness, upper material, colour, patina, stitching, ornaments, hardware and branding. Do not add tassels, apron stitching, a raised heel or any other benchmark-specific feature unless visible in the product references."
)
_FLATS_LOAFERS_DETAILS: Final[tuple[str, ...]] = (
    "- Subject: One uploaded flat or loafer, without a foot. - Presentation: Product-only, naturally resting on the studio surface with no visible support. - Camera angle and orientation: Slightly elevated front three-quarter. - Product position and pose: One shoe diagonally across the lower-middle frame, toe lower left and heel upper right. - Framing and crop: Complete shoe including toe, heel and sole, with ample neutral space above. - Product scale: Match benchmark occupancy and negative space while preserving actual proportions. - Silhouette: Preserve toe width and shape, vamp height, opening, heel height, arch and sole thickness. - Visible construction: Actual toe, side panel, opening, ornaments and sole edge. - Product volume: Real upper structure and cavity depth without an invented foot or shoe tree. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no props. - Lighting: Soft diffused directional light with gentle contact shadows; retain actual sheen and texture without excessive gloss or artificial grain. - Colour treatment: Preserve source colour, patina and tonal variation; do not transfer benchmark brown, dark sole or beige cast. - Secondary styling: No person, feet, socks, hands, shoe tree, mannequin, hanger or stand. - Output: One continuous portrait ecommerce photograph, approximately 4:5; no collage, inset, duplicate angle, text or watermark.",
    "- Subject: One uploaded flat or loafer, without a foot. - Presentation: Product-only, resting on its sole. - Camera angle and orientation: Low level side profile, toe left and heel right. - Framing and crop: Complete shoe across most of the lower-middle frame; retain toe, heel and upper edge. - Product scale: Match benchmark occupancy and negative space while preserving actual proportions. - Silhouette: Preserve toe, vamp, opening, heel, arch and sole profile. - Visible construction: Actual side construction, vamp edge, heel height and sole profile. - Product volume: Real upper structure and cavity depth without an invented foot or shoe tree. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6. - Lighting: Soft diffused directional light with gentle contact shadows and real material detail. - Colour treatment: Preserve source colour and patina; do not transfer benchmark brown or dark sole. - Secondary styling: No person, feet, socks, hands, shoe tree, mannequin, hanger or stand. - Output: One continuous portrait ecommerce photograph, approximately 4:5; no collage, inset, duplicate angle, text or watermark.",
    "- Subject: One uploaded flat or loafer, without a foot. - Presentation: Product-only, naturally supported on its sole. - Camera angle and orientation: Low level opposite-facing side profile, toe right and heel left. - Framing and crop: Whole shoe with generous space above and no clipped ends. - Product scale: Match benchmark occupancy and negative space while preserving actual proportions. - Silhouette: Preserve toe, vamp, opening, heel, arch and sole profile. - Visible construction: Actual side panel, upper edge, heel, arch and sole construction; never flip missing-side details. - Product volume: Real upper structure and cavity depth without an invented foot or shoe tree. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6. - Lighting: Soft diffused directional light with gentle contact shadows. - Colour treatment: Preserve source colour and patina; do not transfer benchmark styling. - Secondary styling: No person, feet, socks, hands, shoe tree, mannequin, hanger or stand. - Output: One continuous portrait ecommerce photograph, approximately 4:5; no collage, inset, duplicate angle, text or watermark.",
    "- Subject: One uploaded flat or loafer, without a foot. - Presentation: Product-only, naturally resting on the studio surface. - Camera angle and orientation: Head-on front, slightly elevated to reveal the vamp. - Product position and pose: Single shoe centred, toe toward camera and heel behind. - Framing and crop: Complete projected outline with clear border and upper negative space. - Product scale: Match benchmark occupancy while preserving proportions. - Silhouette: Preserve toe, vamp, opening, heel, arch and sole thickness. - Visible construction: Toe, vamp, opening and actual decorative or fastening elements. - Product volume: Real upper structure and cavity depth without an invented foot or shoe tree. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6. - Lighting: Soft diffused directional light with gentle contact shadows. - Colour treatment: Preserve source colour and patina; do not transfer benchmark styling. - Secondary styling: No person, feet, socks, hands, shoe tree, mannequin, hanger or stand. - Output: One continuous portrait ecommerce photograph, approximately 4:5; no collage, inset, duplicate angle, text or watermark.",
    "- Subject: One uploaded flat or loafer, without a foot. - Presentation: Product-only, naturally resting on the studio surface. - Camera angle and orientation: Centred straight rear, slightly elevated, with no side turn. - Product position and pose: Heel faces camera and the long axis recedes behind. - Framing and crop: Whole projected rear outline with heel base and collar retained. - Product scale: Match benchmark occupancy while preserving proportions. - Silhouette: Preserve actual heel height, collar, arch and sole thickness. - Visible construction: Actual heel counter, rear seams, collar, heel block and sole junction only where supported. - Product volume: Real upper structure and cavity depth without an invented foot or shoe tree. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6. - Lighting: Soft diffused directional light with gentle contact shadows. - Colour treatment: Preserve source colour and patina; do not transfer benchmark styling. - Secondary styling: No person, feet, socks, hands, shoe tree, mannequin, hanger or stand. - Output: One continuous portrait ecommerce photograph, approximately 4:5; no collage, inset, duplicate angle, text or watermark.",
    "- Subject: One uploaded flat or loafer, without a foot. - Presentation: Product-only overhead arrangement. - Camera angle and orientation: Direct overhead, camera parallel to the supporting surface. - Product position and pose: One shoe vertically aligned, toe top and heel bottom. - Framing and crop: Complete toe-to-heel perimeter spanning most of image height. - Product scale: Match benchmark occupancy while preserving proportions. - Silhouette: Preserve toe, vamp, opening, heel, arch and sole thickness. - Visible construction: Actual top outline, vamp, ornament, collar opening and visible insole. - Product volume: Real upper structure and cavity depth without an invented foot or shoe tree. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6. - Lighting: Soft diffused directional light with gentle contact shadows. - Colour treatment: Preserve source colour and patina; do not transfer benchmark styling. - Secondary styling: No person, feet, socks, hands, shoe tree, mannequin, hanger or stand. - Output: One continuous portrait ecommerce photograph, approximately 4:5; no collage, inset, duplicate angle, text or watermark.",
    "- Subject: One pair of uploaded flats or loafers worn by an adult. - Presentation: Natural standing wear with relaxed grounded feet. - Camera angle and orientation: Low front view with slight downward visibility of vamps. - Product position and pose: Both feet grounded, side by side, toes facing camera. - Framing and crop: Lower legs below knees and complete pair; dark trouser hems above shoes, small ankle exposure, no clipped toes. - Product scale: Match benchmark occupancy while preserving proportions. - Silhouette: Preserve actual toe, vamp, opening, heel, arch and sole. - Visible construction: Actual worn toe, vamp/ornament, collar fit and front sole edge. - Product volume: Natural foot-supported shape without stretching the upper. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6. - Lighting: Soft diffused directional light with gentle contact shadows. - Colour treatment: Preserve source colour and patina; do not transfer benchmark styling. - Secondary styling: Plain dark trouser hems only; no upper body. Keep shoes unobscured and preserve left/right differences. - Output: One continuous portrait ecommerce photograph, approximately 4:5; no collage, inset, duplicate angle, text or watermark.",
    "- Subject: One pair of uploaded flats or loafers worn by an adult. - Presentation: Natural standing wear with relaxed grounded feet. - Camera angle and orientation: Low side view. - Product position and pose: Both toes point left; near foot ahead, far shoe partly behind, both grounded. - Framing and crop: Below-knee legs and shoes; near shoe complete, far toe occlusion allowed and far heel at right. - Product scale: Match benchmark occupancy while preserving proportions. - Silhouette: Preserve actual toe, vamp, opening, heel, arch and sole. - Visible construction: Near-side profile, vamp and ornaments, actual heel/arch and visible far heel. - Product volume: Natural foot-supported shape without stretching the upper. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6. - Lighting: Soft diffused directional light with gentle contact shadows. - Colour treatment: Preserve source colour and patina; do not transfer benchmark styling. - Secondary styling: Plain dark trouser hems only; no upper body. Keep shoes unobscured and preserve left/right differences. - Output: One continuous portrait ecommerce photograph, approximately 4:5; no collage, inset, duplicate angle, text or watermark.",
)
_FLATS_LOAFERS_MODES = ("garment", "garment", "garment", "garment", "garment", "garment", "model", "model")
_FLATS_LOAFERS_EVIDENCE = (("front_view", "side_view"), ("side_view",), ("side_view",), ("front_view",), ("rear_view",), ("top_view",), ("front_view",), ("side_view", "rear_view"))
_FLATS_LOAFERS_NAMES = ("Three-Quarter Product", "Side Profile — Toe Left", "Side Profile — Toe Right", "Front View", "Rear View", "Top View", "Front on Feet", "Side on Feet")
_FLATS_LOAFERS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    f"ecommerce-footwear-flats-loafers-{index + 1:02d}": replace(
        FOOTWEAR_ECOMMERCE_TEMPLATES[index if index < 6 else 6 if index == 6 else 7],
        id=f"ecommerce-footwear-flats-loafers-{index + 1:02d}", name=_FLATS_LOAFERS_NAMES[index],
        description=f"Reviewed Flats / Loafers Ecommerce composition: {_FLATS_LOAFERS_NAMES[index]}.",
        applicable_families=("shoes",), reference_object_key=f"docs/flats-loafers-output-details/references/{index + 1:02d}_" + ("three_quarter_product" if index == 0 else "side_profile_toe_left" if index == 1 else "side_profile_toe_right" if index == 2 else "front_view" if index == 3 else "rear_view" if index == 4 else "top_view" if index == 5 else "front_on_feet" if index == 6 else "side_on_feet") + ".png",
        presentation_mode=_FLATS_LOAFERS_MODES[index], output_presentation="worn_product" if _FLATS_LOAFERS_MODES[index] == "model" else "product_only",
        output_details=_FLATS_LOAFERS_DETAILS[index], required_evidence=_FLATS_LOAFERS_EVIDENCE[index],
        required_product_fields=("product_type", "global_details.colour", "global_details.materials", "global_details.construction", "category_details", "category_details.toe_shape", "category_details.sole_type"),
        prompt_format_rules=(
            "The product reference images are the primary authority for every visible footwear feature.",
            "Use the template only for composition and presentation, never for footwear identity.",
            _FLATS_LOAFERS_CONSTRUCTION,
            "Uncertainty applies only to genuinely hidden, obstructed, cropped or unassessable details.",
        ),
        version=2,
    ) for index in range(8)
}


# Heels is a dedicated Footwear family. The red patent court-shoe benchmarks
# control composition only; they must not turn flats, sandals or block heels
# into a pointed stiletto pump.
_HEELS_FIDELITY = "Preserve the uploaded heel's actual heel type, height and geometry, pitch, toe shape, opening, upper coverage, straps, fastening, platform, arch, sole, lining, finish, seams, hardware and branding. Do not infer numeric heel height or transfer the benchmark's pointed closed pump, red lacquer, tan lining or heel tip to another product."
_HEELS_MODES = ("garment", "garment", "garment", "garment", "garment", "garment", "model", "model")
_HEELS_EVIDENCE = (("front_view", "side_view"), ("side_view",), ("side_view",), ("front_view", "top_view"), ("rear_view", "sole_or_underside"), ("top_view",), ("front_view",), ("side_view", "rear_view"))
_HEELS_NAMES = ("Three-Quarter Product", "Side Profile — Toe Left", "Side Profile — Toe Right", "Front View", "Rear View", "Top View", "Front on Feet", "Side on Feet")
_HEELS_DETAIL_PREFIX = "- Subject: Uploaded heeled footwear. - Presentation: {presentation}. - Camera and orientation: {camera}. - Framing and position: {framing}. - Silhouette: Preserve actual heel geometry, pitch, toe-box shape, opening, sole thickness and arch clearance; do not infer numeric heel height from the benchmark. - Visible construction: Show only actual toe, upper, opening, lining, heel, arch, sole, seams, straps, buckles and embellishments supported by product references. - Product volume: Preserve real upper structure and cavity; no invented foot or shoe tree for product-only views. - Background: Light warm beige seamless studio surface/background, approximately #C8C1B6; no props or scenery. - Lighting: Soft diffused directional light with controlled reflections and contact shadows; preserve glossy, matte or suede finish from the product rather than copying the benchmark finish. - Colour treatment: Preserve source colour, lining colour and tonal variation; do not transfer benchmark red lacquer or tan sole. - Secondary styling: {styling}. - Output: One continuous portrait ecommerce photograph, approximately 4:5; no collage, inset, duplicate angle, text or watermark."
_HEELS_DETAILS: Final[tuple[str, ...]] = (
    _HEELS_DETAIL_PREFIX.format(presentation="product-only, resting naturally on forefoot sole and heel tip", camera="Elevated front three-quarter", framing="One shoe diagonally toe lower left and heel upper right; complete upper, heel tip and toe with generous space above", styling="No person, feet, socks, hands, mannequin, shoe tree or visible support."),
    _HEELS_DETAIL_PREFIX.format(presentation="product-only, resting naturally on forefoot sole and heel tip", camera="Low side profile, slightly elevated to see the inner rim; toe left and heel right", framing="Single shoe horizontal across lower-middle frame; entire toe and heel tip retained", styling="No person, feet, socks, hands, mannequin, shoe tree or visible support."),
    _HEELS_DETAIL_PREFIX.format(presentation="product-only, resting naturally on forefoot sole and heel tip", camera="Low opposite-facing side profile; toe right and heel left", framing="Single shoe with complete outline and generous upper negative space", styling="No person, feet, socks, hands, mannequin, shoe tree or visible support."),
    _HEELS_DETAIL_PREFIX.format(presentation="product-only, upright and naturally supported", camera="Centred head-on front, elevated to show opening and insole", framing="One shoe vertically centred with full projected outline and clear margins", styling="No person, feet, socks, hands, mannequin, shoe tree or visible support."),
    _HEELS_DETAIL_PREFIX.format(presentation="product-only, upright with heel tip aligned beneath the counter", camera="Straight centred rear without deliberate side turn", framing="Complete shoe projection with heel tip, counter and exposed arch underside visible", styling="No person, feet, socks, hands, mannequin, shoe tree or visible support."),
    _HEELS_DETAIL_PREFIX.format(presentation="product-only overhead arrangement", camera="Direct overhead, perpendicular to the studio surface", framing="Long axis vertical, toe top and heel bottom, whole outline filling most of image height", styling="No person, feet, socks, hands, mannequin, shoe tree or visible support."),
    _HEELS_DETAIL_PREFIX.format(presentation="natural standing wear by an adult", camera="Front-facing, slightly elevated toward toe boxes and insteps", framing="Pair side by side with a small gap; lower legs below knees and complete shoes", styling="Bare lower legs only; no socks, trousers, accessories, upper body or face; feet grounded and shoes correctly fitted."),
    _HEELS_DETAIL_PREFIX.format(presentation="natural standing wear by an adult", camera="Low side view", framing="Toes point left; near foot ahead, far toe partly hidden; both heel tips grounded; crop below knees", styling="Bare lower legs only; no socks, trousers, accessories, upper body or face; preserve natural left/right anatomy."),
)
_HEELS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    f"ecommerce-footwear-heels-{index + 1:02d}": replace(
        FOOTWEAR_ECOMMERCE_TEMPLATES[index if index < 6 else 6 if index == 6 else 7],
        id=f"ecommerce-footwear-heels-{index + 1:02d}", name=_HEELS_NAMES[index],
        description=f"Reviewed Heels Ecommerce composition: {_HEELS_NAMES[index]}.",
        applicable_families=("heels",), reference_object_key=f"docs/heels-output-details/references/{index + 1:02d}_" + ("three_quarter_product" if index == 0 else "side_profile_toe_left" if index == 1 else "side_profile_toe_right" if index == 2 else "front_view" if index == 3 else "rear_view" if index == 4 else "top_view" if index == 5 else "front_on_feet" if index == 6 else "side_on_feet") + ".png",
        presentation_mode=_HEELS_MODES[index], output_presentation="worn_product" if _HEELS_MODES[index] == "model" else "product_only",
        output_details=_HEELS_DETAILS[index], required_evidence=_HEELS_EVIDENCE[index],
        required_product_fields=("product_type", "global_details.colour", "global_details.materials", "global_details.construction", "category_details", "category_details.toe_shape", "category_details.sole_type"),
        prompt_format_rules=("The product reference images are the primary authority for every visible footwear feature.", "Use the template only for composition and presentation, never for footwear identity.", _HEELS_FIDELITY, "Uncertainty applies only to genuinely hidden, obstructed, cropped or unassessable details."),
        version=2,
    ) for index in range(8)
}


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
    "category_details.inseam_length",
    "category_details.leg_opening",
    "category_details.drawcord_details",
    "category_details.shorts_length",
    "category_details.visible_uncertainties",
)
_BOTTOMS_RULES = (
    "The product reference images are the primary authority for every visible feature.",
    "Product identity data must be presented before presentation instructions.",
    "Preserve the observed waistband, waist height, rise, leg shape, leg width, garment length, hem, pockets, closures, belt loops, pleats, darts, panels and seams.",
    "Use the template only for composition and presentation, never for product identity.",
    "Preserve visible graphics, logos, embroidery, appliques, patterns, washes and colour boundaries exactly as shown in the product references.",
    "For model-worn templates, use a real model and keep the framing limited to the waist or lower midsection downward; do not turn the output into a face-led or full-body portrait.",
    "When a template specifies an invisible mannequin, the mannequin must be fully invisible; a visible torso is a headless mannequin and is not interchangeable with an invisible mannequin.",
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


def _shorts_template(*, number: int, name: str, description: str, instructions: str, base_index: int, required: tuple[str, ...] = (), artwork_surface_mode: str = "flat", output_presentation: str = "product_only") -> GenerationTemplate:
    base = BOTTOMS_ECOMMERCE_TEMPLATES[base_index]
    return replace(
        base,
        id=f"ecommerce-bottoms-shorts-{number:02d}",
        name=name,
        description=description,
        prompt_instructions=instructions,
        required_product_fields=_BOTTOMS_REQUIRED_FIELDS + required,
        applicable_families=("shorts",),
        artwork_surface_mode=artwork_surface_mode,
        output_presentation=output_presentation,
        version=2,
    )


SHORTS_ECOMMERCE_TEMPLATES: Final[tuple[GenerationTemplate, ...]] = (
    _shorts_template(number=1, name="Flat-Laid Product", description="A complete pair of shorts laid flat as a product-only studio photograph.", base_index=0, instructions="Create ONE photorealistic product-only studio photograph of the exact shorts laid flat and front-facing on a clean neutral surface. Show the complete waistband, elastic construction, drawcord, front closure seam, slanted pockets, leg shape, inseam and both hems. Preserve the exact colour, textured fabric and proportions. No model, mannequin, body, props, collage or multiple views."),
    _shorts_template(number=2, name="Front Invisible Mannequin", description="A complete front view of the shorts shaped by an invisible mannequin.", base_index=0, instructions="Create ONE photorealistic straight front ecommerce photograph of the exact shorts shaped by a completely invisible mannequin, not a headless mannequin. Preserve natural waistband, rise, pocket, leg and hem volume, but show no mannequin, head, torso, legs or support. Show only the garment against a clean neutral studio background. No model, props, collage or multiple views."),
    _shorts_template(number=3, name="Three-Quarter Invisible Mannequin", description="A three-quarter product view of the shorts shaped by an invisible mannequin.", base_index=2, instructions="Create ONE photorealistic three-quarter front product photograph of the exact shorts shaped by a completely invisible mannequin, not a headless mannequin. Show the waistband, drawcord, nearest slanted pocket, side profile, leg opening and depth. Keep the mannequin completely invisible and preserve the exact textured fabric and construction. No person, support, props, collage or multiple views.", artwork_surface_mode="angled"),
    _shorts_template(number=4, name="Rear Invisible Mannequin", description="A complete rear view of the shorts shaped by an invisible mannequin.", base_index=1, instructions="Create ONE photorealistic straight rear ecommerce photograph of the exact shorts shaped by a completely invisible mannequin, not a headless mannequin. Show the rear waistband, seat, centre-back seam, leg shape and both hems. Keep every body part and mannequin support invisible; do not invent rear pockets or labels. No person, props, collage or multiple views.", artwork_surface_mode="rear"),
    _shorts_template(number=5, name="Front-Facing Model", description="A waist-down front-facing model view of the shorts.", base_index=4, instructions="Show the exact shorts worn by an adult model in a straight front-facing ecommerce pose. Frame from the lower torso to below both hems; exclude the face, head, shoulders and chest. Use a plain grey T-shirt and clean white low-top sneakers as restrained styling, matching the benchmark composition. Keep hands at the sides and show the waistband, drawcord, pockets, fit and hems clearly. No collage or multiple views.", required=("category_details.garment_length", "category_details.fit_and_silhouette"), artwork_surface_mode="worn", output_presentation="worn_product"),
    _shorts_template(number=6, name="Three-Quarter Full-Length Model", description="A full-length three-quarter model view showing the shorts in outfit context.", base_index=2, instructions="Show the exact shorts worn by an adult model in a relaxed three-quarter stance, full length from the neck down to the feet, with the face and facial features excluded. Match the benchmark's plain grey T-shirt, white low-top sneakers, neutral studio background and restrained styling. Keep the shorts prominent and preserve the waistband, drawcord, pockets, textured fabric, leg shape and hems. One photograph only, no collage.", required=("category_details.garment_length", "category_details.fit_and_silhouette"), artwork_surface_mode="worn", output_presentation="worn_product"),
    _shorts_template(number=7, name="Rear-Facing Model", description="A waist-down rear-facing model view of the shorts.", base_index=5, instructions="Show the exact shorts worn by an adult model facing directly away from the camera. Frame from the lower torso to below both hems; exclude the head and face. Match the neutral studio styling, including a plain grey crew-neck T-shirt covering the torso, and show the rear waistband, seat, centre-back seam, leg shape and hems clearly. The model must not be shirtless or show a bare upper body. Do not invent rear pockets or other construction. No collage or multiple views.", required=("category_details.garment_length", "category_details.fit_and_silhouette"), artwork_surface_mode="worn", output_presentation="worn_product"),
    _shorts_template(number=8, name="Full-Length Front-Facing Model", description="A full-length straight-on model view showing the complete outfit and shorts fit.", base_index=4, instructions="Show the exact shorts worn by an adult model in a straight front-facing full-length ecommerce photograph from the neck down to the feet, with the face excluded. Match the benchmark's plain grey T-shirt, white low-top sneakers and neutral studio setting. Keep the shorts clearly readable and preserve the waistband, drawcord, pockets, rise, textured fabric, leg openings and hems. One photograph only, no collage.", required=("category_details.garment_length", "category_details.fit_and_silhouette"), artwork_surface_mode="worn", output_presentation="worn_product"),
    _shorts_template(number=9, name="Waistband & Closure Detail", description="A close-up of the shorts waistband, drawcord, closure and upper front construction.", base_index=6, instructions="Create ONE tight photorealistic ecommerce construction detail of the exact shorts' upper front. Show the elastic waistband, white drawcord and metal tips, front closure seam, rise, upper pocket edge and textured fabric. Match the benchmark close-up framing and lighting. Do not show a face, full outfit, mannequin, invented fastenings, collage or inset; output one photograph only.", required=("category_details.waist_height", "category_details.fly_or_closure"), artwork_surface_mode="detail"),
)

def _joggers_template(*, number: int, name: str, description: str, instructions: str, base_index: int, required: tuple[str, ...] = (), artwork_surface_mode: str = "flat", output_presentation: str = "product_only") -> GenerationTemplate:
    base = BOTTOMS_ECOMMERCE_TEMPLATES[base_index]
    return replace(
        base,
        id=f"ecommerce-bottoms-joggers-{number:02d}",
        name=name,
        description=description,
        prompt_instructions=instructions,
        required_product_fields=_BOTTOMS_REQUIRED_FIELDS + required,
        applicable_families=("casual_bottoms",),
        artwork_surface_mode=artwork_surface_mode,
        output_presentation=output_presentation,
        version=2,
    )


JOGGERS_ECOMMERCE_TEMPLATES: Final[tuple[GenerationTemplate, ...]] = (
    _joggers_template(number=1, name="Flat-Laid Product", description="Complete joggers laid flat showing the front shape, waistband, pockets and cuffs.", base_index=0, instructions="Create ONE photorealistic product-only studio photograph of the exact joggers laid flat and front-facing on a clean neutral surface. Show the full front shape, elastic waistband, drawcord, angled pockets, soft tapered legs and ribbed ankle cuffs. Preserve the exact cream colour, soft fabric texture, proportions and construction. No model, mannequin, body, props, collage or multiple views."),
    _joggers_template(number=2, name="Front Invisible Mannequin", description="Front joggers view with natural garment volume and no visible mannequin.", base_index=0, instructions="Create ONE photorealistic straight front ecommerce photograph of the exact joggers shaped by a completely invisible mannequin, not a headless mannequin. Preserve natural waistband, drawcord, pocket, leg and cuff volume, but show no mannequin, head, torso, legs or support. Show only the garment against a clean neutral studio background. No model, props, collage or multiple views."),
    _joggers_template(number=3, name="Three-Quarter Invisible Mannequin", description="Angled front joggers view highlighting the pocket, side profile and leg taper.", base_index=2, instructions="Create ONE photorealistic three-quarter front product photograph of the exact joggers shaped by a completely invisible mannequin, not a headless mannequin. Highlight the nearest angled pocket, side profile, relaxed-to-tapered leg shape and ribbed ankle cuff while keeping the waistband and drawcord visible. Preserve the exact soft fabric texture and cream colour. Keep the mannequin completely invisible. No person, support, props, collage or multiple views.", artwork_surface_mode="angled"),
    _joggers_template(number=4, name="Rear Invisible Mannequin", description="Rear joggers view showing the seat, waistband and cuffs with approximated rear details.", base_index=1, instructions="Create ONE photorealistic straight rear ecommerce photograph of the exact joggers shaped by a completely invisible mannequin, not a headless mannequin. Show the rear waistband, seat, centre-back construction, leg shape and ribbed ankle cuffs. Rear details are approximated only from the product references; do not invent rear pockets, labels or panels. Keep every body part and mannequin support invisible. No person, props, collage or multiple views.", artwork_surface_mode="rear"),
    _joggers_template(number=5, name="Front-Facing Model", description="Lower-torso-to-feet model view showing the joggers' fit with neutral footwear.", base_index=4, instructions="Show the exact joggers worn by an adult model in a straight front-facing ecommerce pose. Frame from the lower torso to the feet; exclude the face, head, shoulders and chest. The model must wear a plain white T-shirt and neutral white low-top footwear. Show the waistband, drawcord, pockets, fit, leg taper and ribbed cuffs clearly. No collage or multiple views.", required=("category_details.garment_length", "category_details.fit_and_silhouette"), artwork_surface_mode="worn", output_presentation="worn_product"),
    _joggers_template(number=6, name="Three-Quarter Model", description="Neck-to-feet angled model pose showing the joggers' fit and drape.", base_index=2, instructions="Show the exact joggers worn by an adult model in a relaxed three-quarter angled pose from the neck to the feet, with the face and facial features excluded. Match the benchmark styling: a plain white T-shirt, neutral white low-top footwear and a clean studio background. Preserve the joggers' waistband, drawcord, pockets, soft drape, leg taper and ribbed cuffs. Keep the product prominent. One photograph only, no collage.", required=("category_details.garment_length", "category_details.fit_and_silhouette"), artwork_surface_mode="worn", output_presentation="worn_product"),
    _joggers_template(number=7, name="Rear-Facing Model", description="Rear model view showing the joggers' seat and leg fit with approximated rear details.", base_index=5, instructions="Show the exact joggers worn by an adult model facing directly away from the camera. Frame from the neck to the feet, excluding the head and face. The model must wear a plain white T-shirt and neutral white low-top footwear. Show the rear waistband, seat, leg fit, soft drape and ribbed ankle cuffs; approximate hidden rear details only from the references and do not invent pockets or panels. No collage or multiple views.", required=("category_details.garment_length", "category_details.fit_and_silhouette"), artwork_surface_mode="worn", output_presentation="worn_product"),
    _joggers_template(number=8, name="Full-Length Front Model", description="Straight front model view from neck to feet with a plain white T-shirt.", base_index=4, instructions="Show the exact joggers worn by an adult model in a straight front-facing full-length ecommerce photograph from the neck to the feet, with the face excluded. The model must wear a plain white T-shirt and neutral white low-top footwear against a clean studio background. Preserve the waistband, drawcord, pockets, soft fabric, leg shape, taper and ribbed ankle cuffs. One photograph only, no collage.", required=("category_details.garment_length", "category_details.fit_and_silhouette"), artwork_surface_mode="worn", output_presentation="worn_product"),
    _joggers_template(number=9, name="Folded Top-Down Product", description="Folded joggers photographed from above, showing the waistband, pockets and fabric.", base_index=3, instructions="Create ONE photorealistic top-down product photograph of the exact joggers neatly folded on a clean neutral surface. Keep the elastic waistband, drawcord, angled pocket edges, soft fabric texture and folded leg or cuff structure readable. Match the benchmark's compact folded composition and natural contact shadows. Do not show a model, mannequin, body, props, collage or multiple views.", artwork_surface_mode="folded"),
)

def _skirts_template(*, number: int, name: str, description: str, instructions: str, base_index: int, artwork_surface_mode: str = "flat", output_presentation: str = "product_only") -> GenerationTemplate:
    base = BOTTOMS_ECOMMERCE_TEMPLATES[base_index]
    return replace(
        base,
        id=f"ecommerce-bottoms-skirts-{number:02d}",
        name=name,
        description=description,
        prompt_instructions=instructions,
        required_product_fields=_BOTTOMS_REQUIRED_FIELDS,
        applicable_families=("skirts",),
        artwork_surface_mode=artwork_surface_mode,
        output_presentation=output_presentation,
        version=2,
    )


SKIRTS_ECOMMERCE_TEMPLATES: Final[tuple[GenerationTemplate, ...]] = (
    _skirts_template(number=1, name="Front Product", description="Product-only close front view of the structured pleated skirt.", base_index=0, instructions="Create ONE photorealistic product-only close front studio photograph of the exact skirt against a clean white or neutral background. Show the structured waistband, belt loops, button and front-fly construction, vertical pleats or panels, flared silhouette and hem. Preserve the exact brown/taupe colour, material texture, proportions and stitching. No person, mannequin, body, props, collage or multiple views."),
    _skirts_template(number=2, name="Back Product", description="Product-only close rear view of the structured pleated skirt.", base_index=1, instructions="Create ONE photorealistic product-only close rear studio photograph of the exact skirt against a clean white or neutral background. Show the rear waistband, belt loops, vertical panels or pleats, flared silhouette and hem. Do not invent rear pockets or hidden construction; approximate only what is supported by the references. No person, mannequin, body, props, collage or multiple views.", artwork_surface_mode="rear"),
    _skirts_template(number=3, name="Front Model", description="Cropped straight front model view of the skirt.", base_index=4, instructions="Show the exact skirt worn by an adult female model in a cropped straight front-facing ecommerce pose. Exclude the face and head while keeping the waistband, button and front-fly construction, pleats, flared silhouette and hem visible. Match the benchmark styling with a fitted black short-sleeve top and black ballet flats. Keep the model's hands holding the skirt edges naturally. One photograph only, no collage.", artwork_surface_mode="worn", output_presentation="worn_product"),
    _skirts_template(number=4, name="Back Model", description="Cropped straight rear model view of the skirt.", base_index=5, instructions="Show the exact skirt worn by an adult female model in a cropped straight rear-facing ecommerce pose, with the head and face excluded. Show the rear waistband, belt loops, back panels or pleats, fit, flare and hem clearly. Match the benchmark styling with a fitted black short-sleeve top and black ballet flats. Do not invent rear pockets or hidden construction. One photograph only, no collage.", artwork_surface_mode="worn", output_presentation="worn_product"),
    _skirts_template(number=5, name="Full Three-Quarter Model", description="Full-length three-quarter model view showing the skirt's fit and drape.", base_index=2, instructions="Show the exact skirt worn by an adult female model in a relaxed full-length three-quarter pose from the neck to the feet, with the face excluded. Match the benchmark styling: fitted black short-sleeve top and black ballet flats. Preserve the waistband, belt loops, button and front-fly details, pleats, flared silhouette, fabric drape and hem. Keep the skirt prominent. One photograph only, no collage.", artwork_surface_mode="worn", output_presentation="worn_product"),
    _skirts_template(number=6, name="Full Front Natural Model", description="Full-length straight front model view with natural relaxed arms.", base_index=4, instructions="Show the exact skirt worn by an adult female model in a full-length straight front-facing ecommerce photograph from the neck to the feet, with the face excluded. Match the benchmark styling with a fitted black short-sleeve top and black ballet flats. Keep both arms relaxed naturally at the sides. Preserve the waistband, belt loops, front button and fly, pleats, flared silhouette and hem. One photograph only, no collage.", artwork_surface_mode="worn", output_presentation="worn_product"),
)


def _leggings_template(*, number: int, name: str, description: str, instructions: str, base_index: int, artwork_surface_mode: str = "flat", output_presentation: str = "product_only") -> GenerationTemplate:
    base = BOTTOMS_ECOMMERCE_TEMPLATES[base_index]
    return replace(
        base,
        id=f"ecommerce-bottoms-leggings-{number:02d}",
        name=name,
        description=description,
        prompt_instructions=instructions,
        required_product_fields=_BOTTOMS_REQUIRED_FIELDS,
        applicable_families=("leggings",),
        artwork_surface_mode=artwork_surface_mode,
        output_presentation=output_presentation,
        version=2,
    )


LEGGINGS_ECOMMERCE_TEMPLATES: Final[tuple[GenerationTemplate, ...]] = (
    _leggings_template(number=1, name="Cropped Front Model", description="Cropped straight front model view of fitted leggings.", base_index=4, instructions="Show the exact leggings worn by an adult female model in a straight front-facing ecommerce pose, cropped from the lower torso to the feet with the face, head, shoulders and chest excluded. Preserve the model's body proportions, plain white T-shirt, white footwear, relaxed hands outside the garment and the leggings' smooth opaque cream stretch fabric, high-rise waistband, close fit and narrow ankle hems. One photograph only, no collage.", artwork_surface_mode="worn", output_presentation="worn_product"),
    _leggings_template(number=2, name="Front Flat-Lay Product", description="Product-only front flat-lay view of the complete leggings.", base_index=0, instructions="Create ONE photorealistic product-only front flat-lay photograph of the exact leggings on a clean neutral surface. Show the complete high-rise waistband, close-fitting hips and legs, narrow stitched ankle hems and minimal tonal seams. Preserve the warm pale cream-beige colour and opaque matte smooth stretch jersey. No body, model, mannequin, props, collage or multiple views."),
    _leggings_template(number=3, name="Rear Invisible Mannequin", description="Straight rear product view on an invisible mannequin.", base_index=1, instructions="Create ONE photorealistic straight rear product photograph of the exact leggings on a completely invisible mannequin, not a headless mannequin. Show the high-rise waistband, centre-back seam, fitted seat, legs and narrow ankle hems. Rear details are approximated only from the product references. Make all mannequin body parts and support invisible. No person, props, collage or multiple views.", artwork_surface_mode="rear"),
    _leggings_template(number=4, name="Three-Quarter Front Invisible Mannequin", description="Angled front product view on an invisible mannequin.", base_index=2, instructions="Create ONE photorealistic three-quarter front product photograph of the exact leggings on a completely invisible mannequin, not a headless mannequin. Highlight the side seam, hip and leg silhouette, close fit and narrow ankle hem while preserving the high-rise waistband. Keep the mannequin completely invisible and preserve the smooth matte stretch jersey. No person, support, props, collage or multiple views.", artwork_surface_mode="angled"),
    _leggings_template(number=5, name="Front Invisible Mannequin", description="Straight front product view with natural leggings volume.", base_index=0, instructions="Create ONE photorealistic straight front product photograph of the exact leggings shaped by a completely invisible mannequin, not a headless mannequin. Preserve natural high-rise waistband and close-fitting leg volume, but show no mannequin, head, torso, legs or support. Show only the leggings against a clean neutral studio background. No pockets, drawcord, ribbed cuffs, logos, props or multiple views."),
    _leggings_template(number=6, name="Folded Top-Down Product", description="Neatly folded leggings photographed from directly above.", base_index=3, instructions="Create ONE photorealistic true top-down product photograph of the exact leggings neatly folded on a clean neutral surface. Show the broad smooth waistband, minimal tonal seams, opaque matte stretch fabric and plain folded ankle hems. Preserve the compact folded positioning and neutral backdrop. No person, mannequin, props, collage or multiple views.", artwork_surface_mode="folded"),
    _leggings_template(number=7, name="Cropped Rear Model", description="Cropped straight rear model view of fitted leggings.", base_index=5, instructions="Show the exact leggings worn by an adult female model in a straight rear-facing ecommerce pose, cropped from the lower torso to the feet with the head and face excluded. Preserve the model's body proportions, plain white T-shirt, white footwear and relaxed hands outside the garment. Show the high-rise waistband, rear seam, fitted seat and narrow ankle hems. Rear details are approximated only from the references. One photograph only, no collage.", artwork_surface_mode="worn", output_presentation="worn_product"),
    _leggings_template(number=8, name="Full-Length Front Model", description="Straight front model view from neck to feet.", base_index=4, instructions="Show the exact leggings worn by an adult female model in a straight front-facing full-length ecommerce photograph from the neck to the feet, with the face excluded. The model must wear a plain white T-shirt, white footwear and both hands relaxed outside the garment. Preserve the high-rise waistband, smooth opaque cream stretch jersey, close fit, minimal seams and narrow ankle hems. One photograph only, no collage.", artwork_surface_mode="worn", output_presentation="worn_product"),
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
        return _support_required_evidence("footwear", template_id)
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
    "shirts": ("front_model", "folded", "shirts_flat_lay", "front_model", "seated_model", "cuff_detail_worn", "fabric_detail", "front_mannequin", "collar_placket_detail", "cuff_adjustment_worn", "angled_model", "angled_product", "rear_product", "rear_model"),
    "t-shirts-casual-tops": ("flat_lay_product", "hem_fit_detail", "folded_product", "front_model_pocket", "front_invisible_mannequin", "rear_model", "angled_invisible_mannequin", "fabric_texture_detail", "rear_invisible_mannequin"),
    "sleeveless-tops": ("rear_model", "front_model", "sleeveless_angled_invisible_mannequin", "headless_mannequin", "sleeveless_flat_lay", "styled_model"),
    "knitwear": ("folded", "neckline_detail", "front_model", "flat_product", "rear_angled_model", "fabric_detail", "seated_model", "flat_product", "rear_mannequin", "front_mannequin", "styled_model"),
    "hoodies": ("flat_product", "front_mannequin", "rear_mannequin", "angled_mannequin", "front_model", "rear_model", "angled_model", "rear_action", "front_action", "front_model", "seated_angled_model", "full_length_model"),
}

_TOPS_FAMILY_TEMPLATE_NUMBERS: Final[dict[str, tuple[int, ...]]] = {
    "t-shirts-casual-tops": (1, 2, 3, 4, 5, 6, 8, 9, 10),
}

_TOPS_FAMILY_PROFILE_BASES: Final[dict[str, str]] = {
    "folded": "ecommerce-tops-folded-view",
    "folded_product": "ecommerce-tops-folded-view",
    "flat_product": "ecommerce-tops-front-view",
    "front_product_shaped": "ecommerce-tops-front-view",
    "flat_lay_product": "ecommerce-tops-front-view",
    "front_product_straight_on": "ecommerce-tops-front-view",
    "front_product": "ecommerce-tops-front-view",
    "front_invisible_mannequin": "ecommerce-tops-front-view",
    "angled_invisible_mannequin": "ecommerce-tops-front-view",
    "sleeveless_angled_invisible_mannequin": "ecommerce-tops-front-view",
    "sleeveless_flat_lay": "ecommerce-tops-front-view",
    "shirts_flat_lay": "ecommerce-tops-front-view",
    "cuff_detail_worn": "ecommerce-tops-close-up",
    "collar_placket_detail": "ecommerce-tops-close-up",
    "cuff_adjustment_worn": "ecommerce-tops-close-up",
    "front_mannequin": "ecommerce-tops-front-view",
    "headless_mannequin": "ecommerce-tops-front-view",
    "rear_product": "ecommerce-tops-back",
    "rear_invisible_mannequin": "ecommerce-tops-back",
    "rear_mannequin": "ecommerce-tops-back",
    "front_model": "ecommerce-tops-front-model",
    "front_model_pocket": "ecommerce-tops-front-model",
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
    "hem_fit_detail": "ecommerce-tops-close-up",
    "neckline_detail": "ecommerce-tops-close-up",
    "fabric_detail": "ecommerce-tops-fabric",
    "fabric_texture_detail": "ecommerce-tops-fabric",
}

_TOPS_FAMILY_NAMES: Final[dict[str, tuple[str, ...]]] = {
    "shirts": ("Styled Front Model", "Folded Shirt", "Flat-Lay Shirt", "Front Model", "Seated Model", "Cuff Detail", "Fabric Texture Detail", "Front Invisible Mannequin", "Collar & Button Placket Detail", "Cuff Adjustment Detail", "Side / Three-Quarter Model", "Side / Three-Quarter Product", "Rear Product", "Rear Model"),
    "t-shirts-casual-tops": ("Front Product", "Hem & Fit Detail", "Folded T-Shirt", "Front Model (Hand in Pocket)", "Front Invisible Mannequin", "Rear Model", "Side / Three-Quarter Invisible Mannequin", "Fabric Texture Detail", "Rear Invisible Mannequin"),
    "sleeveless-tops": ("Rear Model", "Front Model", "3/4 View Invisible Mannequin", "Front Headless Mannequin", "Front Product", "Styled Model"),
    "knitwear": ("Folded Knitwear", "Neckline Detail", "Front Model", "Front Product", "Rear Three-Quarter Model", "Knit Fabric Detail", "Seated Styled Model", "Flat-Lay Knitwear", "Rear Invisible Mannequin", "Front Invisible Mannequin", "Styled Model"),
    "hoodies": ("Flat Product", "Front Invisible Mannequin", "Rear Invisible Mannequin", "Three-Quarter Invisible Mannequin", "Front Model", "Rear Model", "Three-Quarter Model", "Rear Model Adjusting Hood", "Front Model Adjusting Hood", "Model with Hands in Pockets", "Seated Three-Quarter Model", "Full-Length Model"),
}

_SHIRTS_TEMPLATE_REFERENCE_PATHS: Final[tuple[str, ...]] = tuple(
    f"apps/web/public/output-examples/tops/shirts/shirts-ecom-{index + 2:02d}-{filename}.png"
    for index, filename in enumerate((
        "styled-front-model", "folded-product-cuff-visible", "flat-lay-full-product", "front-model-studio",
        "lifestyle-seated-model", "detail-barrel-cuff", "detail-poplin-fabric-fold", "invisible-mannequin-front",
        "detail-collar-button-placket", "detail-cuff-adjustment", "side-three-quarter-model", "side-three-quarter-product",
        "rear-product", "rear-model",
    ))
)

_TSHIRTS_TEMPLATE_REFERENCE_PATHS: Final[tuple[str, ...]] = tuple(
    f"apps/web/public/output-examples/tops/t-shirts-casual/t-shirts-casual-ecom-{number:02d}-{filename}.png"
    for number, filename in (
        (1, "front-product-shaped"), (2, "hem-fit-detail-model"), (3, "folded-product"),
        (4, "front-model"), (5, "front-invisible-mannequin"), (6, "rear-model"),
        (8, "side-three-quarter-invisible-mannequin"), (9, "fabric-knit-texture-detail"),
        (10, "rear-invisible-mannequin"),
    )
)

_TSHIRTS_PRESENTATION_MODES: Final[tuple[str, ...]] = (
    "garment", "model", "garment", "model", "invisible_mannequin",
    "model", "invisible_mannequin", "garment", "invisible_mannequin",
)

_SLEEVELESS_TEMPLATE_REFERENCE_PATHS: Final[tuple[str, ...]] = (
    "apps/web/public/output-examples/tops/sleeveless/sleeveless-ecom-01-rear-model.png",
    "apps/web/public/output-examples/tops/sleeveless/sleeveless-ecom-02-front-model.png",
    "apps/web/public/output-examples/tops/sleeveless/sleeveless-ecom-03-three-quarter-product.png",
    "apps/web/public/output-examples/tops/sleeveless/sleeveless-ecom-04-front-invisible-mannequin.png",
    "apps/web/public/output-examples/tops/sleeveless/sleeveless-ecom-07-front-product.png",
    "apps/web/public/output-examples/tops/sleeveless/sleeveless-ecom-06-styled-model-no-face.png",
)

_SLEEVELESS_PRESENTATION_MODES: Final[tuple[str, ...]] = (
    "model", "model", "invisible_mannequin", "mannequin", "garment", "model",
)

_KNITWEAR_TEMPLATE_REFERENCE_PATHS: Final[tuple[str, ...]] = tuple(
    f"apps/web/public/output-examples/tops/knitwear/knitwear-ecom-{index:02d}-{filename}.png"
    for index, filename in enumerate((
        "folded-product", "neckline-detail", "front-model", "front-product",
        "rear-three-quarter-model", "knit-fabric-detail", "seated-styled-model",
        "flat-lay-full-product", "rear-invisible-mannequin", "front-invisible-mannequin",
        "styled-model",
    ), start=1)
)

_KNITWEAR_PRESENTATION_MODES: Final[tuple[str, ...]] = (
    "garment", "garment", "model", "model", "model", "garment",
    "model", "garment", "invisible_mannequin", "invisible_mannequin", "model",
)

_HOODIES_TEMPLATE_REFERENCE_PATHS: Final[tuple[str, ...]] = tuple(
    f"apps/web/public/output-examples/tops/hoodies/hoodies-ecom-{index:02d}-{filename}.png"
    for index, filename in enumerate((
        "flat-product", "front-invisible-mannequin", "back-invisible-mannequin",
        "three-quarter-invisible-mannequin", "front-model", "back-model",
        "three-quarter-model", "back-model-adjusting-hood", "front-model-adjusting-hood",
        "model-hands-in-trouser-pockets", "seated-three-quarter-model",
        "full-length-model-face-excluded",
    ), start=1)
)

_HOODIES_PRESENTATION_MODES: Final[tuple[str, ...]] = (
    "garment", "invisible_mannequin", "invisible_mannequin", "invisible_mannequin",
    "model", "model", "model", "model", "model", "model", "model", "model",
)

_SHIRTS_PRESENTATION_MODES: Final[tuple[str, ...]] = (
    "model", "garment", "garment", "model", "model", "model", "garment",
    "invisible_mannequin", "garment", "model", "model", "invisible_mannequin",
    "invisible_mannequin", "model",
)

_SHIRTS_OUTPUT_DETAILS: Final[tuple[str, ...]] = (
    "Subject: uploaded shirt worn by one adult model. Presentation: tucked into dark navy trousers with a simple brown belt; sleeves extended and cuffs closed where the product permits. Camera: approximately level with the chest, almost straight-on. Frame from the lower face to the upper thighs, including both hands; exclude the eyes and top of the head. Show the collar, shoulders, shirt front and both cuffs, with natural folds at the tuck. Background: Light warm beige studio backdrop approximately #C8C1B6.",
    "Subject: one neatly folded uploaded shirt. Present it on Background: Light warm beige studio backdrop approximately #C8C1B6. Use a directly overhead camera, centre the compact fold, keep the collar, upper placket, supported buttons and one actual cuff readable, with soft contact shadows and no accessories.",
    "Subject: complete uploaded shirt laid flat front-up. Use a directly overhead camera, collar at the top and hem at the bottom. Show the complete collar, body, sleeves, cuffs and hem with modest margins on a studio surface. Background: Light warm beige studio backdrop approximately #C8C1B6. Use shallow natural folds only; no mannequin or person.",
    "Subject: uploaded shirt worn untucked by one adult model. Presentation: relaxed standing pose, sleeves rolled to the forearms where the product permits, one hand in a trouser pocket and the other relaxed; plain light trousers remain secondary. Camera: chest-level near-front view with a slight torso turn. Frame from the lower face to the upper thighs; exclude the eyes and upper head, while retaining the collar, shirt hem and rolled sleeve ends. Background: Light warm beige studio backdrop approximately #C8C1B6.",
    "Subject: uploaded shirt worn by one seated adult model on a simple stool. Use a near-front, slightly elevated three-quarter view from the chin/base of neck through the lap and upper thighs. Keep collar, placket, forearms and shirt drape readable, with restrained trousers/belt styling and Background: Light warm beige studio backdrop approximately #C8C1B6.",
    "Subject: the uploaded shirt's actual cuff and adjacent sleeve while worn. Use a close oblique view from slightly above the wrist, with the cuff and fastening centred, the sleeve running diagonally and the hand visible. Exclude the face and full body; show actual cuff geometry, closure, stitching and sleeve pleats without forcing a cuff type.",
    "Subject: one continuous area of the uploaded shirt's actual fabric. Use a tight oblique macro view with soft rolling folds and shallow natural depth of field. Fill every frame edge with the real material; exclude the garment outline, model, mannequin and swatches; Background: Light warm beige studio backdrop approximately #C8C1B6.",
    "Subject: complete uploaded shirt shaped by a completely invisible mannequin. Use a straight front view at mid-garment height, with the entire collar-to-hem silhouette, both sleeves and cuffs visible. Centre the shirt with modest margins, natural three-dimensional volume and Background: Light warm beige studio backdrop approximately #C8C1B6; no body or support may be visible.",
    "Subject: the uploaded shirt's actual collar and upper front closure. Use a tight oblique product-only close-up, with collar construction and a short placket section sharply readable. Exclude the full garment, wearer and mannequin; Background: Light warm beige studio backdrop approximately #C8C1B6.",
    "Subject: the uploaded shirt's cuff being adjusted while worn. Use a close frontal chest-and-wrist view with one forearm raised and the opposite hand touching the cuff. Keep the cuff fastening and stitching unobscured, exclude the face and waist, and use soft lighting with Background: Light warm beige studio backdrop approximately #C8C1B6.",
    "Subject: uploaded shirt worn by one adult model in a standing front three-quarter pose. Use a chest-level camera approximately 30–45 degrees from front, crop strictly from the base of the neck to upper thighs, and show no face, facial features, eyes, nose, mouth, hair or top of head. Keep collar, front closure, near sleeve and cuff visible, and use restrained styling against Background: Light warm beige studio backdrop approximately #C8C1B6.",
    "Subject: complete uploaded shirt on a completely invisible mannequin. Use a front three-quarter view approximately 30–45 degrees from straight front, showing the front closure, near shoulder, sleeve, cuff and side depth. Keep the full shirt visible, with natural hollow garment volume and Background: Light warm beige studio backdrop approximately #C8C1B6; no person or visible support.",
    "Subject: complete back of the uploaded shirt on a completely invisible mannequin. Use a straight-on rear view, centred and square to camera, showing collar back, shoulders, back panel, sleeves, cuffs and hem. Preserve supported rear construction without inventing hidden details, against Background: Light warm beige studio backdrop approximately #C8C1B6.",
    "Subject: uploaded shirt worn by one adult model viewed straight from behind. Presentation: tucked into plain navy trousers with a brown belt, arms relaxed and sleeves extended where applicable. Use a straight rear camera from the lower back of the head/nape through the upper thighs; the lower back of the head may be visible but exclude the face and lower legs. Keep the collar back, shoulders, sleeves and cuffs clear; the tuck naturally conceals the hem. Background: Light warm beige studio backdrop approximately #C8C1B6.",
)

_TSHIRTS_OUTPUT_DETAILS: Final[tuple[str, ...]] = (
    'Subject: Complete uploaded T-shirt. Presentation: Front-up flat lay resting on a studio surface with both sleeves spread naturally. Camera angle: Directly overhead, perpendicular to the laid-out garment. View orientation: Front surface towards camera, neckline above hem. Framing: Entire T-shirt, both sleeves and complete hem visible. Crop: Do not clip any garment edge. Product position: Centred with body axis vertical. Product scale: Fill most of the frame with modest margins. Silhouette: Preserve actual laid-flat proportions; no inflated chest or cylindrical sleeve shaping. Visible construction: Actual neckline binding, shoulder seams, sleeve hems, bottom hem and supported artwork. Garment volume: Shallow natural folds and surface contact shadows only. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft even illumination with subtle shadows beneath garment edges. Colour treatment: Preserve exact uploaded colour, pattern and fabric finish. Composition: One unfolded product, no person, mannequin or accessories. Output: One continuous high-fidelity ecommerce photograph only.',
    "Subject: Lower front and hem of the uploaded T-shirt while worn. Presentation: Standing adult model wearing the T-shirt untucked over simple jeans, arms relaxed beside hips. Camera angle: Straight-on at lower torso height. View orientation: Front square to camera. Framing: Lower chest/abdomen through upper thighs, with hands beside the body. Crop: Intentionally exclude neckline, shoulders, head and lower legs; retain complete hem width. Product position: Hem crosses the lower-middle frame; shirt body occupies the upper area. Product scale: Hem stitching and local drape large and readable. Silhouette: Preserve actual hem contour and fit around the waist/hips. Visible construction: Hem seam, side seam if visible, material and lower-front artwork where present. Garment volume: Natural worn folds and a small overlap over jeans. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft even detail lighting with gentle fold shadows. Colour treatment: Preserve product colour and texture without transferring the example's blue. Composition: One worn hem detail; jeans and hands are secondary context. Output: One continuous high-fidelity ecommerce photograph only.",
    'Subject: One folded uploaded T-shirt. Presentation: Compact rectangular fold with neckline visible at the top and one sleeve folded diagonally across the image-left edge. Camera angle: Direct overhead view of the surface. View orientation: Front-up, neck at top. Framing: Entire folded arrangement surrounded by a narrow surface border. Crop: No clipped folded edges or neckline; unfolded hem may be concealed by folding. Product position: Centred and upright. Product scale: Folded product fills most of image height. Silhouette: Natural layered rectangle matching actual garment thickness. Visible construction: Actual neck shape/binding, displayed sleeve hem and front fabric/artwork where exposed. Garment volume: Low folded thickness with soft contact shadows. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft diffuse overhead light with restrained shadows beneath folds. Colour treatment: Preserve uploaded colour, texture and artwork across folds. Composition: One folded T-shirt; no detached sample, model or accessories. Output: One continuous high-fidelity ecommerce photograph only.',
    'Subject: Uploaded T-shirt worn in a relaxed standing pose. Presentation: One adult model in simple jeans, one hand in a trouser pocket, opposite arm relaxed; T-shirt untucked. Camera angle: Near-front at torso height, slight relaxed body turn. View orientation: Front dominant, no rear surface. Framing: Neck through upper thighs with shirt and sleeves visible. Crop: Exclude entire face/head and lower legs; preserve neckline, sleeve ends and visible hem. Product position: Torso centred, pocket-hand elbow angled outward on image right. Product scale: Shirt fills most of the upper frame with limited jean context below. Silhouette: Preserve actual fit with slight asymmetrical gathering near the pocket hand. Visible construction: Neckline, shoulder seams, sleeves, front artwork and hem where exposed. Garment volume: Natural chest and waist drape from the relaxed stance. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft studio light, gentle shadows, clear material detail. Colour treatment: Preserve true uploaded garment colour and artwork. Composition: One worn front view, simple jeans only as secondary styling. Output: One continuous high-fidelity ecommerce photograph only.',
    'Subject: Complete uploaded T-shirt. Presentation: Naturally shaped on a completely invisible mannequin, with hollow neckline and sleeves; no skin or support visible. Camera angle: Straight-on at mid-garment height. View orientation: Front square to camera. Framing: Complete neckline-to-hem silhouette and both sleeve ends. Crop: Do not crop garment extremities. Product position: Centred vertically and horizontally. Product scale: Large product with modest margins on every side. Silhouette: Preserve actual fit and proportions while showing three-dimensional chest and sleeve volume. Visible construction: Actual neckline, sleeve seams/hems, lower hem and front artwork. Garment volume: Rounded shoulders, cylindrical sleeves and natural torso drape, fully invisible supporting form. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft diffuse studio light with subtle volume shadows. Colour treatment: Preserve exact uploaded colour, fabric and surface treatment. Composition: One complete product, no human, visible mannequin, hanger or props. Output: One continuous high-fidelity ecommerce photograph only.',
    'Subject: Back of uploaded T-shirt while worn. Presentation: One standing adult model, back towards camera, untucked T-shirt over simple jeans, arms relaxed beside hips. Camera angle: Straight-on rear at torso height. View orientation: Back square to camera with shoulders level. Framing: Nape through upper thighs, including both hands. Crop: Exclude head and face; include full shirt back, sleeves and hem. Product position: Torso centred with arms outside shirt silhouette. Product scale: Shirt dominates frame; jeans supply limited context below hem. Silhouette: Preserve actual rear fit, width, length and drape. Visible construction: Rear neckline, shoulders, sleeve hems, bottom hem and supported rear artwork/seams. Garment volume: Natural worn back and waist folds. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft even illumination with restrained arm and fold shadows. Colour treatment: Preserve actual rear colour and pattern; do not transfer front artwork to the back. Composition: One rear-facing model, no face or additional view. Output: One continuous high-fidelity ecommerce photograph only.',
    'Subject: Complete uploaded T-shirt with front and side visible together. Presentation: Three-dimensional garment on a completely invisible mannequin; no person, skin or support visible. Camera angle: Front three-quarter, approximately 30–45 degrees from straight front. View orientation: Front turned towards image left; near side seam and sleeve opening visible on image right. Keep front artwork on the visible front surface. Framing: Entire T-shirt including neckline, both sleeves and hem. Crop: No clipped product edges. Product position: Complete silhouette centred with natural perspective asymmetry. Product scale: Large readable garment with a clear border around it. Silhouette: Preserve real proportions, with near sleeve broader and far side foreshortened by perspective. Visible construction: Front neckline, front fabric/artwork, near sleeve opening, side seam and hem. Garment volume: Rounded chest and shoulder, hollow sleeve openings and natural side drape. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft directional studio illumination revealing front-to-side depth. Colour treatment: Preserve exact product identity, artwork geometry and material colour. Composition: One front three-quarter product view; no rear view or straight-on substitute. Output: One continuous high-fidelity ecommerce photograph only.',
    "Subject: One continuous area of the uploaded T-shirt's fabric. Presentation: Material-only macro close-up with soft diagonal rolling folds. Camera angle: Shallow oblique macro view across the fabric surface. View orientation: Surface texture fills view; no full garment orientation. Framing: Fabric extends beyond all four image edges. Crop: Exclude garment silhouette, neckline, model, hands and studio surroundings. Product position: A low fabric ridge crosses the foreground with additional gentle folds behind it. Product scale: Knit or weave structure readable at realistic macro scale. Silhouette: Local material folds only. Visible construction: Actual yarn/weave/knit texture and surface finish, preserving markings present in the sampled area. Garment volume: Shallow continuous folds consistent with the actual material. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft grazing illumination with gentle depth of field and restrained valley shadows. Colour treatment: Preserve the actual textile colour and pattern; do not invent a different texture or print close-up. Composition: One unbroken material image; no model panel, full product panel, collage, grid, inset or swatch board. Output: One continuous high-fidelity macro ecommerce photograph only.",
    'Subject: Complete back of the uploaded T-shirt. Presentation: Natural three-dimensional shape on a completely invisible mannequin. Camera angle: Straight-on rear view at mid-garment height. View orientation: Back square to camera; front neckline and front artwork not displayed. Framing: Complete rear neckline, shoulders, sleeves and bottom hem. Crop: Do not clip any product edge. Product position: Centred with level shoulders and upright body axis. Product scale: Garment fills most of portrait frame with modest margins. Silhouette: Preserve actual rear width, sleeve proportions and length. Visible construction: Supported rear seams, neckline binding, sleeve hems, bottom hem and rear graphics if present. Garment volume: Soft shoulder and back volume, sleeves open naturally, no visible supporting body. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft diffuse light with subtle garment form shadows. Colour treatment: Preserve uploaded rear colour and artwork; no invented back design. Composition: One rear product view, no model, hanger or visible mannequin. Output: One continuous high-fidelity ecommerce photograph only.',
)

_SLEEVELESS_OUTPUT_DETAILS: Final[tuple[str, ...]] = (
    "Subject: Uploaded sleeveless top worn from the rear. Presentation: Standing adult model, arms relaxed alongside hips, top untucked over plain light trousers. Camera angle: Straight-on rear at torso height. View orientation: Back square to camera; face turned away. Framing: Lower back of head/nape through upper thighs with hands visible. Crop: Exclude face and upper head; retain full top, shoulder edges, armholes and hem. Product position: Back centred; hair kept clear of garment construction. Product scale: Top dominates the frame, trousers supply limited lower context. Silhouette: Preserve actual back width, length and fit. Visible construction: Supported rear neckline, armhole finishes, seams and hem; do not invent the example's centre seam. Garment volume: Natural worn back drape and slight waist folds. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft diffuse light with gentle arm and fold shadows. Colour treatment: Preserve uploaded colour, pattern and material finish. Composition: One rear-facing model; no extra product or alternate view. Output: One continuous high-fidelity ecommerce photograph only.",
    'Subject: Uploaded sleeveless top worn in a straight front stance. Presentation: Standing adult model, arms down, top untucked over plain light trousers. Camera angle: Straight-on at torso height. View orientation: Front square to camera with level shoulders. Framing: Neck through upper thighs, including hands. Crop: Exclude face and head; include neckline, armholes and entire hem. Product position: Top centred, arms separate from its outline. Product scale: Top fills the central and upper image with modest surrounding space. Silhouette: Preserve actual fit, width and length without making the product more fitted. Visible construction: Actual neckline binding, armhole finishes, darts/seams and hem where present. Garment volume: Natural worn chest and torso shape. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft even illumination with gentle form shadows. Colour treatment: Preserve exact uploaded colour, pattern, texture and finish. Composition: One front-facing model with minimal trouser context. Output: One continuous high-fidelity ecommerce photograph only.',
    'Subject: Complete uploaded sleeveless top. Presentation: Garment supported by a completely invisible mannequin; neckline and armholes hollow, no visible skin, torso or stand. Camera angle: Front three-quarter, approximately 30–45 degrees from straight front. View orientation: Front turned towards image left with the near armhole and side visible on image right. Framing: Entire shoulder-to-hem silhouette including both shoulder edges. Crop: No clipped garment edges. Product position: Centred, upright, with perspective depth across neckline and hem. Product scale: Large product with modest empty margins. Silhouette: Preserve actual body shape and armhole depth in perspective. Visible construction: Front neckline, near armhole, supported side seam/darts and hem. Garment volume: Natural chest depth and hollow openings, with no mannequin visible. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft directional studio illumination revealing side depth. Colour treatment: Preserve true uploaded material colour and texture. Composition: One front three-quarter product view, no person or visible support. Output: One continuous high-fidelity ecommerce photograph only.',
    "Subject: Uploaded sleeveless top on a visible fabric-covered display torso. Presentation: Cream linen-like headless, armless mannequin with cylindrical neck, shoulder stubs and lower torso visibly exposed around the garment. Camera angle: Straight-on at chest height. View orientation: Front square to camera. Framing: Top of mannequin neck through a small portion of mannequin waist below the garment hem. Crop: Retain full garment; lower mannequin torso may continue beyond frame. No stand or legs visible. Product position: Garment and mannequin centred with level shoulders. Product scale: Close product view with neckline, armholes and hem clearly readable. Silhouette: Preserve actual garment fit and shape over the physical display form. Visible construction: Actual neckline, armhole edges, seams, darts and hem; do not invent denim details. Garment volume: Visible mannequin gives natural chest/torso support; its cream surface remains visible in the neckline and armholes. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft even studio light preserving fabric texture and subtle contact shadows. Colour treatment: Preserve the top's true colour without transferring mannequin/background beige onto it. Composition: One top on one visible headless display torso; no human, face or invisible-mannequin substitution. Output: One continuous high-fidelity ecommerce photograph only.",
    'Subject: Complete uploaded sleeveless top laid flat. Presentation: Front-up product on a flat studio surface with shoulder edges and armhole contours naturally arranged. Camera angle: Directly overhead and perpendicular to the surface. View orientation: Front upwards, neckline at top and hem at bottom. Framing: Complete product with clear surrounding surface. Crop: No clipped shoulder, armhole edge or hem. Product position: Centred with body axis vertical. Product scale: Large and readable, leaving modest margins. Silhouette: Preserve actual laid-flat width and length, no inflated bust or torso. Visible construction: Supported neckline and armhole binding, seams/darts and hem. Garment volume: Shallow surface-supported folds and edge shadows only. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft overhead illumination and natural contact shadows. Colour treatment: Preserve uploaded colour, pattern and surface finish. Composition: One unfolded top, no mannequin, human, hanger or styling items. Output: One continuous high-fidelity ecommerce photograph only.',
    'Subject: Uploaded sleeveless top worn in a relaxed styled pose. Presentation: Adult model with both hands in pockets of plain light trousers, top untucked. Camera angle: Near-front, slightly three-quarter at torso height. View orientation: Front dominant with a little near-side depth; shoulders relaxed. Framing: Neck through hips and upper thighs. Crop: Exclude face/head and lower legs; keep full top and hem visible, hands may be hidden naturally in pockets. Product position: Top centred, elbows angled gently outward. Product scale: Shirt fills most of the image with limited trouser context beneath. Silhouette: Preserve actual fit while allowing slight pose-related asymmetry and drape. Visible construction: Actual neckline, armhole finish, front/side seams and hem. Garment volume: Natural worn torso shape and relaxed folds. Background: Light warm beige studio backdrop approximately #C8C1B6. Lighting: Soft diffuse studio lighting with gentle depth and clean detail. Colour treatment: Preserve actual product colour, texture and pattern. Composition: One model with minimal light-trouser styling and no additional accessories. Output: One continuous high-fidelity ecommerce photograph only.',
)

_KNITWEAR_OUTPUT_DETAILS: Final[tuple[str, ...]] = (
    'Subject: One folded uploaded knitwear garment. Presentation: Compact rectangular front-up fold; sleeves concealed beneath the body. Camera angle: Overhead. View orientation: Front-up, neckline at top. Framing: Complete folded stack. Crop: Keep folded edges and collar inside frame. Product position: Centred upright rectangle. Product scale: Fold fills most of the frame with generous surface margin. Silhouette: Soft rectangular layers, not an unfolded torso. Visible construction: Neck ribbing and inner back neckline; visible knit columns and lower fold. Garment volume: Shallow layered thickness and contact shadows. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: Product alone; no separate sleeve draped over the front. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded knitwear neckline and adjacent stitches. Presentation: Garment laid diagonally on a surface for a close detail. Camera angle: Close overhead/slightly oblique. View orientation: Front neckline arc rises toward image right. Framing: Tight collar and upper-chest detail. Crop: Crop most of garment; no full silhouette required. Product position: Neckline spans the upper/middle frame diagonally. Product scale: Stitches and collar edge large and readable. Silhouette: Curved neckline and fabric planes only. Visible construction: Front/back neck edge, inner reverse knit and adjacent stitch columns. Garment volume: Small folds and collar thickness. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One collar detail; no skin, model or inset. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded knitwear worn on a standing adult model. Presentation: Relaxed stance; image-left hand in trouser pocket, opposite arm down; sleeves pushed up. Camera angle: Torso-height, near straight-on. View orientation: Front with a slight body lean. Framing: Lower chin through upper/mid thighs. Crop: Benchmark includes chin/lower beard; exclude eyes and full face, retain hem and relaxed hand. Product position: Torso centred above charcoal trousers. Product scale: Garment dominates frame. Silhouette: Actual worn fit, untucked hem and asymmetrical sleeve gathering. Visible construction: Neckline, front knit, shoulder seams and hem; white underlayer sliver if compatible. Garment volume: Natural waist and forearm bunching. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One model; simple dark trousers and restrained underlayer. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded knitwear worn by an adult model, not product-only. Presentation: Standing with bent arms and hands loosely clasped over lower abdomen; tan trousers. Camera angle: Torso-height straight-on. View orientation: Front. Framing: Lower face to upper thighs. Crop: Lips/chin may appear as in benchmark; eyes excluded; retain both clasped hands and hem. Product position: Centred torso, hands over lower front. Product scale: Knitwear fills most of frame. Silhouette: Worn torso and full-length sleeves ending at wrists. Visible construction: Actual neckline, sleeves, knit and ribbed hem where present; hands obscure some lower front. Garment volume: Natural chest volume and elbow folds. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One worn product; do not remove model or clasped hands. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Back of uploaded knitwear worn by an adult model. Presentation: Standing turned away, head turned toward image left; arms lowered; dark jeans. Camera angle: Torso-height oblique rear. View orientation: Rear three-quarter; back dominant. Framing: Partial side head to upper thighs/seat. Crop: Partial nose/lips/chin, ear and hair may appear; no full face; retain sweater back and hem. Product position: Back centred with side perspective. Product scale: Garment dominates with jeans below. Silhouette: Natural shoulder-to-waist fit. Visible construction: Rear neckline, shoulders, sleeves and hem; white underlayer strip below hem if compatible. Garment volume: Worn back folds and sleeve bends. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One rear-oblique model, not a front or square-back shot. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Actual uploaded knitwear material at macro scale. Presentation: Continuous knit surface with softly rolling diagonal folds. Camera angle: Close macro, gently oblique. View orientation: Surface detail rather than garment front/rear. Framing: Fabric fills every edge. Crop: Exclude garment outline, neckline, cuffs and model. Product position: Diagonal ridges and valleys across frame. Product scale: Individual stitch loops clearly visible. Silhouette: No whole-garment silhouette. Visible construction: Actual knit gauge, yarn and stitch pattern; no invented coarse loops. Garment volume: Soft low folds revealing yarn relief. Background: None visible; actual knit material fills the frame. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One continuous macro surface; no collage, model or product inset. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded knitwear worn seated. Presentation: Relaxed reclining pose in wooden armchair with woven seat; image-left hand toward knee, other hand near waist/lap. Camera angle: Front three-quarter at seated torso height. View orientation: Front-oblique. Framing: Partial lower face through lap/upper legs. Crop: Benchmark includes lower nose/lips/chin; exclude full head, lower legs and shoes. Product position: Torso above lap, wooden chair arms at sides. Product scale: Knitwear central with enough chair context. Silhouette: Seated fit with waist compression. Visible construction: Neckline, sleeves and front knit; cream shirt collar/cuffs/hem where compatible. Garment volume: Natural gathered seated waist; some front obscured by arms. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One seated model, dark jeans and restrained cream shirt layer; chair remains visible. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Complete uploaded knitwear garment. Presentation: Unfolded front-up flat lay, sleeves spread down/out then slightly inward at cuffs. Camera angle: Direct overhead. View orientation: Front-up, neck above hem. Framing: Entire garment. Crop: Retain both cuffs, shoulders, neckline and hem. Product position: Body axis vertical, sleeves separated from body. Product scale: Most of frame with modest margins. Silhouette: Actual laid-flat proportions; no inflated torso. Visible construction: Actual collar, cuffs, hem, seams and knit pattern. Garment volume: Shallow rumples and surface-contact shadows. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One garment only, no mannequin or person. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Complete rear of uploaded knitwear. Presentation: Volumetrically shaped on an invisible form; sleeves hanging with slight bends. Camera angle: Straight-on at garment height. View orientation: Direct rear. Framing: Entire shaped garment. Crop: Retain neck, both cuffs and complete hem. Product position: Centred upright. Product scale: Large with modest clear border. Silhouette: Shoulder/back volume and tubular sleeves. Visible construction: Rear collar, back knit, sleeve seams, cuffs and hem; no front neck opening. Garment volume: Natural supported volume, not flat lay. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: Product only; no body, visible mannequin, hanger or stand. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Complete front of uploaded knitwear. Presentation: Invisible-form presentation; neckline hollow with inner back fabric visible. Camera angle: Straight-on at garment height. View orientation: Direct front. Framing: Entire garment. Crop: Retain collar, both cuffs and full hem. Product position: Centred with balanced shoulders. Product scale: Large with modest border. Silhouette: Supported chest and softly bent sleeves. Visible construction: Actual neckline, seams, knit, cuffs and hem. Garment volume: Natural three-dimensional torso and sleeve volume. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: No model, visible mannequin, hanger or stand. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded knitwear worn by an adult model. Presentation: Standing with arms crossed over chest, sleeves pushed up; dark trousers and braided belt. Camera angle: Near straight-on torso-height. View orientation: Front with head turned toward image left. Framing: Partial lower face to upper thighs. Crop: Partial nose/lips/chin and hair may appear; no full face or lower legs. Product position: Crossed forearms across centre, waist/belt below. Product scale: Upper body dominates. Silhouette: Natural fit with asymmetrical hem bunching. Visible construction: Neckline and visible knit; crossed arms obscure central chest. Garment volume: Forearm gathering and worn waist folds. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One model; subtle white neck underlayer, black trousers and belt secondary. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
)

_HOODIES_OUTPUT_DETAILS: Final[tuple[str, ...]] = (
    'Subject: Complete uploaded hoodie. Presentation: Front-up flat lay; hood spread upward with opening visible, sleeves laid down/out. Camera angle: Direct overhead. View orientation: Direct front-up. Framing: Whole garment. Crop: Retain hood tip, cuffs and hem. Product position: Centred vertically. Product scale: Large with narrow surface border. Silhouette: Flattened body and spread hood; not a worn torso. Visible construction: Actual hood seams, fastenings, pockets, cuffs and hem. Garment volume: Shallow fabric relief and contact shadows. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: Product alone, no model or mannequin. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Complete uploaded hoodie front. Presentation: Invisible-form torso, hood down around empty neckline, sleeves hanging. Camera angle: Straight-on garment-height. View orientation: Direct front. Framing: Whole shaped garment. Crop: Keep hood, cuffs and hem visible. Product position: Centred upright. Product scale: Large with modest margin. Silhouette: Supported chest and tubular sleeves. Visible construction: Actual front pocket/closure, hood opening and trim. Garment volume: Natural torso volume with elbow/wrist folds. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: No human, visible mannequin or support. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Complete uploaded hoodie back. Presentation: Invisible-form presentation with hood down over upper back. Camera angle: Straight-on garment-height. View orientation: Direct rear. Framing: Whole garment. Crop: Retain hood, sleeves, cuffs and hem. Product position: Centred upright. Product scale: Large with modest margin. Silhouette: Supported back, lowered sleeves. Visible construction: Actual rear hood seam, back panel and trim; do not invent front details on back. Garment volume: Soft back volume and sleeve folds. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: Product only, no person or visible form. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Complete uploaded hoodie. Presentation: Invisible form rotated modestly; front remains dominant, one side recedes. Camera angle: Shallow front three-quarter at garment height. View orientation: Front-oblique, not rear. Framing: Whole shaped garment. Crop: Retain full hood, cuffs and hem. Product position: Centred with natural perspective asymmetry. Product scale: Large with modest margin. Silhouette: Chest depth, side plane and angled hem. Visible construction: Front construction, hood opening, near sleeve and side seams where visible. Garment volume: Rounded torso, bent sleeves and open cuff ends. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One product without body or visible mannequin; avoid exaggerated side rotation. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded hoodie worn by an adult model. Presentation: Standing front, arms relaxed beside hips; hood down; black trousers. Camera angle: Straight-on torso-height. View orientation: Direct front. Framing: Neck through thighs. Crop: Exclude face; retain hands, full hoodie and hem. Product position: Torso centred. Product scale: Hoodie dominant, trousers secondary. Silhouette: Actual relaxed worn fit. Visible construction: Front hood opening, supported drawstrings/pockets/closure, cuffs and hem. Garment volume: Natural sleeve and waist folds. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One standing model, no props. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded hoodie worn by an adult model. Presentation: Standing away, arms down; hood resting on back; black trousers. Camera angle: Straight-on torso-height. View orientation: Direct rear. Framing: Nape/lower hair through thighs. Crop: Exclude face/full head; retain hands and hoodie hem. Product position: Back centred. Product scale: Hoodie dominates. Silhouette: Actual worn back and shoulder fit. Visible construction: Hood back, rear panel, sleeves and hem. Garment volume: Natural back drape and wrist folds. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One model, no front-view inset. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded hoodie worn by an adult model. Presentation: Slight front-oblique stance, both hands in trouser pockets, hood down. Camera angle: Torso-height front three-quarter. View orientation: Front and near side visible. Framing: Neck through thighs. Crop: Face excluded; hoodie hem retained. Product position: Torso tilted slightly, pockets at lower sides. Product scale: Upper body fills frame. Silhouette: Perspective on side and relaxed front. Visible construction: Front hood, pocket/closure and sleeve construction. Garment volume: Hip and elbow folds from pocket pose. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: Black trousers; hands in trousers, not hoodie pouch. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded hoodie worn from behind. Presentation: Both hands raised to hold edges of lowered hood, elbows outward; do not pull hood over head. Camera angle: Straight-on torso-height. View orientation: Direct rear. Framing: Nape/lower hair through thighs. Crop: Keep hands, elbows and hem inside frame; no face. Product position: Hood and back centred, elbows balanced. Product scale: Back occupies most of frame. Silhouette: Raised-arm shoulder width and intact back length. Visible construction: Hood rear seam and edge, back, cuffs and hem. Garment volume: Sleeve compression at elbows and gentle raised-arm folds. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One rear model adjusting hood, black trousers. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded hoodie worn by an adult model. Presentation: Both hands holding hood edges beside neck, elbows outward; hood down. Camera angle: Straight-on torso-height. View orientation: Front. Framing: Neck through thighs. Crop: Exclude face; keep hands, elbows and hem. Product position: Hands frame neckline without hiding central chest. Product scale: Torso fills most of frame. Silhouette: Raised-arm fit with natural waist shift. Visible construction: Hood opening, actual drawstrings/closure, pocket and cuffs. Garment volume: Elbow folds and slight tension toward hood. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One front model with black trousers; hood not worn over head. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded hoodie worn by an adult model. Presentation: Near-square front stance, both hands in black trouser pockets, hood down. Camera angle: Near straight-on torso-height. View orientation: Front, minimal rotation. Framing: Neck through thighs. Crop: Exclude face; retain full hoodie and wrists entering trouser pockets. Product position: Centred torso. Product scale: Garment dominant. Silhouette: Relaxed front with slight waist asymmetry. Visible construction: Hood opening, front pocket/closure and cuffs. Garment volume: Natural waist bunching and bent-sleeve folds. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: Hands in trouser pockets, not hoodie pocket; distinguish from angled slot 07. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded hoodie worn seated. Presentation: Seated on a plain light block, legs apart, hands resting on thighs; hood down. Camera angle: Seated torso-height, shallow front-oblique. View orientation: Front-dominant with angled lap/legs. Framing: Neck through lap and knees/upper lower legs. Crop: Exclude face and shoes; retain both hands and visible seat. Product position: Torso central above spread lap. Product scale: Closer seated crop, hoodie dominant. Silhouette: Seated waist compression and relaxed sleeves. Visible construction: Actual front construction; hem follows seated waist. Garment volume: Soft folds above hem and elbows. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: Black trousers and light cube seat; do not substitute standing pose. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
    'Subject: Uploaded hoodie in a standing outfit. Presentation: Relaxed stance, hands in hoodie pouch where present; black trousers and white trainers. Camera angle: Level full-outfit view. View orientation: Front. Framing: Neck through complete shoes. Crop: Face/head excluded; preserve shoes and ground margin. Product position: Centred standing figure with feet apart. Product scale: Smaller garment scale to fit full lower body. Silhouette: Actual hoodie fit above full trouser silhouette. Visible construction: Full hoodie, actual pockets and cuffs; hands must not require invented pockets. Garment volume: Natural bent-elbow and waist folds. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no props except those specified. Lighting: Soft diffused studio illumination with gentle dimensional shadows; retain readable fabric texture without harsh highlights. Colour treatment: Preserve uploaded garment hue, saturation, tonal depth and finish; no benchmark-colour transfer or beige cast on the product. Composition: One face-excluded full-length outfit; if uploaded hoodie lacks pockets, relax hands beside body. Output: One continuous high-fidelity ecommerce photograph; no collage, inset, labels or added graphics.',
)

_TOPS_FAMILY_PROFILE_INSTRUCTIONS: Final[dict[str, str]] = {
    "folded": "Present the top neatly folded as a product-only ecommerce image. Arrange the fold so the visible colour, material, neckline or collar and distinctive construction remain clear.",
    "folded_product": "Present ONE neatly folded T-shirt as a product-only ecommerce photograph on a clean studio surface. Keep the folded neckline, one sleeve edge and fabric surface clearly visible; do not show a model, mannequin, second garment, collage or multiple views.",
    "flat_product": "Present the complete top as a single product-only studio image, front-facing and fully visible from neckline to hem. Use natural three-dimensional shaping and a subtle contact shadow, but do not show a person, mannequin or body. Do not create a collage, grid, split-screen, montage or multiple views.",
    "front_product_shaped": "Present ONE complete T-shirt laid out as a product-only studio photograph. Keep it naturally three-dimensionally shaped with a subtle contact shadow, relaxed realistic fabric rather than a rigid technical flat lay, and the full neckline, sleeves and hem visible. No person, mannequin, props, second garment, collage or multiple views.",
    "flat_lay_product": "Present ONE complete T-shirt laid flat, front-up, on a clean studio surface in a true overhead ecommerce photograph. Keep the neckline at the top, the hem at the bottom, both sleeves and the complete hem visible. Use shallow natural folds and surface contact shadows only; do not inflate the chest, shape the garment on a mannequin or create cylindrical sleeve volume. No person, mannequin, props, second garment, collage or multiple views.",
    "front_product_straight_on": "Photograph ONE complete T-shirt as a product-only, perfectly centered straight-on front view. The camera faces the garment squarely; keep the neckline, both sleeves and full hem symmetrically visible with modest margins. No model, mannequin, body, props, perspective angle, collage or multiple views.",
    "front_product": "Present ONE complete T-shirt as a product-only front ecommerce photograph with the full silhouette from neckline to hem visible. Use a clean neutral studio background, natural garment volume and modest margins. No person, mannequin, props, second garment, collage or multiple views.",
    "front_invisible_mannequin": "Present ONE complete T-shirt on a completely invisible mannequin—not a visible headless mannequin—in a straight front ecommerce studio photograph. Preserve the filled shoulder, chest, sleeve and hem volume that the invisible mannequin provides, but make the mannequin, head, neck and body completely invisible. Show only the garment; no person, visible support, props, collage or multiple views.",
    "angled_invisible_mannequin": "Present ONE complete T-shirt on a completely invisible mannequin—not a visible headless mannequin—from a side or three-quarter product angle. Preserve the garment's natural shoulder, chest, sleeve and side volume while keeping the mannequin, head, neck and body completely invisible. Show only the garment; no person, visible support, props, collage or multiple views.",
    "sleeveless_angled_invisible_mannequin": "Present the complete sleeveless top on a completely invisible mannequin—not a visible headless mannequin—from a front three-quarter angle. Keep the neckline, both armholes, near side seam and full hem visible. Preserve natural chest and side volume while making the mannequin, neck, torso, body and support completely invisible. Show only the garment; no person, visible support, props, collage or multiple views.",
    "sleeveless_flat_lay": "Present the complete sleeveless top laid flat, front-up, on a clean studio surface in a true overhead ecommerce photograph. Keep the neckline at the top, the hem at the bottom, both shoulder edges and armholes fully visible. Use shallow natural folds and surface contact shadows only; do not inflate the bust, create torso volume or use a mannequin. No person, props, collage or multiple views.",
    "shirts_flat_lay": "Present the complete shirt laid flat, front-up, on a clean studio surface in a true overhead ecommerce photograph. Keep the collar at the top, the hem at the bottom, both sleeves, cuffs and the complete silhouette visible. Use shallow natural folds and surface contact shadows only; do not inflate the chest, create cylindrical sleeve volume or use a mannequin. No person, props, collage or multiple views.",
    "cuff_detail_worn": "Create a close worn detail of the uploaded shirt's actual cuff and adjacent sleeve. Show one real wrist and hand, with the cuff fastening, edge stitching, sleeve pleats and fabric grain clearly visible. Exclude the face and full body; do not force a barrel cuff or invent a closure. Output one continuous photograph only.",
    "collar_placket_detail": "Create a tight product-only close-up of the uploaded shirt's actual collar and upper button placket. Show the collar construction, placket layers, stitching, buttonholes and supported fastenings clearly. Do not show a model, hands or mannequin, and do not invent a button count or collar type. Output one continuous photograph only.",
    "cuff_adjustment_worn": "Create a close worn detail of the uploaded shirt's actual cuff being adjusted. Show one forearm raised across the torso and the opposite real hand touching the cuff without hiding its fastening or stitching. Exclude the face and waist; maintain anatomically coherent hands and do not invent cuff construction. Output one continuous photograph only.",
    "front_mannequin": "Present the complete front of the top shaped by a completely invisible mannequin—not a visible headless mannequin—in a straight ecommerce studio photograph. Preserve natural shoulder, chest, sleeve and hem volume, but make the mannequin, head, neck, torso and body completely invisible. Show only the garment; no person, visible support, hands, props, collage or multiple views.",
    "headless_mannequin": "Present the complete front of the sleeveless top on a visible fabric-covered headless mannequin. Keep the mannequin torso, shoulders and cylindrical neck support visible around the garment, but do not show a head, face, human model, hands or stand. Centre the product and keep its neckline, armholes, seams and hem fully visible.",
    "rear_product": "Present the complete rear of the top as a product-only studio image. Keep the back silhouette, shoulders, sleeves and hem fully visible.",
    "rear_invisible_mannequin": "Present ONE complete rear T-shirt on a completely invisible mannequin—not a visible headless mannequin—in a straight rear ecommerce studio photograph. Preserve the filled shoulder, back, sleeve and hem volume while making the mannequin, head, neck and body completely invisible. Show only the garment; no person, visible support, props, collage or multiple views.",
    "rear_mannequin": "Present the complete rear of the top on a completely invisible mannequin—not a visible headless mannequin. Do not show a face, visible body or mannequin support.",
    "front_model": "Show the top worn by a model in a simple front-facing studio presentation with the face excluded, cropped below the face. Keep styling minimal and make the garment fit, neckline, sleeves and hem clear.",
    "front_model_pocket": "Show the T-shirt worn by a model in a front-facing studio presentation with the face excluded. Pose the model naturally with one hand resting inside a trouser pocket and the other arm relaxed, while keeping the T-shirt front, neckline, sleeves and hem unobscured. Do not show the face or create a collage or multiple views.",
    "styled_model": "Show the top worn by a minimally styled model with the face excluded. Use a natural relaxed pose with restrained styling; keep the garment as the visual subject and preserve its complete visible silhouette. Do not create a collage, grid, split-screen, montage or multiple views.",
    "seated_model": "Show the top worn by a seated model with the face excluded. Keep the pose simple and ensure the garment's neckline, silhouette, sleeves and visible length remain clear.",
    "seated_angled_model": "Show the top worn by a seated model from a three-quarter angle, with the face excluded. Keep styling minimal and make the garment's depth and fit clear.",
    "full_length_model": "Show the top worn by a model in a full-length composition, excluding the face. Keep the entire garment visible and styling minimal.",
    "rear_model": "Show the top worn by a model in a rear-facing view with the face excluded. Crop below the head and clearly show the back, shoulders, sleeves and hem.",
    "rear_angled_model": "Show the top worn by a model from a rear three-quarter angle, excluding the face. Clearly show the back construction, shoulder shape and drape.",
    "angled_model": "Show the top worn by a model from a side or three-quarter angle, cropped below the face. Make the garment's depth, silhouette and fit clear.",
    "angled_product": "Present the complete top as a product-only side or three-quarter studio view. Keep the silhouette, neckline, sleeves and hem visible.",
    "angled_mannequin": "Present the top on a completely invisible mannequin—not a visible headless mannequin—from a three-quarter angle. Keep the garment's construction and silhouette clear without showing a face.",
    "front_action": "Show the top worn by a model from the front, cropped below the face, while the model naturally adjusts the hood. Keep the garment unobscured and preserve the hood construction.",
    "rear_action": "Show the top worn by a model from the rear, excluding the face, while the model naturally adjusts the hood. Keep the back and hood construction visible.",
    "construction_detail": "Create a tight ecommerce detail of the visible construction feature shown by the template, such as a cuff, collar, placket or fastening. Do not invent a feature.",
    "hem_detail": "Create a close ecommerce detail showing the top's hem, fit and lower construction on the product or a model cropped to exclude the face. Do not lose the product identity.",
    "hem_fit_detail": "Create ONE close-up ecommerce photograph of the T-shirt's lower hem and fit while worn by an adult model. Crop out the entire face and head; show the shirt body, hem stitching, natural drape and the upper supporting outfit only as context. Do not show a full face, unrelated garment as the subject, collage or multiple views.",
    "neckline_detail": "Create a tight ecommerce detail of the neckline and surrounding knit or construction. Preserve the exact shape, material and visible texture.",
    "fabric_detail": "Create ONE single-frame photorealistic macro ecommerce photograph of the actual fabric or knit texture. Fill the frame edge-to-edge with one continuous area of the product material; preserve its true colour, weave, fibre scale, thickness and surface finish. Use a tight close-up with natural shallow depth of field. Do not show the full garment, model, mannequin, garment layout, fabric swatches, artwork collage, grid, split-screen, montage, inset, duplicate view or multiple panels. Output one photograph only.",
    "fabric_texture_detail": "Create ONE single-frame photorealistic macro photograph of the actual T-shirt's fabric surface. Fill the frame with one continuous area of material and show the true observed jersey/knit texture at realistic fibre scale, colour and finish. Introduce a slight controlled twist or gentle fabric fold in that same material area to catch the light and accentuate the texture, without turning it into a knot, drape shot or separate fabric sample. Do not invent ribbing, a different weave or a pattern not visible in the product reference. No garment outline, model, mannequin, fabric swatches, collage, grid, split-screen, inset or multiple views; output one photograph only.",
}


_TOPS_FAMILY_WORN_PROFILES: Final[frozenset[str]] = frozenset({
    "front_model", "front_model_pocket", "styled_model", "seated_model", "seated_angled_model", "cuff_detail_worn", "cuff_adjustment_worn",
    "full_length_model", "rear_model", "rear_angled_model", "angled_model", "hem_fit_detail",
    "front_action", "rear_action",
})
_TOPS_FAMILY_DETAIL_PROFILES: Final[frozenset[str]] = frozenset({
    "construction_detail", "hem_detail", "hem_fit_detail", "neckline_detail", "fabric_detail", "fabric_texture_detail",
})
_TOPS_FAMILY_REAR_PROFILES: Final[frozenset[str]] = frozenset({
    "rear_product", "rear_mannequin", "rear_invisible_mannequin", "rear_model", "rear_angled_model", "rear_action",
})
_TOPS_FAMILY_ANGLED_PROFILES: Final[frozenset[str]] = frozenset({
    "seated_angled_model", "rear_angled_model", "angled_model", "angled_product", "angled_mannequin", "angled_invisible_mannequin",
})


def _tops_family_template(family: str, index: int, profile: str) -> GenerationTemplate:
    base = _BASE_TEMPLATES[_TOPS_FAMILY_PROFILE_BASES[profile]]
    artwork_surface_mode = (
        "detail" if profile in _TOPS_FAMILY_DETAIL_PROFILES
        else "folded" if profile in {"folded", "folded_product"}
        else "rear" if profile in _TOPS_FAMILY_REAR_PROFILES
        else "angled" if profile in _TOPS_FAMILY_ANGLED_PROFILES
        else "worn" if profile in _TOPS_FAMILY_WORN_PROFILES
        else "flat"
    )
    return replace(
        base,
        id=f"ecommerce-tops-{family}-{_TOPS_FAMILY_TEMPLATE_NUMBERS.get(family, tuple(range(1, len(_TOPS_FAMILY_COMPOSITIONS[family]) + 1)))[index]:02d}",
        name=_TOPS_FAMILY_NAMES[family][index],
        description=f"Family-specific Ecommerce presentation for {family.replace('-', ' ')} ({profile.replace('_', ' ')}).",
        prompt_instructions=_TOPS_FAMILY_PROFILE_INSTRUCTIONS[profile],
        applicable_families=(family,),
        reference_object_key=(
            _SHIRTS_TEMPLATE_REFERENCE_PATHS[index] if family == "shirts"
            else _TSHIRTS_TEMPLATE_REFERENCE_PATHS[index] if family == "t-shirts-casual-tops"
            else _SLEEVELESS_TEMPLATE_REFERENCE_PATHS[index] if family == "sleeveless-tops"
            else _KNITWEAR_TEMPLATE_REFERENCE_PATHS[index] if family == "knitwear"
            else _HOODIES_TEMPLATE_REFERENCE_PATHS[index] if family == "hoodies"
            else base.reference_object_key
        ),
        presentation_mode=(
            _SHIRTS_PRESENTATION_MODES[index] if family == "shirts"
            else _TSHIRTS_PRESENTATION_MODES[index] if family == "t-shirts-casual-tops"
            else _SLEEVELESS_PRESENTATION_MODES[index] if family == "sleeveless-tops"
            else _KNITWEAR_PRESENTATION_MODES[index] if family == "knitwear"
            else _HOODIES_PRESENTATION_MODES[index] if family == "hoodies"
            else ("mannequin" if profile == "headless_mannequin" else "invisible_mannequin" if profile in {"front_invisible_mannequin", "angled_invisible_mannequin", "sleeveless_angled_invisible_mannequin", "rear_invisible_mannequin", "front_mannequin", "rear_mannequin", "angled_mannequin"} else "model" if profile in _TOPS_FAMILY_WORN_PROFILES else "garment")
        ),
        output_details=(
            _SHIRTS_OUTPUT_DETAILS[index] if family == "shirts"
            else _TSHIRTS_OUTPUT_DETAILS[index] if family == "t-shirts-casual-tops"
            else _SLEEVELESS_OUTPUT_DETAILS[index] if family == "sleeveless-tops"
            else _KNITWEAR_OUTPUT_DETAILS[index] if family == "knitwear"
            else _HOODIES_OUTPUT_DETAILS[index] if family == "hoodies"
            else ""
        ),
        output_presentation="worn_product" if profile in _TOPS_FAMILY_WORN_PROFILES else "product_only",
        artwork_surface_mode=artwork_surface_mode,
        version=2 if family in {"shirts", "t-shirts-casual-tops"} else base.version,
        required_evidence=("rear_view",) if profile in _TOPS_FAMILY_REAR_PROFILES else ("front_view",),
    )


_TOPS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    template.id: template
    for family, profiles in _TOPS_FAMILY_COMPOSITIONS.items()
    for index, profile in enumerate(profiles)
    for template in (_tops_family_template(family, index, profile),)
}
_STRUCTURED_BOTTOMS_OUTPUT_DETAILS: Final[tuple[str, ...]] = (
    "Subject: The uploaded structured bottoms in the composition described below. Presentation: Laid flat, product only; no body or mannequin. Camera angle: Directly overhead, perpendicular to the surface. View orientation: Straight front facing upward. Framing: Whole garment, waistband to both hems, with a narrow surface border. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Waistband horizontal at top; legs straight and slightly separated. Product scale: Nearly full portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Front waistband, closure, pockets, belt loops and leg/hem stitching where present. Garment volume: Flattened straight legs with modest natural fabric relief, not filled body volume. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One unfolded pair; do not turn this into a floating shaped product. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded structured bottoms in the composition described below. Presentation: Laid flat, rear facing up; no body or mannequin. Camera angle: Directly overhead. View orientation: Straight rear. Framing: Complete waistband, seat, both legs and hems within frame. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred with parallel separated legs. Product scale: Most of portrait height with even margins. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Rear waistband, yoke, centre seam and back pockets only where supported by the upload. Garment volume: Flat rear silhouette, retaining actual leg width. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One complete rear view; no inset front view. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded structured bottoms in the composition described below. Presentation: Worn by one adult model with a small portion of a light neutral top and tan ankle boots. Camera angle: Approximately hip level, angled to the front-side. View orientation: Front three-quarter, not rear; front closure remains visible. Framing: Lower torso just above waistband through both complete boots; no head or upper body. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Standing, legs separated; one boot slightly forward. Product scale: Garment fills most of portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Front rise, near pocket, outer seam, full leg and hems where present. Garment volume: Natural hip, thigh and knee volume with straight hanging legs. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: This image is model-worn despite the current name ending in Product. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded structured bottoms in the composition described below. Presentation: Product folded lengthwise and then upward, resting on a surface. Camera angle: Overhead. View orientation: Front upper section up, with a leg folded across the lower portion. Framing: Entire compact folded arrangement with generous surrounding surface. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Waistband at top; exposed folded hem across lower right. Product scale: Folded stack occupies roughly central two thirds of image height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Waistband, closure, near pocket, folded leg and hem stitching where present. Garment volume: Flat layered stack with real fold thickness. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One folded pair; no model, hanger or duplicate garments. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded structured bottoms in the composition described below. Presentation: Worn by one adult model, dark neutral top edge and tan ankle boots. Camera angle: Straight-on at lower-body level. View orientation: Front. Framing: Crop immediately above waistband; include both boots completely; exclude head and upper torso. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Neutral standing stance with both legs apart. Product scale: Nearly fills portrait frame vertically. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Front closure, pockets, rise, legs and hems where present. Garment volume: Actual worn fit; natural folds at rise, knees and ankles. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One front waist-down model view, not flat lay. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded structured bottoms in the composition described below. Presentation: Worn by one adult model, dark neutral top edge and tan ankle boots. Camera angle: Straight-on at lower-body level. View orientation: Rear. Framing: Immediately above waistband to complete boot heels; head and upper torso outside frame. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Standing with legs slightly separated. Product scale: Nearly full portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Rear waistband, yoke, pockets and leg seams where supported. Garment volume: Natural seat and rear-leg volume. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One rear waist-down model view. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded structured bottoms in the composition described below. Presentation: Close-up worn on an adult model; a dark top edge and one relaxed hand remain visible. Camera angle: Close front-side view around hip height. View orientation: Front at a slight angle. Framing: Waistband to upper thighs; legs, shoes and head excluded; lateral garment edges may leave frame. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Front closure near centre, pocket at image right, relaxed hand at image left. Product scale: Upper garment fills almost the whole image. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Closure, belt loops, pocket opening, stitching and hardware only as supported. Garment volume: Natural worn rise and hip curvature. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One continuous worn construction detail, not a collage. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded structured bottoms in the composition described below. Presentation: Product-only flat-lay pocket detail. Camera angle: Close overhead camera; garment arranged diagonally. View orientation: Front pocket panel. Framing: Tight crop of waistband, belt loop and pocket; most garment outside frame. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Waistband runs upward towards image right; pocket curve dominates centre. Product scale: Pocket construction fills frame with a small surface wedge. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Pocket opening, small inner pocket, rivets and belt loop if present; do not invent a centre closure. Garment volume: Flat material with raised seam and pocket-edge layers. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One diagonal pocket macro; no model and no extra views. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded structured bottoms in the composition described below. Presentation: Product-only flat-lay lower-leg detail. Camera angle: Overhead, diagonal arrangement. View orientation: One lower leg and hem. Framing: Crop upper leg out; show entire near hem edge and opening. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Leg descends from upper left toward lower right. Product scale: Lower-leg fabric occupies most of frame. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Actual side seam, hem stitching, folded edge and fabric texture. Garment volume: Flattened leg with slight opening depth at hem. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One hem detail with exposed studio surface; no full garment inset. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
)

_STRUCTURED_BOTTOMS_TEMPLATE_REFERENCE_PATHS: Final[tuple[str, ...]] = (
    "apps/web/public/output-examples/bottoms/01-front-view.png",
    "apps/web/public/output-examples/bottoms/02-back-view.png",
    "apps/web/public/output-examples/bottoms/03-side-angle-product.png",
    "apps/web/public/output-examples/bottoms/04-folded-product-flat-lay.png",
    "apps/web/public/output-examples/bottoms/05-front-model.png",
    "apps/web/public/output-examples/bottoms/06-back-model.png",
    "apps/web/public/output-examples/bottoms/07-waistband-closure-detail.png",
    "apps/web/public/output-examples/bottoms/08-pocket-panel-detail.png",
    "apps/web/public/output-examples/bottoms/09-hem-leg-detail.png",
)

_STRUCTURED_BOTTOMS_PRESENTATION_MODES: Final[tuple[str, ...]] = (
    "garment", "garment", "model", "garment", "model",
    "model", "model", "garment", "garment",
)

_STRUCTURED_BOTTOMS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    template.id: replace(
        _BASE_TEMPLATES[template.id],
        output_details=_STRUCTURED_BOTTOMS_OUTPUT_DETAILS[index],
        reference_object_key=_STRUCTURED_BOTTOMS_TEMPLATE_REFERENCE_PATHS[index],
        presentation_mode=_STRUCTURED_BOTTOMS_PRESENTATION_MODES[index],
    )
    for index, template in enumerate(BOTTOMS_ECOMMERCE_TEMPLATES)
}

_SHORTS_OUTPUT_DETAILS: Final[tuple[str, ...]] = (
    "Subject: The uploaded shorts in the composition described below. Presentation: Product only, laid flat. Camera angle: Direct overhead. View orientation: Front upward. Framing: Whole waistband, sides and both hems, narrow margins. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred with waistband horizontal and legs spread slightly. Product scale: Almost full image width. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Gathered waistband, tied cord, pocket edges, fly seam and hem where supplied. Garment volume: Flattened wide leg panels, low relief. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One flat garment; no mannequin volume. If the product has drawstrings, let the actual drawstrings fall naturally with gravity; do not pose, stiffen, knot or invent them. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded shorts in the composition described below. Presentation: Invisible-form product; no visible body or support. Camera angle: Straight-on at garment level. View orientation: Front. Framing: Complete garment with both leg openings in frame. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Waistband level; legs evenly spaced. Product scale: Fills most of frame. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Actual waist, drawcord, centre seam, pockets and hems. Garment volume: Rounded hip and leg-opening depth; not flattened. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One shaped front product. If the product has drawstrings, let the actual drawstrings fall naturally with gravity; do not pose, stiffen, knot or invent them. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded shorts in the composition described below. Presentation: Invisible-form product. Camera angle: Front three-quarter, roughly 25–35 degrees off centre. View orientation: Front-side; front cord/closure remains visible. Framing: Complete waistband to hems with narrow margins. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Near side at image right, front centre shifted left. Product scale: Garment dominates frame. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Near side pocket, front waist, seams and leg openings as supplied. Garment volume: Unequal projected leg widths show rotation and real hip depth. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One angled product; no body, feet or rear-only view. If the product has drawstrings, let the actual drawstrings fall naturally with gravity; do not pose, stiffen, knot or invent them. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded shorts in the composition described below. Presentation: Invisible-form product. Camera angle: Straight-on. View orientation: Rear. Framing: Whole waistband and both hems. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred rear seam with evenly separated legs. Product scale: Most of frame. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Rear waist, centre seam and hem; preserve actual pocket details, if any. Garment volume: Rounded seat and open leg volume. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One rear product; no front cord visible through the back. If the product has drawstrings, let the actual drawstrings fall naturally with gravity; do not pose, stiffen, knot or invent them. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded shorts in the composition described below. Presentation: Adult model with a small grey top edge, arms relaxed at sides. Camera angle: Straight-on around hip level. View orientation: Front. Framing: Just above waistband to around knees; exclude lower legs, feet and head. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Hands at outer thighs without obscuring centre front. Product scale: Shorts fill most width and upper three quarters of crop. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Waistband, cord, front seam and hems as supplied. Garment volume: Natural worn hip volume and loose leg openings. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One close worn view, not neck-to-feet. If the product has drawstrings, let the actual drawstrings fall naturally with gravity; do not pose, stiffen, knot or invent them. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded shorts in the composition described below. Presentation: Adult model with grey T-shirt and plain white low-top trainers. Camera angle: Front three-quarter. View orientation: Front-side. Framing: Neck to complete shoes; face excluded. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Arms down; weight shifted and one foot slightly forward. Product scale: Full outfit fills portrait; shorts occupy central region. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Front waist, near side, leg openings and supported construction. Garment volume: Natural loose short-leg drape around thighs. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One standing full-outfit view, no additional panel. If the product has drawstrings, let the actual drawstrings fall naturally with gravity; do not pose, stiffen, knot or invent them. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded shorts in the composition described below. Presentation: Adult model with grey top edge and relaxed hands beside hips. Camera angle: Straight-on at hip level. View orientation: Rear. Framing: Above waistband to around knees; feet and head excluded. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred rear, hands beside garment. Product scale: Shorts occupy most of crop. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Rear waistband, centre seam and hems; actual pockets retained. Garment volume: Natural worn seat and loose leg openings. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One rear close model view. If the product has drawstrings, let the actual drawstrings fall naturally with gravity; do not pose, stiffen, knot or invent them. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded shorts in the composition described below. Presentation: Adult model with grey T-shirt and white low-top trainers. Camera angle: Straight-on. View orientation: Front. Framing: Neck to complete shoes, no face. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Arms relaxed, hands beside thighs, feet slightly apart. Product scale: Full outfit visible with shorts central. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Front waist, closure/cord, pockets and hems as supported. Garment volume: Natural relaxed fit and level waistband. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One neutral full-outfit front view. If the product has drawstrings, let the actual drawstrings fall naturally with gravity; do not pose, stiffen, knot or invent them. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded shorts in the composition described below. Presentation: Product-only upper-front detail; no model. Camera angle: Close straight front view. View orientation: Front. Framing: Full central waistband and cord down through rise; hems and most legs excluded. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Cord bow upper centre, centre seam descending vertically. Product scale: Waist and upper fabric fill almost all frame. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Waistband channels, drawcord, eyelets/tips and closure seam only if supplied. Garment volume: Gentle shaped fabric relief, not a flat pattern diagram. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One detail photograph, no full-body or fabric inset. If the product has drawstrings, let the actual drawstrings fall naturally with gravity; do not pose, stiffen, knot or invent them. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
)

_JOGGERS_OUTPUT_DETAILS: Final[tuple[str, ...]] = (
    "Subject: The uploaded casual bottoms in the composition described below. Presentation: Product only, laid flat. Camera angle: Direct overhead. View orientation: Front upward. Framing: Complete waistband through both cuffs, no clipping. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred waistband at top, legs separated evenly. Product scale: Almost full portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Waistband gathering, tied drawcord, angled pockets and cuffs if present. Garment volume: Flat relaxed legs, tapering only as the uploaded product does; slight material thickness. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One unfolded pair; no model. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded casual bottoms in the composition described below. Presentation: Product shaped by an invisible form; no visible body or support. Camera angle: Straight-on, approximately mid-garment level. View orientation: Front. Framing: Entire waistband to both cuffs. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred with symmetrical separated legs. Product scale: Almost full portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Front waistband, drawcord, pocket edges and leg finish as supplied. Garment volume: Rounded hip and thigh volume; soft folds gather above cuffs when applicable. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One volumetric front view, distinct from slot 01 flat lay. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded casual bottoms in the composition described below. Presentation: Invisible-form product view, no body or visible support. Camera angle: Front three-quarter, approximately 30 degrees off centre. View orientation: Front and near side; not rear. Framing: Entire waistband and both cuffs. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Near hip at image left, front centre displaced toward image right; one knee subtly flexed. Product scale: Almost full portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Near side pocket, waist, front seam and cuffs as supplied. Garment volume: Rounded hip depth and softly bent leg, natural drape above cuffs. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One angled garment, no shoes or model. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded casual bottoms in the composition described below. Presentation: Invisible-form product view without a visible body. Camera angle: Straight-on. View orientation: Rear. Framing: Complete waistband, seat, legs and cuffs. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred rear seam, separated legs. Product scale: Almost full portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Rear waistband, centre seam, leg seams and cuffs; retain actual rear pockets if supplied. Garment volume: Soft rounded seat and relaxed rear legs. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One rear garment view; no front drawcord shown through fabric. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded casual bottoms in the composition described below. Presentation: Adult model wearing the product with a white top edge and off-white low-top trainers. Camera angle: Straight-on lower-body view. View orientation: Front. Framing: Lower torso above waistband to complete trainers; no face. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: One arm hangs at image left, opposite hand rests in pocket where available. Product scale: Product dominates portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Visible waistband, drawcord, near pocket and cuffs as supplied. Garment volume: Relaxed worn legs and soft folds above ankles. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One standing model; styling secondary to garment. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded casual bottoms in the composition described below. Presentation: Adult model in plain white T-shirt and white low-top trainers. Camera angle: Front three-quarter at waist level. View orientation: Angled front, not side-only or rear. Framing: Neck to complete shoes; exclude face and head. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Both hands in pockets if available; one leg extended sideways with relaxed weight shift. Product scale: Whole outfit fills portrait, bottoms remain focus. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Waist, side pocket openings, seam lines and cuff finish as supplied. Garment volume: Natural angled hip volume and asymmetric leg drape. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One model with gentle stance, no action pose. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded casual bottoms in the composition described below. Presentation: Adult model wearing the product, white top edge and off-white trainers. Camera angle: Straight-on lower-body view. View orientation: Rear. Framing: Lower torso above waistband to complete shoes; head excluded. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Both arms relaxed beside hips, feet separated. Product scale: Garment dominates portrait. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Rear waistband, centre seam and cuffs; actual pocket configuration preserved. Garment volume: Natural seat and rear leg fit with ankle folds. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One cropped rear model view. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded casual bottoms in the composition described below. Presentation: Adult model in white T-shirt and white low-top trainers. Camera angle: Straight-on. View orientation: Front. Framing: Neck to complete feet; no face. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred, hands in pockets if available, feet apart. Product scale: Full outfit visible; bottoms about lower two thirds. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Front waist, drawcord, pockets and ankle finish as supported. Garment volume: Relaxed natural worn fit, not flat-lay stiffness. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One front model, wider crop than slot 05. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded casual bottoms in the composition described below. Presentation: Product folded into a compact stack on a surface. Camera angle: Direct overhead. View orientation: Front upper section upward. Framing: Entire folded stack; extended legs concealed by folds. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Waistband at top, front rise centred, folded cuffs peek out at upper right. Product scale: Stack fills central frame with clear margins. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Waistband, drawcord, pockets and partially exposed cuff edges if present. Garment volume: Thick soft layers and gently rounded folds. Background: Light warm beige seamless studio backdrop/surface, approximately #C8C1B6; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One folded pair, no model or props. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
)

_SHORTS_TEMPLATE_REFERENCE_PATHS: Final[tuple[str, ...]] = tuple(
    f"apps/web/public/output-examples/bottoms/shorts/{index:02d}-{filename}.png"
    for index, filename in enumerate((
        "flat-laid-product", "front-invisible-mannequin", "three-quarter-invisible-mannequin",
        "rear-invisible-mannequin", "front-facing-model", "three-quarter-full-length-model",
        "rear-facing-model", "full-length-front-facing-model", "waistband-closure-detail",
    ), start=1)
)

_SHORTS_PRESENTATION_MODES: Final[tuple[str, ...]] = (
    "garment", "invisible_mannequin", "invisible_mannequin", "invisible_mannequin",
    "model", "model", "model", "model", "garment",
)

_SHORTS_REQUIRED_EVIDENCE: Final[tuple[tuple[str, ...], ...]] = (
    ("front_view",), ("front_view",), ("front_view",), ("rear_view",),
    ("front_view",), ("front_view",), ("rear_view",), ("front_view",),
    ("front_view",),
)

_SHORTS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    template.id: replace(
        template,
        output_details=_SHORTS_OUTPUT_DETAILS[index],
        reference_object_key=_SHORTS_TEMPLATE_REFERENCE_PATHS[index],
        presentation_mode=_SHORTS_PRESENTATION_MODES[index],
        required_evidence=_SHORTS_REQUIRED_EVIDENCE[index],
    )
    for index, template in enumerate(SHORTS_ECOMMERCE_TEMPLATES)
}
_JOGGERS_TEMPLATE_REFERENCE_PATHS: Final[tuple[str, ...]] = tuple(
    f"apps/web/public/output-examples/bottoms/joggers/{index:02d}-{filename}.png"
    for index, filename in enumerate((
        "flat-laid-product", "front-invisible-mannequin", "three-quarter-invisible-mannequin",
        "rear-invisible-mannequin", "front-facing-model", "three-quarter-model",
        "rear-facing-model", "full-length-front-model", "folded-top-down",
    ), start=1)
)

_JOGGERS_PRESENTATION_MODES: Final[tuple[str, ...]] = (
    "garment", "invisible_mannequin", "invisible_mannequin", "invisible_mannequin",
    "model", "model", "model", "model", "garment",
)

_JOGGERS_REQUIRED_EVIDENCE: Final[tuple[tuple[str, ...], ...]] = (
    ("front_view",), ("front_view",), ("front_view",), ("rear_view",),
    ("front_view",), ("front_view",), ("rear_view",), ("front_view",),
    ("front_view",),
)

_JOGGERS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    template.id: replace(
        template,
        output_details=_JOGGERS_OUTPUT_DETAILS[index],
        reference_object_key=_JOGGERS_TEMPLATE_REFERENCE_PATHS[index],
        presentation_mode=_JOGGERS_PRESENTATION_MODES[index],
        required_evidence=_JOGGERS_REQUIRED_EVIDENCE[index],
    )
    for index, template in enumerate(JOGGERS_ECOMMERCE_TEMPLATES)
}
_LEGGINGS_OUTPUT_DETAILS: Final[tuple[str, ...]] = (
    "Subject: The uploaded leggings in the composition described below. Presentation: Adult model wearing leggings with a white top edge and off-white trainers. Camera angle: Straight-on at lower-body level. View orientation: Front. Framing: Lower torso above waistband through complete trainers; head excluded. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Arms relaxed, both hands visible outside thighs, legs apart. Product scale: Garment fills most portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Broad smooth waistband, rise seams and narrow ankle hems as supplied. Garment volume: Close body-following fit from hip to ankle, not loose jogger volume. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One cropped model view; no added pockets or drawcord unless the actual garment has them. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded leggings in the composition described below. Presentation: Product only, laid flat on a surface. Camera angle: Direct overhead. View orientation: Front upward. Framing: Entire waistband and both ankle hems within margins. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred waistband, straight separated legs. Product scale: Almost full portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Waistband join, centre seam, leg seams and hem stitching as supplied. Garment volume: Flattened tapered panels with little body volume. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One unfolded flat lay, distinct from slot 05. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded leggings in the composition described below. Presentation: Invisible-form product with no visible body or feet. Camera angle: Straight-on. View orientation: Rear. Framing: Complete waistband to ankle hems. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Rear centre seam centred, legs separated. Product scale: Almost full portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Rear waistband join, centre seam and narrow hems as supplied. Garment volume: Rounded seat, knees and calves with fitted rather than baggy volume. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One rear shaped garment; do not substitute front. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded leggings in the composition described below. Presentation: Invisible-form product with no visible body. Camera angle: Front three-quarter. View orientation: Front and near side. Framing: Complete waist to both ankle hems. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Near hip at image left, front centre displaced right; one knee subtly bent. Product scale: Almost full portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Waistband, near side seam, front rise and ankle finish as supplied. Garment volume: Fitted hip and leg curves with asymmetric perspective. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One angled shaped product, no model feet. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded leggings in the composition described below. Presentation: Invisible-form product with no visible body. Camera angle: Straight-on. View orientation: Front. Framing: Whole waistband and both hems. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred front seam, evenly separated legs. Product scale: Almost full portrait height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Waistband join, front rise and hems as supported. Garment volume: Smooth fitted hip, thigh and calf volume, not flat panels. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One shaped front garment, no shoes or stand. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded leggings in the composition described below. Presentation: Product neatly folded on a surface. Camera angle: Direct overhead. View orientation: Front upper section upward. Framing: Whole folded stack with margins; unfolded legs concealed. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Waistband at top, rise seam central, folded layers exposed at image right. Product scale: Compact stack occupies central majority of image. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Smooth waistband, seam junction and fabric surface; no invented drawcord or cuffs. Garment volume: Soft rounded folds and layered edges. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One folded garment only. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded leggings in the composition described below. Presentation: Adult model with a white top edge and off-white trainers. Camera angle: Straight-on lower-body view. View orientation: Rear. Framing: Lower torso above waistband to complete shoes; no head. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Arms down beside hips, feet apart. Product scale: Leggings dominate portrait. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Rear waistband, centre seam and stitched ankle hems as supplied. Garment volume: Body-following rear fit with natural seat and calf contours. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One cropped rear worn view. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded leggings in the composition described below. Presentation: Adult model in a plain white T-shirt and white trainers. Camera angle: Straight-on. View orientation: Front. Framing: Neck to complete shoes; face/head excluded. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Arms down, relaxed hands beside thighs, feet apart. Product scale: Full outfit in portrait; leggings in lower majority. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Waistband, rise and ankle hems as supplied. Garment volume: Fitted legs with natural minimal wrinkles. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One full-outfit front model, wider crop than slot 01. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
)

_LEGGINGS_TEMPLATE_REFERENCE_PATHS: Final[tuple[str, ...]] = tuple(
    f"apps/web/public/output-examples/bottoms/leggings/{index:02d}-leggings.png"
    for index in range(1, 9)
)

_LEGGINGS_PRESENTATION_MODES: Final[tuple[str, ...]] = (
    "model", "garment", "invisible_mannequin", "invisible_mannequin",
    "invisible_mannequin", "garment", "model", "model",
)

_LEGGINGS_REQUIRED_EVIDENCE: Final[tuple[tuple[str, ...], ...]] = (
    ("front_view",), ("front_view",), ("rear_view",), ("front_view",),
    ("front_view",), ("front_view",), ("rear_view",), ("front_view",),
)

_LEGGINGS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    template.id: replace(
        template,
        output_details=_LEGGINGS_OUTPUT_DETAILS[index],
        reference_object_key=_LEGGINGS_TEMPLATE_REFERENCE_PATHS[index],
        presentation_mode=_LEGGINGS_PRESENTATION_MODES[index],
        required_evidence=_LEGGINGS_REQUIRED_EVIDENCE[index],
    )
    for index, template in enumerate(LEGGINGS_ECOMMERCE_TEMPLATES)
}
_SKIRTS_OUTPUT_DETAILS: Final[tuple[str, ...]] = (
    "Subject: The uploaded skirt in the composition described below. Presentation: Product only, front laid on a studio surface; no body or visible support. Camera angle: Overhead, approximately perpendicular to front panel. View orientation: Front upward. Framing: Entire waist and flared hem with generous space above and below. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred, waistband level, hem spread naturally. Product scale: Most image width; about central two thirds of height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Waistband, front closure, loops, pleats and hem only if the uploaded skirt has them. Garment volume: Flat resting A-line outline with raised pleat layers, not body-filled shaping. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One complete front product; retain uploaded length and shape, not necessarily the benchmark mini length. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded skirt in the composition described below. Presentation: Product only, back laid on a studio surface. Camera angle: Overhead. View orientation: Rear upward. Framing: Whole waistband and hem with clear margins. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Centred waistband and rear centre line. Product scale: Most image width, central two thirds of height. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Rear waist, loops, pleats, centre seam and hem where present. Garment volume: Flat resting rear silhouette with dimensional pleat edges. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One complete rear product; do not add the front button to the rear. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded skirt in the composition described below. Presentation: Adult model wearing skirt with the lower edge of a fitted dark grey top. Camera angle: Straight-on around hip level. View orientation: Front. Framing: Just above waistband to around knees; shoes and head excluded. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Skirt centred; arms not visible in benchmark. Product scale: Skirt dominates width and upper portion of crop. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Front waist, closure, pleats and entire hem as supplied. Garment volume: Natural worn waist and flared drape; preserve actual skirt cut. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One close model view with unobstructed skirt. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded skirt in the composition described below. Presentation: Adult model with a fitted dark grey top edge. Camera angle: Straight-on around hip level. View orientation: Rear. Framing: Above waistband to around knees; no shoes or head. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Rear centred, arms outside crop. Product scale: Skirt dominates width. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Rear waist, centre seam, pleats and complete hem as supported. Garment volume: Natural seat volume and hanging rear pleats where present. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One close rear worn view. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded skirt in the composition described below. Presentation: Adult model in fitted dark grey short-sleeve top and black ballet flats. Camera angle: Slight front three-quarter. View orientation: Front-side, not rear. Framing: Base of neck/upper shoulders through complete shoes; no head. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Arms relaxed beside skirt; one leg angled outward and weight shifted. Product scale: Whole outfit in portrait, skirt central. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Front waistband, near-side drape and hem as supplied. Garment volume: Natural waist fit and hanging flared volume, slight asymmetric stance. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One softly angled full-outfit model. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
    "Subject: The uploaded skirt in the composition described below. Presentation: Adult model in fitted dark grey short-sleeve top and black ballet flats. Camera angle: Straight-on. View orientation: Front. Framing: Neck to complete shoes; face excluded. Crop: Respect the stated frame; do not replace a detail crop with a whole-product view or clip a product edge required to remain visible. Product position: Arms relaxed at sides, one knee softened, feet separated. Product scale: Whole outfit with skirt central. Silhouette: Preserve the uploaded product's actual proportions and outline within this arrangement. Visible construction: Front waist, supported closure, pleats and hem. Garment volume: Natural front fit and relaxed hem rather than rigid symmetry. Background: Clean light warm beige studio backdrop or matte surface, approximately #C8C1B6, wherever visible; no white cutout background, props or horizon line. Lighting: Soft diffuse studio illumination, subtle natural form/contact shadows appropriate to this presentation, and readable fabric and seam detail. Colour treatment: Preserve the uploaded product's true colour, pattern and finish; avoid beige tint spilling onto the garment. Composition: One natural standing front model. Output: One continuous high-fidelity ecommerce photograph. No collage, split panels, insets, duplicate views, text or watermark.",
)

_SKIRTS_TEMPLATE_REFERENCE_PATHS: Final[tuple[str, ...]] = tuple(
    f"apps/web/public/output-examples/bottoms/skirts/{index:02d}-skirt.png"
    for index in range(1, 7)
)

_SKIRTS_PRESENTATION_MODES: Final[tuple[str, ...]] = (
    "garment", "garment", "model", "model", "model", "model",
)

_SKIRTS_REQUIRED_EVIDENCE: Final[tuple[tuple[str, ...], ...]] = (
    ("front_view",), ("rear_view",), ("front_view",),
    ("rear_view",), ("front_view",), ("front_view",),
)

_SKIRTS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    template.id: replace(
        template,
        output_details=_SKIRTS_OUTPUT_DETAILS[index],
        reference_object_key=_SKIRTS_TEMPLATE_REFERENCE_PATHS[index],
        presentation_mode=_SKIRTS_PRESENTATION_MODES[index],
        required_evidence=_SKIRTS_REQUIRED_EVIDENCE[index],
    )
    for index, template in enumerate(SKIRTS_ECOMMERCE_TEMPLATES)
}
_BOOTS_NAMES = (
    "Front Three-Quarter on Model", "Side on Model — Toe Raised", "Front Three-Quarter Detail",
    "Rear Three-Quarter Detail", "Three-Quarter on Model", "Rear Heel Close-Up",
    "Side and Vamp Close-Up", "Crossed Step on Model", "Side Profile — Product Only",
)
_BOOTS_MODES = ("model", "model", "model", "model", "model", "model", "model", "model", "garment")
_BOOTS_EVIDENCE = (
    ("front_view", "side_view"), ("side_view", "sole_or_underside"), ("front_view", "side_view"),
    ("rear_view", "side_view"), ("front_view", "side_view"), ("rear_view", "side_view"),
    ("front_view", "side_view"), ("side_view", "rear_view", "sole_or_underside"), ("side_view",),
)
_BOOTS_DETAILS = (
    "Front three-quarter pair worn on an adult; crop above the midsection, retain complete boots and floor. Preserve actual shaft, toe, heel, sole and supported decoration.",
    "Single worn boot in side profile with toe raised and heel grounded; retain complete shaft, toe, heel and sole edge.",
    "Close front three-quarter pair detail; crop through the shafts and retain toes and near heel.",
    "Low rear three-quarter pair detail; retain heel counters, rear seams, heel bases and near toe.",
    "Grounded three-quarter pair worn on an adult; retain complete shaft rims, toes and heels with legs cropped above the knees.",
    "Tight rear heel close-up; retain heel bases and floor contact, with intentional toe crop.",
    "Close side/front three-quarter pair detail; retain near vamp, toe, sole edge and heel.",
    "Crossed-step pair worn on an adult; retain complete boots and shaft rims with physically credible contact.",
    "One complete boot upright in straight side profile, product-only, with shaft rim, toe, heel and sole edge fully visible.",
)
_BOOTS_FAMILY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {
    f"ecommerce-footwear-boots-{index + 1:02d}": replace(
        FOOTWEAR_ECOMMERCE_TEMPLATES[0],
        id=f"ecommerce-footwear-boots-{index + 1:02d}",
        name=_BOOTS_NAMES[index],
        description=f"Reviewed Boots ecommerce composition: {_BOOTS_NAMES[index].lower()}.",
        applicable_families=("boots",),
        applicable_subtypes=_FOOTWEAR_SUBTYPES + ("ankle boots", "knee-high boots", "tall boots", "heeled boots"),
        reference_object_key=f"docs/boots-output-details/references/{index + 1:02d}_" + (
            ("front_three_quarter_on_model" if index == 0 else "side_on_model_toe_raised" if index == 1 else "front_three_quarter_detail" if index == 2 else "rear_three_quarter_detail" if index == 3 else "three_quarter_on_model" if index == 4 else "rear_heel_close_up" if index == 5 else "side_vamp_close_up" if index == 6 else "crossed_step_on_model" if index == 7 else "side_profile_product_only")
        ) + ".png",
        presentation_mode=_BOOTS_MODES[index],
        output_presentation="worn_product" if _BOOTS_MODES[index] == "model" else "product_only",
        required_evidence=_BOOTS_EVIDENCE[index],
        output_details=f"- Subject: Uploaded boots. - Presentation mode: {_BOOTS_MODES[index]}. - Composition: {_BOOTS_DETAILS[index]} - Preserve the uploaded boot's actual shaft height, opening, toe shape, heel geometry, sole, material, colour and branding; never transfer benchmark black, suede, slouch, heel or shaft construction. - Background: Warm light beige seamless studio background and floor, approximately #C8C1B6. - Lighting: Broad soft studio illumination with credible contact shadows and readable dark materials. - Output: One continuous ecommerce image; no collage, inset, text, watermark, extra boots or invented construction.",
        version=1,
    ) for index in range(9)
}

_TEMPLATES: Final[dict[str, GenerationTemplate]] = {**_BASE_TEMPLATES, **_TOPS_FAMILY_TEMPLATES, **_JACKETS_FAMILY_TEMPLATES, **_COATS_FAMILY_TEMPLATES, **_GILETS_FAMILY_TEMPLATES, **_TRAINERS_FAMILY_TEMPLATES, **_FLATS_LOAFERS_FAMILY_TEMPLATES, **_HEELS_FAMILY_TEMPLATES, **_BOOTS_FAMILY_TEMPLATES, **_STRUCTURED_BOTTOMS_FAMILY_TEMPLATES, **_SHORTS_FAMILY_TEMPLATES, **_JOGGERS_FAMILY_TEMPLATES, **_LEGGINGS_FAMILY_TEMPLATES, **_SKIRTS_FAMILY_TEMPLATES}
_LEGACY_TEMPLATES: Final[dict[str, GenerationTemplate]] = {TOPS_CLEAN_PRODUCT_SHOT.id: TOPS_CLEAN_PRODUCT_SHOT}


def get_generation_template(template_id: str) -> GenerationTemplate | None:
    """Return a template by its stable ID, or ``None`` when it is unknown."""
    return _TEMPLATES.get(template_id) or _LEGACY_TEMPLATES.get(template_id)


def _canonical_family(category: str, family: str | None) -> str | None:
    if not family:
        return None
    value = family.strip().lower()
    if category.strip().lower() == "footwear" and value in {"trainers", "flats-loafers", "sandals-open-shoes"}:
        return "shoes"
    return value


def validate_generation_template(template_id: str, *, category: str, channel: str, subtype: str | None = None, product_family: str | None = None) -> GenerationTemplate:
    """Load a template and ensure it is valid for the requested product."""
    template = get_generation_template(template_id)
    if template is None:
        raise ValueError(f"Unknown generation template: {template_id}")
    if template.category != category.strip().lower():
        raise ValueError(f"Template {template_id} is not available for category {category}")
    if template.channel != channel.strip().lower():
        raise ValueError(f"Template {template_id} is not available for channel {channel}")
    product_family = _canonical_family(category, product_family)
    if template.applicable_families:
        # Bottoms templates are shared composition primitives, so an unknown
        # bottoms family may use the conservative generic policy. A known
        # family must still be one explicitly supported by the template.
        unknown_bottoms_family = template.category == "bottoms" and product_family is None
        unknown_outerwear_family = template.category == "outerwear" and product_family is None
        unknown_footwear_family = template.category == "footwear" and product_family is None
        legacy_outerwear_choice = (
            template.category == "outerwear"
            and template_id.startswith("ecommerce-outerwear-")
            and not any(token in template_id for token in ("-coats-", "-gilets-padded-vests-"))
        )
        if not (unknown_bottoms_family or unknown_outerwear_family or unknown_footwear_family or legacy_outerwear_choice) and product_family not in template.applicable_families:
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
        family = _canonical_family(category or "", product_family)
        # Once a family is known, expose only the locked family pack. Generic
        # category templates remain available when family is unconfirmed.
        templates = [template for template in templates if template.applicable_families and family in template.applicable_families]
    # subtype is intentionally not used to hide templates; it is descriptive
    # context for prompt compilation and future ranking.
    return templates
