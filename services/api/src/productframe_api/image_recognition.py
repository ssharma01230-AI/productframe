"""Safe product-image screening and structured visual analysis.

The screening gate runs before detailed analysis. It accepts wearable fashion
products (including accessories) and rejects unrelated objects, graphics, and
screenshots.
"""
from __future__ import annotations

import base64
import io
import os
import time
from enum import StrEnum
from typing import Annotated, Callable

from openai import OpenAI, RateLimitError
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, ValidationError, field_validator

MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_DIMENSION = 10_000
MAX_ANALYSIS_DIMENSION = 2_048
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
OPENAI_MAX_RETRIES = 8
OPENAI_MIN_INTERVAL_SECONDS = 1.0
_last_openai_call = 0.0


def _openai_call(operation):
    """Throttle and retry OpenAI calls instead of failing on transient 429s."""
    global _last_openai_call
    delay = 2.0
    for attempt in range(OPENAI_MAX_RETRIES):
        wait = OPENAI_MIN_INTERVAL_SECONDS - (time.monotonic() - _last_openai_call)
        if wait > 0:
            time.sleep(wait)
        try:
            result = operation()
            _last_openai_call = time.monotonic()
            return result
        except RateLimitError:
            _last_openai_call = time.monotonic()
            if attempt == OPENAI_MAX_RETRIES - 1:
                raise
            time.sleep(min(delay, 60.0))
            delay *= 2


def _image_input(data_url: str, detail: str = "low") -> dict[str, str]:
    return {"type": "input_image", "image_url": data_url, "detail": detail}


class ProductCategory(StrEnum):
    OUTERWEAR = "outerwear"
    TOPS = "tops"
    BOTTOMS = "bottoms"
    SOCKS = "socks"
    FOOTWEAR = "footwear"
    UNDERWEAR = "underwear"
    ACCESSORIES = "accessories"


class ProductCategorization(BaseModel):
    category: ProductCategory
    product_type: str = Field(min_length=5, max_length=120)
    confidence: float = Field(ge=0, le=1)


class ImageScreeningResult(BaseModel):
    """The mandatory pass/fail decision made before product analysis."""

    passed: bool
    detected_item: str | None = None
    item_count: int = Field(ge=0, le=20)
    primary_item_clear: bool
    reason: str = Field(min_length=10, max_length=300)


class ProductIdentity(BaseModel):
    product_type: str = Field(min_length=3, max_length=120)
    dominant_colour: str = Field(min_length=3, max_length=120)
    pattern_or_finish: str = Field(min_length=3, max_length=160)
    visual_signature: str = Field(min_length=10, max_length=300)


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


