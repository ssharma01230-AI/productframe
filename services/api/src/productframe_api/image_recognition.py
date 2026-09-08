"""Safe product-image screening and structured visual analysis.

The screening gate runs before detailed analysis. It accepts wearable fashion
products (including accessories) and rejects unrelated objects, graphics, and
screenshots.
"""
from __future__ import annotations

import base64
import io
import os
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from contextvars import ContextVar
from enum import StrEnum
from threading import Event, Lock
from typing import Annotated, Callable, Literal

from openai import OpenAI
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, ValidationError, field_validator

from .analysis_limits import AnalysisBudgetError, AnalysisLimits, RateLimiter, estimate_request_tokens, retry_delay
from .category_registry import get_bottoms_family_for_subtype
from .category_schemas import CATEGORY_DETAIL_MODELS, BottomsFamily, CategoryDetails, UnderwearFamily
from .analysis_router import AnalysisRouter, AnalysisSafetyError
from .image_processing import normalize_image_orientation

MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_DIMENSION = 10_000
MAX_ANALYSIS_DIMENSION = 2_048
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
OPENAI_MAX_RETRIES = 8
_limiters: dict[str, RateLimiter] = {}
_limiter_lock = Lock()
_analysis_cancel: ContextVar[Event | None] = ContextVar("analysis_cancel", default=None)
_analysis_model: ContextVar[str | None] = ContextVar("analysis_model", default=None)
_analysis_router: ContextVar[AnalysisRouter | None] = ContextVar("analysis_router", default=None)
_analysis_client: ContextVar[OpenAI | None] = ContextVar("analysis_client", default=None)


def _vision_model() -> str:
    return _analysis_model.get() or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")


@contextmanager
def _analysis_session(api_key: str | None, model: str | None):
    if _analysis_router.get() is not None:
        yield
        return
    selected_model = model or _vision_model()
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"), max_retries=0, timeout=45)
    router = AnalysisRouter(client, selected_model, _request_limiter(selected_model))
    model_context = _analysis_model.set(selected_model)
    router_context = _analysis_router.set(router)
    client_context = _analysis_client.set(client)
    try:
        yield
    finally:
        _analysis_model.reset(model_context)
        _analysis_router.reset(router_context)
        _analysis_client.reset(client_context)
        router.close()
        if hasattr(client, "close"):
            client.close()


def _request_limiter(model: str) -> RateLimiter:
    # A cache decorator can initialize twice on simultaneous first requests.
    with _limiter_lock:
        if model not in _limiters:
            _limiters[model] = RateLimiter(AnalysisLimits.from_env())
        return _limiters[model]


def _check_cancelled() -> None:
    signal = _analysis_cancel.get()
    if signal is not None and signal.is_set():
        raise CancelledError("Image analysis stopped after another image failed")


def _openai_call(operation, *, model: str, input_tokens: int = 0, output_tokens: int = 0):
    """Reserve capacity for every attempt, sharing cooldowns across image tasks."""
    limiter = _request_limiter(model)
    for attempt in range(OPENAI_MAX_RETRIES):
        _check_cancelled()
        reservation = limiter.acquire(input_tokens, output_tokens, cancel_event=_analysis_cancel.get())
        try:
            _check_cancelled()
            raw = operation()
        except Exception as exc:
            limiter.observe(reservation, getattr(getattr(exc, "response", None), "headers", None))
            _check_cancelled()
            delay = retry_delay(exc, attempt)
            if delay is None or attempt == OPENAI_MAX_RETRIES - 1:
                raise
            limiter.defer(delay)
        else:
            limiter.observe(reservation, raw.headers)
            return raw.parse()


def _parse_response(client: OpenAI, *, model: str, input: list, text_format):
    limits = AnalysisLimits.from_env()
    router = _analysis_router.get()
    if router is not None:
        return router.parse(input=input, text_format=text_format, output_tokens=limits.max_output_tokens,
                            cancel_event=_analysis_cancel.get(), grouping=text_format.__name__ == "BatchScreeningResult")
    tokens = estimate_request_tokens(input, text_format=text_format, model=model)
    return _openai_call(
        lambda: client.responses.with_raw_response.parse(
            model=model, input=input, text_format=text_format, max_output_tokens=limits.max_output_tokens,
        ),
        model=model, input_tokens=tokens, output_tokens=limits.max_output_tokens,
    )


def _moderate_image(client: OpenAI, data_url: str):
    # Moderation has a separate request-rate bucket from the vision model.
    return _openai_call(
        lambda: client.moderations.with_raw_response.create(
            model="omni-moderation-latest", input=[{"type": "image_url", "image_url": {"url": data_url}}],
        ),
        model="omni-moderation-latest",
    )


def _image_input(data_url: str, detail: str = "low") -> dict[str, str]:
    return {"type": "input_image", "image_url": data_url, "detail": detail}


class ProductCategory(StrEnum):
    OUTERWEAR = "outerwear"
    TOPS = "tops"
    BOTTOMS = "bottoms"
    SOCKS = "socks"
    FOOTWEAR = "footwear"
    UNDERWEAR = "underwear"
    HEADWEAR = "headwear"
    SCARVES = "scarves"
    GLOVES = "gloves"
    RINGS = "rings"
    BRACELETS = "bracelets"
    EARRINGS = "earrings"
    WATCHES = "watches"
    BELTS = "belts"
    NECKWEAR = "neckwear"


class ProductCategorization(BaseModel):
    category: ProductCategory
    # Product family is system-controlled for categories that use rendering
    # families. Null is deliberate when the image does not support a confident
    # family assignment.
    product_family: UnderwearFamily | BottomsFamily | None = None
    subtype: str | None = None
    product_type: str = Field(min_length=5, max_length=120)
    confidence: float = Field(ge=0, le=1)


class ImageScreeningResult(BaseModel):
    """The mandatory pass/fail decision made before product analysis."""

    passed: bool
    detected_item: str | None = None
    item_count: int = Field(ge=0, le=20)
    primary_item_clear: bool
    supporting_clothing_is_styling: bool = False
    reason: str = Field(min_length=10, max_length=300)


class ProductIdentity(BaseModel):
    product_type: str = Field(min_length=3, max_length=120)
    dominant_colour: str = Field(min_length=3, max_length=120)
    pattern_or_finish: str = Field(min_length=3, max_length=160)
    visual_signature: str = Field(min_length=10, max_length=300)
    # Media coverage is deliberately separate from product identity. Defaults
    # preserve compatibility with older provider responses and fixtures.
    media_views: list[Literal["front_view", "rear_view", "top_view", "side_view", "sole_or_underside", "flat_lay", "detail", "worn", "unknown"]] = Field(default_factory=list, max_length=8)
    visible_evidence: list[str] = Field(default_factory=list, max_length=30)


class ProductImageGroup(BaseModel):
    product_number: int = Field(ge=1)
    image_numbers: list[int] = Field(min_length=1)
    reason: str = Field(min_length=10, max_length=300)


class RejectedImage(BaseModel):
    image_number: int = Field(ge=1)
    reason: str = Field(min_length=10, max_length=300)


class BatchScreeningResult(BaseModel):
    passed: bool
    unique_product_count: int = Field(ge=0)
    groups: list[ProductImageGroup] = Field(default_factory=list)
    rejected_images: list[RejectedImage] = Field(default_factory=list)
    reason: str = Field(min_length=10, max_length=300)


class ImageRejectedError(ValueError):
    def __init__(self, screening: ImageScreeningResult):
        self.screening = screening
        super().__init__(screening.reason)


class ColourDescription(BaseModel):
    """Detailed visible colour information shared by all product categories."""

    primary_colour: str = Field(min_length=3, max_length=120)
    secondary_colours: list[str] = Field(default_factory=list, max_length=12)
    pattern: str = Field(min_length=3, max_length=120)
    colour_distribution: str = Field(min_length=3, max_length=240)
    tonal_variation: str = Field(min_length=3, max_length=160)
    saturation: str = Field(min_length=3, max_length=80)
    brightness: str = Field(min_length=3, max_length=80)
    colour_finish: str = Field(min_length=3, max_length=100)
    wash_treatment: str = Field(default="not_visible", max_length=160)
    fade_level: str = Field(default="not_visible", max_length=100)
    colour_variation: str = Field(default="not_visible", max_length=160)
    visible_uncertainties: list[str] = Field(default_factory=list, max_length=12)


class MaterialDescription(BaseModel):
    appearance: str = Field(min_length=3, max_length=500)
    weight: str = Field(min_length=3, max_length=160)
    thickness: str = Field(min_length=3, max_length=160)
    texture: str = Field(min_length=3, max_length=300)
    finish: str = Field(min_length=3, max_length=160)
    stretch_or_flexibility: str = Field(min_length=3, max_length=160)
    drape_or_rigidity: str = Field(min_length=3, max_length=160)
    visible_condition: str = Field(min_length=3, max_length=300)
    drape_quality: str = Field(default="not_visible", max_length=160)
    rigidity_level: str = Field(default="not_visible", max_length=100)
    wrinkle_visibility: str = Field(default="not_visible", max_length=160)
    surface_softness: str = Field(default="not_visible", max_length=160)
    fabric_body: str = Field(default="not_visible", max_length=160)
    visible_uncertainties: list[str] = Field(default_factory=list)


class ConstructionDescription(BaseModel):
    silhouette: str = Field(min_length=3, max_length=300)
    shape: str = Field(min_length=3, max_length=300)
    proportions: str = Field(min_length=3, max_length=300)
    construction_details: list[str] = Field(min_length=1)
    functional_details: list[str] = Field(default_factory=list)
    callouts: list[str] = Field(default_factory=list)
    visible_uncertainties: list[str] = Field(default_factory=list)


class ArtworkIdentity(BaseModel):
    """Location and identity of artwork visible on the submitted product."""

    artwork_type: Literal["print", "illustration", "logo", "text", "embroidery", "applique", "other"]
    description: str = Field(min_length=10, max_length=500)
    source_bounds: list[float] = Field(min_length=4, max_length=4)
    garment_relative_bounds: list[float] = Field(min_length=4, max_length=4)
    visible_fraction: float = Field(ge=0, le=1)
    extraction_confidence: float = Field(ge=0, le=1)

    @field_validator("source_bounds", "garment_relative_bounds")
    @classmethod
    def validate_normalized_bounds(cls, value: list[float]) -> list[float]:
        if any(coordinate < 0 or coordinate > 1 for coordinate in value):
            raise ValueError("artwork bounds must contain normalized coordinates")
        if value[2] <= 0 or value[3] <= 0 or value[0] + value[2] > 1.001 or value[1] + value[3] > 1.001:
            raise ValueError("artwork bounds must be normalized x, y, width, height")
        return value


class BrandingDescription(BaseModel):
    graphics: list[str] = Field(default_factory=list)
    logos: list[str] = Field(default_factory=list)
    graphic_details: list[str] = Field(default_factory=list)
    artwork_regions: list[ArtworkIdentity] = Field(default_factory=list, max_length=8)


class GenderDescription(BaseModel):
    assumed: str = Field(min_length=3, max_length=120)
    user_confirmed: str | None = Field(default=None, max_length=120)


EvidenceStatus = Literal[
    "clearly_visible",
    "partially_visible",
    "uncertain",
    "not_visible",
    "user_confirmed",
]


class ConfidenceAssessment(BaseModel):
    score: float = Field(ge=0, le=1)
    status: EvidenceStatus
    evidence: list[str]
    uncertainties: list[str]


class GenderConfidence(ConfidenceAssessment):
    source: Literal["model", "user", "none"]


class ProductConfidence(BaseModel):
    overall: ConfidenceAssessment
    category: ConfidenceAssessment
    product_identity: ConfidenceAssessment
    colour: ConfidenceAssessment
    materials: ConfidenceAssessment
    construction: ConfidenceAssessment
    branding: ConfidenceAssessment
    category_specific: ConfidenceAssessment
    gender: GenderConfidence


class GlobalProductDetails(BaseModel):
    colour: ColourDescription
    materials: MaterialDescription
    construction: ConstructionDescription
    branding: BrandingDescription
    gender: GenderDescription
    source_rotation_degrees: Literal[0, 90, 180, 270] = 0