class ProductAnalysis(BaseModel):
    product_name: str = Field(min_length=3, max_length=160)
    category: ProductCategory
    product_type: str = Field(min_length=5, max_length=120)
    colours: str = Field(min_length=5, max_length=300)
    materials: str = Field(min_length=3, max_length=300)
    features: list[str] = Field(min_length=1, max_length=30)
    description: str = Field(min_length=30, max_length=320)
    confidence: float = Field(ge=0, le=1)

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
        with Image.open(io.BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            image.thumbnail((MAX_ANALYSIS_DIMENSION, MAX_ANALYSIS_DIMENSION), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=88, optimize=True)
            return PrescreenedImage(image_bytes=output.getvalue(), content_type="image/jpeg", width=width, height=height, original_format=original_format)
    except UnidentifiedImageError as exc:
        raise ValueError("file is not a readable image") from exc


def _data_url(image: PrescreenedImage) -> str:
    encoded = base64.b64encode(image.image_bytes).decode("ascii")
    return f"data:{image.content_type};base64,{encoded}"


def categorize_product_image(client: OpenAI, data_url: str) -> ProductCategorization:
    """Categorize an approved image before detailed attribute analysis."""
    response = _openai_call(lambda: client.responses.parse(
        model="gpt-4o-mini",
        input=[{"role": "user", "content": [{"type": "input_text", "text": """Categorize this already-approved wearable fashion product.
Choose exactly one category: outerwear, tops, bottoms, socks, footwear, underwear, accessories.
Return a highly specific product_type, such as '3/4 length dark green leather jacket with a belted waist'.
Do not describe colours, materials, features, or write a long description yet."""}, _image_input(data_url, detail="high")]}],
        text_format=ProductCategorization,
    ))
    if response.output_parsed is None:
        raise ValueError("product categorization returned no result")
    return response.output_parsed


def screen_product_image(client: OpenAI, data_url: str) -> ImageScreeningResult:
    """Decide whether an image contains an allowed wearable fashion product."""
    response = _openai_call(lambda: client.responses.parse(
        model="gpt-4o-mini",
        input=[{"role": "user", "content": [{"type": "input_text", "text": """Act as a strict product-image gate.
Pass only when the image clearly shows a wearable fashion product intended for a catalogue: clothing, footwear, or a fashion accessory. Accessories include jewellery, watches, sunglasses, hats, caps, scarves, belts, bags, gloves, and hair accessories.

Reject when the main subject is an unrelated object, food, animal, vehicle, furniture, room, landscape, person without a clearly identifiable fashion product, promotional graphic, poster, advertisement, text design, website screenshot, app screenshot, collage, or image where the product cannot be identified. A screenshot or file containing a simple label is allowed when the main content is a clear product photograph; reject only when the screenshot/UI/graphic is the main content. Do not pass an image merely because it contains a person or text. A person wearing a clearly identifiable fashion product may pass. A clear back, side, rear, folded, hanging, or detail view of a recognizable single product may also pass; a front view is not required. Reject only when the product itself cannot be identified from the image.

Return passed=false with a short, specific reason for anything rejected. Return passed=true only when exactly one candidate fashion product is clearly identifiable. Count distinct candidate products, not a person, body parts, or incidental background details. If a model is wearing one clearly featured product, treat other ordinary garments needed to wear it (such as trousers under a shirt) as incidental, not additional candidate products. Reject flat lays, wardrobes, outfit collages, or scenes where multiple products are equally plausible as the submitted item. Set primary_item_clear=true only when one product is clearly the intended subject."""}, _image_input(data_url, detail="high")]}],
        text_format=ImageScreeningResult,
    ))
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
    reason: str = Field(min_length=10, max_length=300)


def identify_product_image(client: OpenAI, data_url: str) -> ProductIdentity:
    response = _openai_call(lambda: client.responses.parse(
        model="gpt-4o-mini",
        input=[{"role": "user", "content": [{"type": "input_text", "text": "Describe this single fashion product image for identity matching across a batch. Record only visible evidence. Identify the specific product type, dominant colour or colourway, pattern or finish, and a concise visual signature covering distinctive shape, construction, closures, panels, trims, hardware or other details. Do not identify the model, background, photography style, brand, SKU or hidden information."}, _image_input(data_url, detail="high")]}],
        text_format=ProductIdentity,
    ))
    if response.output_parsed is None:
        raise ValueError("product identity summary returned no result")
    return response.output_parsed


def _group_product_images_once(client: OpenAI, data_urls: list[str], identities: list[ProductIdentity] | None = None, categories: list[ProductCategorization] | None = None) -> BatchScreeningResult:
    """Group one bounded set of images in a single model request."""
    content: list[dict[str, str]] = [{"type": "input_text", "text": """You are grouping images for a fashion product catalogue.
Identify which images represent the same catalogue product. A catalogue product is one distinct purchasable item or product variant. Images of the same item may show different angles, sides, details, crops, poses, lighting, backgrounds, or model views.
Group images together only when visible evidence indicates they represent the same item. Consider the complete visual identity: overall shape and silhouette, colour and colourway, print or pattern, material appearance, construction, seams, panels, pockets, closures, fastenings, straps, handles, soles, trims, hardware, proportions, and other distinctive details.
Keep images in separate groups when they show different product identities, including separately distinguishable variants that differ in visible design, colour, pattern, construction, finish, or other product-defining characteristics.
Do not merge images only because products share a broad category, similar shape or style, similar material, photography, model, background, collection, or batch. Product category and product type are not sufficient evidence. The person, model, mannequin, pose, background, and photography style are not product identity evidence.
Do not split images because of normal lighting, shadows, white balance, reflections, camera processing, or minor photographic variation.
For clothing, footwear, bags, jewellery, and other accessories, use the relevant visible identity details for that product type. When evidence is insufficient to determine whether images show the same item, prefer separate groups rather than making an unsupported merge. False merging is more damaging than creating an additional group.
Every image must appear in exactly one group. Do not omit, duplicate, or reuse image numbers.
For each group return a sequential product number, all image numbers in the group, a concise explanation of the visible evidence, a confidence score from 0 to 1, and the key characteristics distinguishing it from other groups. Base decisions only on visible product evidence. Do not infer brand, SKU, size, price, collection, stock identity, or other hidden information."""}]
    for number, data_url in enumerate(data_urls, start=1):
        content.append({"type": "input_text", "text": f"Image {number}:"})
        if identities and number <= len(identities):
            identity = identities[number - 1]
            category_text = f"; category={categories[number - 1].category.value}; categorised type={categories[number - 1].product_type}" if categories and number <= len(categories) else ""
            content.append({"type": "input_text", "text": f"Independent image analysis: type={identity.product_type}; dominant colour/colourway={identity.dominant_colour}; pattern or finish={identity.pattern_or_finish}; visual signature={identity.visual_signature}{category_text}"})
        content.append(_image_input(data_url, detail="high"))
    expected = list(range(1, len(data_urls) + 1))
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = _openai_call(lambda: client.responses.parse(model="gpt-4o-mini", input=[{"role": "user", "content": content}], text_format=BatchScreeningResult))
            if response.output_parsed is None:
                raise ValueError("batch grouping returned no decision")
            result = response.output_parsed
            all_numbers = [number for group in result.groups for number in group.image_numbers]
            if sorted(all_numbers) != expected or len(set(all_numbers)) != len(all_numbers):
                raise ValueError("batch grouping did not assign every image exactly once")
            result.unique_product_count = len(result.groups)
            return result
        except (ValueError, ValidationError) as exc:
            last_error = exc
            content[0]["text"] = content[0]["text"] + "\nYour previous grouping response was invalid. Assign every image number exactly once, with no missing or duplicate numbers."
    # Identity annotations improve difficult colourway decisions, but a malformed
    # annotated response must not fail the whole batch. Retry the same visual
    # grouping request without annotations as a safe fallback.
    if identities:
        return _group_product_images_once(client, data_urls)
    raise ValueError("batch grouping did not produce a valid complete assignment") from last_error


def group_product_images(client: OpenAI, data_urls: list[str], identities: list[ProductIdentity] | None = None, categories: list[ProductCategorization] | None = None) -> BatchScreeningResult:
    """Group large batches in bounded chunks, then merge chunk representatives."""
    if len(data_urls) <= 8:
        return _group_product_images_once(client, data_urls, identities, categories)
    chunk_groups: list[ProductImageGroup] = []
    chunk_size = 12
    for start in range(0, len(data_urls), chunk_size):
        chunk = _group_product_images_once(client, data_urls[start:start + chunk_size], identities[start:start + chunk_size] if identities else None, categories[start:start + chunk_size] if categories else None)
        chunk_groups.extend(ProductImageGroup(product_number=len(chunk_groups) + index + 1, image_numbers=[number + start for number in group.image_numbers], reason=group.reason) for index, group in enumerate(chunk.groups))
    representatives = [data_urls[group.image_numbers[0] - 1] for group in chunk_groups]
    representative_identities = [identities[group.image_numbers[0] - 1] for group in chunk_groups] if identities else None
    representative_categories = [categories[group.image_numbers[0] - 1] for group in chunk_groups] if categories else None
    merged = _group_product_images_once(client, representatives, representative_identities, representative_categories)
    groups = [ProductImageGroup(product_number=index + 1, image_numbers=[number for member in merged_group.image_numbers for number in chunk_groups[member - 1].image_numbers], reason=merged_group.reason) for index, merged_group in enumerate(merged.groups)]
    return BatchScreeningResult(passed=True, unique_product_count=len(groups), groups=groups, reason="All images were grouped using bounded batches.")


def analyze_product_images(image_bytes_list: list[bytes], *, api_key: str | None = None, model: str = "gpt-4o-mini", run_safety_check: bool = True, progress_callback: Callable[[str, str, int, int, int], None] | None = None) -> BatchAnalysisResult:
    """Screen a batch and report how many unique fashion products it contains."""
    if not image_bytes_list:
        raise ValueError("at least one image is required")
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
        report("validation", f"Validated image {number} of {len(image_bytes_list)}", number, len(image_bytes_list), round(number / len(image_bytes_list) * 15))
    if not images:
        return BatchAnalysisResult(passed=False, unique_product_count=0, rejected_images=rejected, reason="No images passed technical validation.")
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    data_urls = [_data_url(image) for image in images]
    accepted_data_urls: list[str] = []
    accepted_numbers: list[int] = []
    identities: list[ProductIdentity] = []
    categories: list[ProductCategorization] = []
    report("screening", "Screening accepted images", 0, len(data_urls), 15)
    for local_number, data_url in enumerate(data_urls, start=1):
        number = validated_numbers[local_number - 1]
        if run_safety_check:
            moderation = client.moderations.create(model="omni-moderation-latest", input=[{"type": "image_url", "image_url": {"url": data_url}}])
            if moderation.results[0].flagged:
                rejected.append(RejectedImage(image_number=number, reason="Image did not pass the safety check."))
                continue
        screening = screen_product_image(client, data_url)
        if not screening.passed or screening.item_count != 1 or not screening.primary_item_clear:
            rejected.append(RejectedImage(image_number=number, reason=screening.reason))
            continue
        accepted_data_urls.append(data_url)
        accepted_numbers.append(number)
        identities.append(identify_product_image(client, data_url))
        categories.append(categorize_product_image(client, data_url))
        report("analysis", f"Analysed image {local_number} of {len(data_urls)}", local_number, len(data_urls), 15 + round(local_number / len(data_urls) * 45))
    if not accepted_data_urls:
        return BatchAnalysisResult(passed=False, unique_product_count=0, rejected_images=rejected, reason="No images passed validation and product screening.")
    report("grouping", "Comparing analysed images and finding product groups", 0, len(accepted_data_urls), 62)
    grouping = group_product_images(client, accepted_data_urls, identities, categories)
    report("grouping", f"Found {len(grouping.groups)} product groups", len(accepted_data_urls), len(accepted_data_urls), 75)
    products = []
    accepted_bytes = [image_bytes_list[number - 1] for number in accepted_numbers]
    for group in grouping.groups:
        local_numbers = group.image_numbers
        original_numbers = [accepted_numbers[number - 1] for number in local_numbers]
        representative = accepted_bytes[local_numbers[0] - 1]
        member_categories = [categories[number - 1].category for number in local_numbers]
        group_category = max(set(member_categories), key=member_categories.count)
        representative_category = next((categories[number - 1] for number in local_numbers if categories[number - 1].category == group_category), categories[local_numbers[0] - 1])
        analysis = analyze_product_image(representative, api_key=api_key, model=model, run_safety_check=False, screen_already=True, known_categorization=representative_category)
        report("synthesis", f"Preparing product details {group.product_number} of {len(grouping.groups)}", group.product_number, len(grouping.groups), 75 + round(group.product_number / len(grouping.groups) * 25))
        analysis.category = group_category
        products.append(IdentifiedProduct(product_number=group.product_number, image_numbers=original_numbers, grouping_reason=group.reason, analysis=analysis))
    return BatchAnalysisResult(passed=True, unique_product_count=len(products), products=products, rejected_images=rejected, reason="Accepted images were grouped and analysed; rejected images were omitted.")


def analyze_product_image(image_bytes: bytes, *, api_key: str | None = None, model: str = "gpt-4o-mini", run_safety_check: bool = True, screen_already: bool = False, known_categorization: ProductCategorization | None = None) -> ProductAnalysis:
    """Screen and analyse one product image using an OpenAI vision model."""
    image = prescreen_image(image_bytes)
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    data_url = _data_url(image)
    if run_safety_check:
        moderation = client.moderations.create(model="omni-moderation-latest", input=[{"type": "image_url", "image_url": {"url": data_url}}])
        if moderation.results[0].flagged:
            raise ImageRejectedError(ImageScreeningResult(passed=False, item_count=0, primary_item_clear=False, reason="Image did not pass the safety check."))

    screening = screen_product_image(client, data_url) if not screen_already else None
    if screening is not None and (not screening.passed or screening.item_count != 1 or not screening.primary_item_clear):
        if screening.item_count != 1:
            screening.reason = f"The image contains {screening.item_count} candidate fashion items; exactly one clearly identifiable product is required."
        elif not screening.primary_item_clear:
            screening.reason = "No single fashion product is clearly identifiable as the item being submitted."
        screening.passed = False
        raise ImageRejectedError(screening)

    categorization = known_categorization or categorize_product_image(client, data_url)
    instructions = f"""Analyse this approved wearable fashion product photograph for an ecommerce catalogue.
The separate categorization step identified the product as category '{categorization.category}' and type '{categorization.product_type}'. Use those values unless the image clearly disproves them.

Return only the requested structured fields.
- Generate a concise, human-friendly product name, such as 'Pink cotton shirt', 'Black leather jacket', or 'White low-top trainers'. Include the dominant visible colour and product type when useful. Do not use placeholders such as 'Unconfirmed product'.
- Use the category and product type supplied by the categorization step.
- Make product_type highly specific, for example '3/4 length dark green leather jacket with a belted waist'.
- Describe colours specifically, including the dominant colour and important secondary colours.
- Name only materials visible or strongly supported by the image. Say 'appears to be' when uncertain.
- List every visible commercial feature: pattern, pockets, zips, buttons, seams, straps, laces, sole, collar, cuffs, hardware, and so on.
- Write a factual 30–40 word description. Do not invent brand, size, price, or hidden features.
- Confidence must reflect how clearly the image supports the result, from 0 to 1.
"""
    content = [{"type": "input_text", "text": instructions}, _image_input(data_url, detail="high")]
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = _openai_call(lambda: client.responses.parse(model=model, input=[{"role": "user", "content": content}], text_format=ProductAnalysis))
            if response.output_parsed is None:
                raise ValueError("AI returned no structured product analysis")
            analysis = response.output_parsed
            words = analysis.description.split()
            if len(words) < 30:
                words.extend("The product is presented as a wearable fashion item for catalogue use with details based only on visible evidence.".split())
            analysis.description = " ".join(words[:40])
            return analysis
        except ValidationError as exc:
            last_error = exc
            content[0]["text"] = instructions + "\nYour previous answer failed validation. The description must contain exactly 35 space-separated words. Write the description first, count every word, then return it."
    raise ValueError("AI returned product details that did not meet the required format") from last_error