class TopGarmentDetails(BaseModel):
    """Detailed, visible attributes used to preserve top identity during generation."""

    neckline_type: str = Field(min_length=3, max_length=80)
    neckline_depth: str = Field(min_length=3, max_length=80)
    sleeve_type: str = Field(min_length=3, max_length=100)
    sleeve_length: str = Field(min_length=3, max_length=80)
    sleeve_width: str = Field(min_length=3, max_length=80)
    shoulder_shape: str = Field(min_length=3, max_length=100)
    collar_or_neck_binding: str = Field(min_length=3, max_length=120)
    hem_shape: str = Field(min_length=3, max_length=80)
    fit_and_silhouette: str = Field(min_length=3, max_length=160)
    garment_length: str = Field(min_length=3, max_length=80)
    material_appearance: str = Field(min_length=3, max_length=240)
    apparent_weight: str = Field(min_length=3, max_length=100)
    surface_texture: str = Field(min_length=3, max_length=160)
    surface_finish: str = Field(min_length=3, max_length=100)
    construction_details: list[str] = Field(min_length=1, max_length=20)
    visible_uncertainties: list[str] = Field(default_factory=list, max_length=20)
    collar_thickness: str = "not_visible"
    collar_width: str = "not_visible"
    neckline_rigidity: str = "not_visible"
    body_width_relative_to_length: str = "not_visible"
    shoulder_drop: str = "not_visible"
    silhouette_volume: str = "not_visible"
    sleeve_width_relative_to_body: str = "not_visible"
    hem_position: str = "not_visible"
    drape_quality: str = "not_visible"
    rigidity_level: str = "not_visible"
    wrinkle_visibility: str = "not_visible"
    surface_softness: str = "not_visible"
    fabric_body: str = "not_visible"
    wash_treatment: str = "not_visible"
    fade_level: str = "not_visible"
    graphic_condition: str = "not_visible"
    graphic_scale: str = "not_visible"
    graphic_placement: str = "not_visible"
    graphic_edge_quality: str = "not_visible"


class ProductAnalysis(BaseModel):
    product_name: str = Field(min_length=3, max_length=160)
    category: ProductCategory
    # Populated for categories with rendering families; null means the family
    # could not be established confidently and conservative fallback is used.
    product_family: UnderwearFamily | BottomsFamily | None = None

    @field_validator("product_name")
    @classmethod
    def product_name_max_five_words(cls, value: str) -> str:
        # Keep the assigned display name concise even if the model returns a
        # longer descriptive phrase.
        return " ".join(value.split()[:5])

    product_type: str = Field(min_length=5, max_length=120)
    colours: str = Field(min_length=5, max_length=300)
    colour_details: ColourDescription | None = None
    materials: str = Field(min_length=3, max_length=300)
    features: list[str] = Field(min_length=1, max_length=30)
    description: str = Field(min_length=30, max_length=320)
    confidence: float = Field(ge=0, le=1)
    # Category-specific details are optional for legacy analysis fixtures. New
    # tops analysis is instructed to populate this object.
    tops_details: TopGarmentDetails | None = None
    global_details: GlobalProductDetails | None = None
    category_details: CategoryDetails | None = None
    confidence_details: ProductConfidence | None = None

    @field_validator("product_type", "colours", "materials")
    @classmethod
    def reject_vague_values(cls, value: str) -> str:
        vague = {"unknown", "n/a", "multicolour", "multicolored", "clothing", "garment", "item"}
        if value.strip().lower() in vague:
            raise ValueError("analysis must be specific rather than vague")
        return value.strip()


class PrescreenedImage(BaseModel):
    image_bytes: bytes
    content_type: Annotated[str, Field(pattern=r"^image/jpeg$")]
    width: int
    height: int
    original_format: str


def prescreen_image(image_bytes: bytes) -> PrescreenedImage:
    """Validate, decode, resize, and re-encode an image before any AI call."""
    if not image_bytes:
        raise ValueError("image is empty")
    if len(image_bytes) > MAX_INPUT_BYTES:
        raise ValueError("image is larger than the 20 MB limit")
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            original_format = (image.format or "").upper()
            if original_format not in ALLOWED_FORMATS:
                raise ValueError("only JPEG, PNG, and WEBP images are supported")
            width, height = image.size
            if width < 32 or height < 32:
                raise ValueError("image is too small")
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                raise ValueError("image dimensions are too large")
            image.verify()
        normalized = normalize_image_orientation(image_bytes, quality=95)
        with Image.open(io.BytesIO(normalized.content)) as image:
            image = image.convert("RGB")
            image.thumbnail((MAX_ANALYSIS_DIMENSION, MAX_ANALYSIS_DIMENSION), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=88, optimize=True)
            return PrescreenedImage(image_bytes=output.getvalue(), content_type="image/jpeg", width=image.width, height=image.height, original_format=original_format)
    except UnidentifiedImageError as exc:
        raise ValueError("file is not a readable image") from exc


def _data_url(image: PrescreenedImage) -> str:
    encoded = base64.b64encode(image.image_bytes).decode("ascii")
    return f"data:{image.content_type};base64,{encoded}"


def categorize_product_image(client: OpenAI, data_url: str) -> ProductCategorization:
    """Categorize an approved image before detailed attribute analysis."""
    response = _parse_response(client,
        model=_vision_model(),
        input=[{"role": "user", "content": [{"type": "input_text", "text": """Categorize this already-approved wearable fashion product.
Choose exactly one category: outerwear, tops, bottoms, socks, footwear, underwear, headwear, scarves, gloves, rings, neckwear, watches, bracelets, earrings, belts.
Never return bags; bags are outside the supported clothing product scope and must be rejected.
For category underwear, set product_family to exactly one of: lower_body_underwear, bra, lingerie, base_layer, underwear_set. Set it to null when the family cannot be established confidently. Use underwear_set for a coordinated multi-piece product; use bra for bras or bralettes; use lower_body_underwear for boxers, briefs or bikini briefs; use base_layer for vests, undershirts or camisoles; use lingerie for slips, bodysuits, corsets or decorative lingerie-led pieces.
For category bottoms, return subtype as exactly one of: shorts, skirt, leggings, trousers, jeans, cargo trousers, joggers, chinos. Set product_family to exactly one of: structured_bottoms, casual_bottoms, leggings, skirts, matching the subtype mapping. Set both subtype and product_family to null when the bottoms subtype cannot be established confidently.
For all other categories, product_family and subtype must be null.
Return a highly specific product_type, such as '3/4 length dark green leather jacket with a belted waist'.
Do not describe colours, materials, features, or write a long description yet."""}, _image_input(data_url, detail="high")]}],
        text_format=ProductCategorization,
    )
    if response.output_parsed is None:
        raise ValueError("product categorization returned no result")
    categorization = response.output_parsed
    if categorization.category == ProductCategory.BOTTOMS:
        # The model identifies the subtype, but the family is assigned by the
        # backend mapping so users and model output cannot override routing.
        family = get_bottoms_family_for_subtype(categorization.subtype)
        categorization.product_family = family
        if family is None:
            categorization.subtype = None
    else:
        categorization.product_family = (
            categorization.product_family
            if categorization.category == ProductCategory.UNDERWEAR
            else None
        )
        categorization.subtype = None
    return categorization


def screen_product_image(client: OpenAI, data_url: str) -> ImageScreeningResult:
    """Decide whether an image contains an allowed wearable fashion product."""
    response = _parse_response(client,
        model=_vision_model(),
        input=[{"role": "user", "content": [{"type": "input_text", "text": """Act as a strict product-image gate.
Pass only when the image clearly shows a wearable clothing or fashion product intended for a catalogue: clothing, footwear, headwear, scarves, gloves, jewellery, watches, belts or neckwear. Bags, backpacks, luggage and purses are outside the supported clothing product scope and must be rejected.

Reject when the main subject is an unrelated object, food, animal, vehicle, furniture, room, landscape, person without a clearly identifiable fashion product, promotional graphic, poster, advertisement, text design, website screenshot, app screenshot, collage, or image where the product cannot be identified. A screenshot or file containing a simple label is allowed when the main content is a clear product photograph; reject only when the screenshot/UI/graphic is the main content. Do not pass an image merely because it contains a person or text. A person wearing a clearly identifiable fashion product may pass. A clear back, side, rear, folded, hanging, or detail view of a recognizable single product may also pass; a front view is not required. Reject only when the product itself cannot be identified from the image.

Return passed=false with a short, specific reason for anything rejected. Return passed=true only when exactly one candidate fashion product is clearly identifiable. Count distinct candidate products, not a person, body parts, or incidental background details. A model's supporting clothes are styling when one product is clearly emphasised by framing, focus, graphic visibility or composition; do not count those supporting clothes as submitted products. Set supporting_clothing_is_styling=true in that case. For example, trousers or a skirt worn beneath a prominently framed shirt are styling, while a balanced outfit image that promotes the top and bottom equally contains multiple candidate products. Reject flat lays, wardrobes, outfit collages, or scenes where multiple products are equally plausible as the submitted item. Set primary_item_clear=true only when one product is clearly the intended subject."""}, _image_input(data_url, detail="high")]}],
        text_format=ImageScreeningResult,
    )
    if response.output_parsed is None:
        raise ValueError("image screening returned no decision")
    return response.output_parsed


class IdentifiedProduct(BaseModel):
    product_number: int = Field(ge=1)
    image_numbers: list[int] = Field(min_length=1)
    grouping_reason: str = Field(min_length=10, max_length=300)
    analysis: ProductAnalysis


class BatchAnalysisResult(BaseModel):
    passed: bool
    unique_product_count: int = Field(ge=0)
    products: list[IdentifiedProduct] = Field(default_factory=list)
    rejected_images: list[RejectedImage] = Field(default_factory=list)
    # Original image number -> model-derived media coverage. Keeping this at
    # image level lets readiness explain exactly which upload supports a card.
    image_evidence: dict[str, dict[str, object]] = Field(default_factory=dict)
    reason: str = Field(min_length=10, max_length=300)


def identify_product_image(client: OpenAI, data_url: str) -> ProductIdentity:
    response = _parse_response(client,
        model=_vision_model(),
        input=[{"role": "user", "content": [{"type": "input_text", "text": "Describe this single fashion product image for identity matching across a batch. Record only visible evidence. Identify the specific product type, dominant colour or colourway, pattern or finish, and a concise visual signature covering distinctive shape, construction, closures, panels, trims, hardware or other details. Also classify every clearly visible media view using only: front_view, rear_view, top_view, side_view, sole_or_underside, flat_lay, detail, worn, unknown. Record concrete visible evidence relevant to template readiness, such as rear_pockets, waistband, outsole_tread, heel, cuff, print, pattern, toe_shape, or fabric_texture. Do not claim a view or detail that is hidden, obstructed or not visible. Do not identify the model, background, photography style, brand, SKU or hidden information."}, _image_input(data_url, detail="high")]}],
        text_format=ProductIdentity,
    )
    if response.output_parsed is None:
        raise ValueError("product identity summary returned no result")
    return response.output_parsed


def _grouping_content(data_urls: list[str], identities: list[ProductIdentity] | None = None, categories: list[ProductCategorization] | None = None) -> list:
    content: list[dict[str, str]] = [{"type": "input_text", "text": """You are grouping images for a fashion product catalogue.
Identify which images represent the same catalogue product. A catalogue product is one distinct purchasable item or product variant. Images of the same item may show different angles, sides, details, crops, poses, lighting, backgrounds, or model views.
Group images together only when visible evidence indicates they represent the same item. Consider the complete visual identity: overall shape and silhouette, colour and colourway, print or pattern, material appearance, construction, seams, panels, pockets, closures, fastenings, straps, handles, soles, trims, hardware, proportions, and other distinctive details.
Keep images in separate groups when they show different product identities, including separately distinguishable variants that differ in visible design, colour, pattern, construction, finish, or other product-defining characteristics.
Do not merge images only because products share a broad category, similar shape or style, similar material, photography, model, background, collection, or batch. Product category and product type are not sufficient evidence. The person, model, mannequin, pose, background, and photography style are not product identity evidence.
Do not split images because of normal lighting, shadows, white balance, reflections, camera processing, or minor photographic variation.
For clothing, footwear, headwear, scarves, gloves, jewellery, watches, belts and neckwear, use the relevant visible identity details for that product type. Bags, backpacks, luggage and purses are not supported product categories. When evidence is insufficient to determine whether images show the same item, prefer separate groups rather than making an unsupported merge. False merging is more damaging than creating an additional group.
Every image must appear in exactly one group. Do not omit, duplicate, or reuse image numbers.
For each group return a sequential product number, all image numbers in the group, a concise explanation of the visible evidence, a confidence score from 0 to 1, and the key characteristics distinguishing it from other groups. Base decisions only on visible product evidence. Do not infer brand, SKU, size, price, collection, stock identity, or other hidden information."""}]
    for number, data_url in enumerate(data_urls, start=1):
        content.append({"type": "input_text", "text": f"Image {number}:"})
        if identities and number <= len(identities):
            identity = identities[number - 1]
            category_text = f"; category={categories[number - 1].category.value}; categorised type={categories[number - 1].product_type}" if categories and number <= len(categories) else ""
            content.append({"type": "input_text", "text": f"Independent image analysis: type={identity.product_type}; dominant colour/colourway={identity.dominant_colour}; pattern or finish={identity.pattern_or_finish}; visual signature={identity.visual_signature}{category_text}"})
        content.append(_image_input(data_url, detail="high"))
    return content


def _group_product_images_once(client: OpenAI, data_urls: list[str], identities: list[ProductIdentity] | None = None, categories: list[ProductCategorization] | None = None) -> BatchScreeningResult:
    """Group one token-bounded set, preserving the existing matching criteria."""
    content = _grouping_content(data_urls, identities, categories)
    expected = list(range(1, len(data_urls) + 1))
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = _parse_response(client, model=_vision_model(), input=[{"role": "user", "content": content}], text_format=BatchScreeningResult)
            if response.output_parsed is None:
                raise ValueError("batch grouping returned no decision")
            result = response.output_parsed
            all_numbers = [number for group in result.groups for number in group.image_numbers]
            if sorted(all_numbers) != expected or len(set(all_numbers)) != len(all_numbers):
                raise ValueError("batch grouping did not assign every image exactly once")
            result.unique_product_count = len(result.groups)
            return result
        except (AnalysisBudgetError, AnalysisSafetyError):
            raise
        except (ValueError, ValidationError) as exc:
            last_error = exc
            content[0]["text"] = content[0]["text"] + "\nYour previous grouping response was invalid. Assign every image number exactly once, with no missing or duplicate numbers."
    # Identity annotations improve difficult colourway decisions, but a malformed
    # annotated response must not fail the whole batch. Retry the same visual
    # grouping request without annotations as a safe fallback.
    if identities:
        return _group_product_images_once(client, data_urls)
    raise ValueError("batch grouping did not produce a valid complete assignment") from last_error


def _grouping_fits(data_urls: list[str], identities=None, categories=None) -> bool:
    content = [{"role": "user", "content": _grouping_content(data_urls, identities, categories)}]
    tokens = estimate_request_tokens(content, text_format=BatchScreeningResult, model=_vision_model())
    # Leave room for the existing validation-retry instructions, as well as output.
    return tokens + 1024 <= _request_limiter(_vision_model()).input_budget()


def group_product_images(client: OpenAI, data_urls: list[str], identities: list[ProductIdentity] | None = None, categories: list[ProductCategorization] | None = None) -> BatchScreeningResult:
    """Bound both image chunks and representative comparisons by their token cost."""
    def select(items, indices):
        return [items[index] for index in indices] if items is not None else None

    def fits(indices):
        return _grouping_fits(select(data_urls, indices), select(identities, indices), select(categories, indices))

    def compare(indices):
        return _group_product_images_once(client, select(data_urls, indices), select(identities, indices), select(categories, indices))

    def remap(result, members):
        return [ProductImageGroup(
            product_number=index + 1,
            image_numbers=[number for member in group.image_numbers for number in members[member - 1].image_numbers],
            reason=group.reason,
        ) for index, group in enumerate(result.groups)]

    if not data_urls:
        raise ValueError("at least one image is required for grouping")
    if fits(list(range(len(data_urls)))):
        return compare(list(range(len(data_urls))))

    chunks: list[list[int]] = []
    current: list[int] = []
    for index in range(len(data_urls)):
        if current and (len(current) >= 12 or not fits(current + [index])):
            chunks.append(current)
            current = []
        if not fits([index]):
            raise AnalysisBudgetError("A grouping image exceeds the configured input-token budget; increase the budget within your API limits.")
        current.append(index)
    if current:
        chunks.append(current)

    chunk_groups: list[ProductImageGroup] = []
    for indices in chunks:
        result = compare(indices)
        chunk_groups.extend(ProductImageGroup(
            product_number=len(chunk_groups) + index + 1,
            image_numbers=[indices[number - 1] + 1 for number in group.image_numbers],
            reason=group.reason,
        ) for index, group in enumerate(result.groups))

    representatives = [group.image_numbers[0] - 1 for group in chunk_groups]
    if fits(representatives):
        groups = remap(compare(representatives), chunk_groups)
    else:
        # The old final merge could exceed context even when every chunk fitted.
        # Compare each new representative against bounded windows of prior groups.
        # Every prior group is considered, without sending the entire batch again.
        groups: list[ProductImageGroup] = []
        for candidate in chunk_groups:
            remaining = list(groups)
            kept: list[ProductImageGroup] = []
            while remaining:
                window: list[ProductImageGroup] = []
                while remaining:
                    indices = [candidate.image_numbers[0] - 1] + [group.image_numbers[0] - 1 for group in window + remaining[:1]]
                    if not fits(indices):
                        break
                    window.append(remaining.pop(0))
                if not window:
                    raise AnalysisBudgetError("Two product representatives exceed the configured grouping token budget; increase the budget within your API limits.")
                members = [candidate] + window
                merged = compare([group.image_numbers[0] - 1 for group in members])
                mapped = remap(merged, members)
                for decision, mapped_group in zip(merged.groups, mapped):
                    if 1 in decision.image_numbers:
                        candidate = mapped_group
                    else:
                        kept.append(mapped_group)
            groups = kept + [candidate]

    groups.sort(key=lambda group: min(group.image_numbers))
    for number, group in enumerate(groups, start=1):
        group.product_number = number
        group.image_numbers.sort()
    return BatchScreeningResult(passed=True, unique_product_count=len(groups), groups=groups, reason="All images were grouped using token-bounded comparisons.")


def _analyze_product_images(image_bytes_list: list[bytes], *, api_key: str | None = None, model: str | None = None, run_safety_check: bool = True, progress_callback: Callable[[str, str, int, int, int], None] | None = None, max_concurrency: int | None = None) -> BatchAnalysisResult:
    """Screen a batch and report how many unique fashion products it contains."""
    if not image_bytes_list:
        raise ValueError("at least one image is required")
    concurrency = AnalysisLimits.from_env().concurrency if max_concurrency is None else max_concurrency
    if not isinstance(concurrency, int) or isinstance(concurrency, bool) or not 1 <= concurrency <= 8:
        raise ValueError("image analysis concurrency must be between 1 and 8")
    def report(stage: str, message: str, completed: int, total: int, percent: int) -> None:
        if progress_callback:
            progress_callback(stage, message, completed, total, percent)

    images: list[PrescreenedImage] = []
    validated_numbers: list[int] = []
    report("validation", "Checking uploaded images", 0, len(image_bytes_list), 2)
    rejected: list[RejectedImage] = []
    for number, image_bytes in enumerate(image_bytes_list, start=1):
        try:
            images.append(prescreen_image(image_bytes))
            validated_numbers.append(number)
        except ValueError as exc:
            rejected.append(RejectedImage(image_number=number, reason=str(exc)))
        report("validation", f"Validated image {number} of {len(image_bytes_list)}", number, len(image_bytes_list), 2 + round(number / len(image_bytes_list) * 13))
    if not images:
        return BatchAnalysisResult(passed=False, unique_product_count=0, rejected_images=rejected, reason="No images passed technical validation.")
    with _analysis_session(api_key, model):
        model = _vision_model()
        client = _analysis_client.get()
        data_urls = [_data_url(image) for image in images]
        accepted_data_urls: list[str] = []
        accepted_numbers: list[int] = []
        identities: list[ProductIdentity] = []
        categories: list[ProductCategorization] = []
        report("screening", "Screening accepted images", 0, len(data_urls), 15)

        cancel_event = Event()
        router = _analysis_router.get()
        selected_model = _vision_model()

        def image_steps(data_url: str):
            # Only independent images overlap. Every image must pass each gate in order.
            _check_cancelled()
            if run_safety_check:
                moderation = _moderate_image(client, data_url)
                if moderation.results[0].flagged:
                    return None, None, "Image did not pass the safety check."
            _check_cancelled()
            screening = screen_product_image(client, data_url)
            acceptable_styled_product = (
                screening.primary_item_clear
                and screening.item_count == 2
            )
            if (not screening.passed or screening.item_count != 1 or not screening.primary_item_clear) and not acceptable_styled_product:
                return None, None, screening.reason
            _check_cancelled()
            identity = identify_product_image(client, data_url)
            _check_cancelled()
            category = categorize_product_image(client, data_url)
            return identity, category, None

        def check_image(data_url: str):
            context = _analysis_cancel.set(cancel_event)
            model_context = _analysis_model.set(selected_model)
            router_context = _analysis_router.set(router)
            try:
                return image_steps(data_url)
            except AnalysisSafetyError as exc:
                return None, None, str(exc)
            finally:
                _analysis_cancel.reset(context)
                _analysis_model.reset(model_context)
                _analysis_router.reset(router_context)

        checked = {}
        with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="image-analysis") as executor:
            futures = {executor.submit(check_image, data_url): index for index, data_url in enumerate(data_urls)}
            try:
                for completed, future in enumerate(as_completed(futures), start=1):
                    checked[futures[future]] = future.result()
                    # SQLAlchemy-backed progress callbacks stay on the coordinator thread.
                    report("analysis", f"Analysed image {completed} of {len(data_urls)}", completed, len(data_urls), 15 + round(completed / len(data_urls) * 45))
            except Exception:
                cancel_event.set()
                for future in futures:
                    future.cancel()
                raise

        # Completion order must never change image numbers or the grouping annotations.
        for index, data_url in enumerate(data_urls):
            number = validated_numbers[index]
            identity, category, rejection_reason = checked[index]
            if rejection_reason:
                rejected.append(RejectedImage(image_number=number, reason=rejection_reason))
                continue
            accepted_data_urls.append(data_url)
            accepted_numbers.append(number)
            identities.append(identity)
            categories.append(category)
        rejected.sort(key=lambda item: item.image_number)
        if not accepted_data_urls:
            return BatchAnalysisResult(passed=False, unique_product_count=0, rejected_images=rejected, reason="No images passed validation and product screening.")
        report("grouping", "Comparing analysed images and finding product groups", 0, len(accepted_data_urls), 62)
        grouping = group_product_images(client, accepted_data_urls, identities, categories)
        report("grouping", f"Found {len(grouping.groups)} product groups", len(accepted_data_urls), len(accepted_data_urls), 75)
        accepted_bytes = [image_bytes_list[number - 1] for number in accepted_numbers]

        def synthesize_group(group: ProductImageGroup) -> IdentifiedProduct:
            context = _analysis_cancel.set(cancel_event)
            model_context = _analysis_model.set(selected_model)
            router_context = _analysis_router.set(router)
            client_context = _analysis_client.set(client)
            try:
                _check_cancelled()
                local_numbers = group.image_numbers
                original_numbers = [accepted_numbers[number - 1] for number in local_numbers]
                representative = accepted_bytes[local_numbers[0] - 1]
                member_categories = [categories[number - 1].category for number in local_numbers]
                group_category = max(set(member_categories), key=member_categories.count)
                representative_category = next((categories[number - 1] for number in local_numbers if categories[number - 1].category == group_category), categories[local_numbers[0] - 1])
                analysis = analyze_product_image(representative, api_key=api_key, model=model, run_safety_check=False, screen_already=True, known_categorization=representative_category)
                analysis.category = group_category
                return IdentifiedProduct(product_number=group.product_number, image_numbers=original_numbers, grouping_reason=group.reason, analysis=analysis)
            finally:
                _analysis_cancel.reset(context)
                _analysis_model.reset(model_context)
                _analysis_router.reset(router_context)
                _analysis_client.reset(client_context)

        report("synthesis", "Preparing product details", 0, len(grouping.groups), 75)
        synthesized: dict[int, IdentifiedProduct] = {}
        with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="product-details") as executor:
            futures = {executor.submit(synthesize_group, group): index for index, group in enumerate(grouping.groups)}
            try:
                for completed, future in enumerate(as_completed(futures), start=1):
                    synthesized[futures[future]] = future.result()
                    report("synthesis", f"Preparing product details {completed} of {len(grouping.groups)}", completed, len(grouping.groups), 75 + round(completed / len(grouping.groups) * 25))
            except Exception:
                cancel_event.set()
                for future in futures:
                    future.cancel()
                raise
        products = [synthesized[index] for index in range(len(grouping.groups))]
        image_evidence = {
            str(number): {
                "views": identity.media_views,
                "evidence": identity.visible_evidence,
            }
            for number, identity in zip(accepted_numbers, identities)
        }
        return BatchAnalysisResult(passed=True, unique_product_count=len(products), products=products, rejected_images=rejected, image_evidence=image_evidence, reason="Accepted images were grouped and analysed; rejected images were omitted.")


def _analyze_product_image(image_bytes: bytes, *, api_key: str | None = None, model: str | None = None, run_safety_check: bool = True, screen_already: bool = False, known_categorization: ProductCategorization | None = None) -> ProductAnalysis:
    """Screen and analyse one product image using an OpenAI vision model."""
    image = prescreen_image(image_bytes)
    with _analysis_session(api_key, model):
        model = _vision_model()
        client = _analysis_client.get()
        data_url = _data_url(image)
        if run_safety_check:
            moderation = _moderate_image(client, data_url)
            if moderation.results[0].flagged:
                raise ImageRejectedError(ImageScreeningResult(passed=False, item_count=0, primary_item_clear=False, reason="Image did not pass the safety check."))

        screening = screen_product_image(client, data_url) if not screen_already else None
        acceptable_styled_product = bool(
            screening
            and screening.primary_item_clear
            and screening.item_count == 2
        )
        if screening is not None and (not screening.passed or screening.item_count != 1 or not screening.primary_item_clear) and not acceptable_styled_product:
            if screening.item_count != 1:
                screening.reason = f"The image contains {screening.item_count} candidate fashion items; exactly one clearly identifiable product is required."
            elif not screening.primary_item_clear:
                screening.reason = "No single fashion product is clearly identifiable as the item being submitted."
            screening.passed = False
            raise ImageRejectedError(screening)

        categorization = known_categorization or categorize_product_image(client, data_url)
        instructions = f"""Analyse this approved wearable fashion product photograph for an ecommerce catalogue.
    The separate categorization step identified the product as category '{categorization.category}', family '{categorization.product_family or "not established"}', and type '{categorization.product_type}'. Use those values unless the image clearly disproves them.
    For underwear and bottoms, preserve the supplied product family when supported. For bottoms, preserve the supplied subtype and family; do not change the system-controlled family. Populate only applicable details and use not_applicable for irrelevant fields. A null family is valid when the image does not support a confident family assignment.

    Return only the requested structured fields.
    - Generate a concise, human-friendly product name of no more than 5 words, such as 'Pink cotton shirt', 'Black leather jacket', or 'White low-top trainers'. Include the dominant visible colour and product type when useful. Do not use placeholders such as 'Unconfirmed product'.
    - Use the category and product type supplied by the categorization step.
    - Make product_type highly specific, for example '3/4 length dark green leather jacket with a belted waist'.
    - Populate colour_details with the primary colour, every visible secondary colour, pattern, colour distribution, tonal variation, saturation, brightness, finish, wash/fade treatment and any colour uncertainties. Preserve observed colour wording; do not normalise it to a generic colour name.
    - Describe colours specifically in the legacy colours field as a concise summary of the same evidence.
    - Name only materials visible or strongly supported by the image. Describe apparent fibre, thickness, weight, drape, texture, stretch, sheen, finish, washing, fading, wrinkles, wear and surface variation. Use 'appears to be' when uncertain; never claim an exact fibre composition from an image alone.
    - List every visible commercial feature: pattern, pockets, zips, buttons, seams, straps, laces, sole, collar, cuffs, hardware, and so on. Treat every print, illustration, logo, embroidery and appliqué as identity-critical artwork. Describe its exact subject and topology: component count, shapes, relative positions, orientation, linework, internal details, colour boundaries and relationship to seams, as well as any text, numbers, placement, scale, spacing, fading, distress and edge quality. Never reduce distinctive artwork to only a generic subject label.
    - For every visible identity-critical artwork, populate global_details.branding.artwork_regions. source_bounds must be a tight normalized [x, y, width, height] rectangle after applying global_details.source_rotation_degrees. garment_relative_bounds must be the same artwork rectangle relative to the visible garment's own bounding rectangle after that rotation. Exclude the model, skin, other clothes and background from the rectangle. Include transparent or base-fabric gaps within the artwork itself. extraction_confidence measures whether the artwork boundary and pixels are sufficiently clear to reuse; lower it for obstruction, blur, severe folds or cropping. Do not create artwork_regions for ordinary fabric patterns that cover the whole garment.
    - Distinguish observed product properties from properties hidden by a model, pose, cropping, lighting or image quality. Mark a property uncertain only when it is genuinely hidden, obstructed, cropped or impossible to assess. Do not mark a clearly visible neckline, collar, sleeve, seam, graphic or surface feature as uncertain merely because its exact measurement is unavailable.
    - Populate global_details completely. Include every colour, material, construction, functional detail, callout, branding and uncertainty field. Do not shorten, summarise or truncate long construction or functional detail lists.
    - Set global_details.source_rotation_degrees to the clockwise rotation required to make the photographed product upright after normal image metadata has been applied. Use only 0, 90, 180 or 270. Judge orientation from the neckline, shoulders, sleeves and hem rather than trusting camera metadata.
    - Populate category_details using the complete schema for the detected category. Include every applicable field and list every visible detail; use visible_uncertainties for fields that cannot be determined. For underwear and bottoms, set category_details.family to the same family as product_family when supplied, and leave irrelevant or uncertain family-specific details null or not_applicable.
    - Populate confidence_details for every section. Scores must reflect visible evidence, not general model certainty. Include evidence and uncertainties for every score. Use not_visible when an attribute cannot be assessed. Never give high confidence to inferred size, hidden construction, exact fibre composition or unconfirmed branding. A graphic subject being recognisable is not enough for high branding or identity confidence; use high confidence only when the artwork's exact visible geometry and details have been captured.
    - In confidence_details.gender, use source='user' only when a user-confirmed gender was supplied. A user-confirmed gender is authoritative over any assumed gender.
    - In global_details.gender, keep assumed and user_confirmed separate. user_confirmed must remain null unless the user explicitly supplied a gender. If a user-confirmed value exists, it is authoritative and must override assumed.
    - For tops, populate tops_details with the neckline type and depth, collar thickness/width/rigidity, sleeve type/length/width, shoulder shape/drop, body width relative to length, silhouette volume, neck binding, hem shape/position, fit, garment length, drape, rigidity, wrinkle visibility, surface softness, fabric body, wash treatment, fade level, graphic condition/scale/placement/edge quality, material appearance, apparent weight, surface texture, finish, construction details and visible uncertainties. When the neckline and collar are visible, describe their actual visible construction rather than returning 'not_visible'. These fields must describe this product, not a generic example of its category. Resolve shoulder and sleeve terminology clearly; describe dropped or relaxed shoulders and loose sleeves explicitly when visible.
    - Record what is not visible or cannot be determined in visible_uncertainties. Never infer numeric size, hidden construction, brand or fibre composition.
    - Write a factual, specific 45–60 word description using only visible evidence. Do not invent brand, size, price, or hidden features.
    - Confidence must reflect how clearly the image supports the result, from 0 to 1.
    """
        content = [{"type": "input_text", "text": instructions}, _image_input(data_url, detail="high")]
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = _parse_response(client, model=_vision_model(), input=[{"role": "user", "content": content}], text_format=ProductAnalysis)
                if response.output_parsed is None:
                    raise ValueError("AI returned no structured product analysis")
                analysis = response.output_parsed
                if analysis.category not in (ProductCategory.UNDERWEAR, ProductCategory.BOTTOMS) and analysis.product_family is not None:
                    raise ValueError("product_family is only valid for categories with rendering families")
                if analysis.category == ProductCategory.BOTTOMS:
                    # Bottoms categorization is authoritative, including an
                    # intentional null when subtype/family is uncertain.
                    analysis.product_family = categorization.product_family
                elif analysis.category == ProductCategory.UNDERWEAR and categorization.product_family is not None:
                    # Categorization is the family authority; detailed analysis
                    # must not silently broaden or change the template family.
                    analysis.product_family = categorization.product_family
                if analysis.colour_details is None or analysis.global_details is None:
                    raise ValueError("colour_details and global_details are required for product analysis")
                if analysis.confidence_details is not None and analysis.confidence_details.gender.source == "user" and analysis.global_details.gender.user_confirmed is None:
                    raise ValueError("user-sourced gender confidence requires a user_confirmed value")
                category_model = CATEGORY_DETAIL_MODELS.get(analysis.category.value)
                if category_model is not None:
                    if analysis.category_details is None:
                        raise ValueError("category_details are required for product analysis")
                    analysis.category_details = category_model.model_validate(analysis.category_details)
                    if analysis.category == ProductCategory.UNDERWEAR and analysis.product_family is not None:
                        analysis.category_details.family = analysis.product_family
                    if analysis.category == ProductCategory.BOTTOMS:
                        analysis.category_details.family = analysis.product_family
                if analysis.category == ProductCategory.TOPS and analysis.tops_details is None:
                    raise ValueError("tops_details is required for tops analysis")
                words = analysis.description.split()
                if len(words) < 45:
                    words.extend("The product is presented as a wearable fashion item for catalogue use with details based only on visible evidence.".split())
                analysis.description = " ".join(words[:60])
                return analysis
            except (ValidationError, ValueError) as exc:
                last_error = exc
                content[0]["text"] = instructions + "\nYour previous answer failed validation. Include every colour_details field and, for tops, every tops_details field. The description must contain 45–60 factual words. Retry using only visible product evidence."
        raise ValueError("AI returned product details that did not meet the required format") from last_error


def analyze_media_evidence(image_bytes: bytes, *, api_key: str | None = None, model: str | None = None) -> dict[str, object]:
    """Extract source-media coverage without repeating full product analysis."""
    image = prescreen_image(image_bytes)
    with _analysis_session(api_key, model):
        identity = identify_product_image(_analysis_client.get(), _data_url(image))
    return {"views": identity.media_views, "evidence": identity.visible_evidence}


def analyze_product_images(image_bytes_list: list[bytes], *, api_key: str | None = None, model: str | None = None,
                           run_safety_check: bool = True, progress_callback=None, max_concurrency: int | None = None) -> BatchAnalysisResult:
    return _analyze_product_images(image_bytes_list, api_key=api_key, model=model,
                                  run_safety_check=run_safety_check, progress_callback=progress_callback, max_concurrency=max_concurrency)


def analyze_product_image(image_bytes: bytes, *, api_key: str | None = None, model: str | None = None,
                          run_safety_check: bool = True, screen_already: bool = False,
                          known_categorization: ProductCategorization | None = None) -> ProductAnalysis:
    return _analyze_product_image(image_bytes, api_key=api_key, model=model, run_safety_check=run_safety_check,
                                 screen_already=screen_already, known_categorization=known_categorization)
