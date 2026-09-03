"""Safe product-image screening and structured visual analysis.

The screening gate runs before detailed analysis. It accepts wearable fashion
products (including accessories) and rejects unrelated objects, graphics, and
screenshots.
"""
from __future__ import annotations

import base64
import io
import os
from enum import StrEnum
from typing import Annotated

from openai import OpenAI
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, ValidationError, field_validator

MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_DIMENSION = 10_000
MAX_ANALYSIS_DIMENSION = 2_048
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


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


class ProductImageGroup(BaseModel):
    product_number: int = Field(ge=1)
    image_numbers: list[int] = Field(min_length=1)
    reason: str = Field(min_length=10, max_length=300)


class BatchScreeningResult(BaseModel):
    passed: bool
    unique_product_count: int = Field(ge=0)
    groups: list[ProductImageGroup] = Field(default_factory=list)
    rejected_images: list[int] = Field(default_factory=list)
    reason: str = Field(min_length=10, max_length=300)


class ImageRejectedError(ValueError):
    def __init__(self, screening: ImageScreeningResult):
        self.screening = screening
        super().__init__(screening.reason)


class ProductAnalysis(BaseModel):
    category: ProductCategory
    product_type: str = Field(min_length=5, max_length=120)
    colours: str = Field(min_length=5, max_length=300)
    materials: str = Field(min_length=3, max_length=300)
    features: list[str] = Field(min_length=1, max_length=30)
    description: str = Field(min_length=30, max_length=320)
    confidence: float = Field(ge=0, le=1)

    @field_validator("description")
    @classmethod
    def description_word_count(cls, value: str) -> str:
        words = value.split()
        if not 30 <= len(words) <= 40:
            raise ValueError("description must contain between 30 and 40 words")
        return value

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
    response = client.responses.parse(
        model="gpt-4o-mini",
        input=[{"role": "user", "content": [{"type": "input_text", "text": """Categorize this already-approved wearable fashion product.
Choose exactly one category: outerwear, tops, bottoms, socks, footwear, underwear, accessories.
Return a highly specific product_type, such as '3/4 length dark green leather jacket with a belted waist'.
Do not describe colours, materials, features, or write a long description yet."""}, {"type": "input_image", "image_url": data_url}]}],
        text_format=ProductCategorization,
    )
    if response.output_parsed is None:
        raise ValueError("product categorization returned no result")
    return response.output_parsed


def screen_product_image(client: OpenAI, data_url: str) -> ImageScreeningResult:
    """Decide whether an image contains an allowed wearable fashion product."""
    response = client.responses.parse(
        model="gpt-4o-mini",
        input=[{"role": "user", "content": [{"type": "input_text", "text": """Act as a strict product-image gate.
Pass only when the image clearly shows a wearable fashion product intended for a catalogue: clothing, footwear, or a fashion accessory. Accessories include jewellery, watches, sunglasses, hats, caps, scarves, belts, bags, gloves, and hair accessories.

Reject when the main subject is an unrelated object, food, animal, vehicle, furniture, room, landscape, person without a clearly identifiable fashion product, promotional graphic, poster, advertisement, text design, website screenshot, app screenshot, collage, or image where the product cannot be identified. Do not pass an image merely because it contains a person or text. A person wearing a clearly identifiable fashion product may pass.

Return passed=false with a short, specific reason for anything rejected. Return passed=true only when exactly one candidate fashion product is clearly identifiable. Count distinct candidate products, not a person, body parts, or incidental background details. If a model is wearing one clearly featured product, treat other ordinary garments needed to wear it (such as trousers under a shirt) as incidental, not additional candidate products. Reject flat lays, wardrobes, outfit collages, or scenes where multiple products are equally plausible as the submitted item. Set primary_item_clear=true only when one product is clearly the intended subject."""}, {"type": "input_image", "image_url": data_url}]}],
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
    rejected_images: list[int] = Field(default_factory=list)
    reason: str = Field(min_length=10, max_length=300)


def group_product_images(client: OpenAI, data_urls: list[str]) -> BatchScreeningResult:
    """Group accepted images by the physical product they represent."""
    content: list[dict[str, str]] = [{"type": "input_text", "text": """Compare these numbered fashion-product images.
Group images together when they show the same physical product from different angles, in different poses, or in different versions of the same photography.
Treat different garments, different shoe models, or clearly different colours/styles as different products. Do not group merely similar-looking products.
Every image number must appear in exactly one group. Return the number of unique products, the image numbers in each group, and a short reason based on visible evidence."""}]
    for number, data_url in enumerate(data_urls, start=1):
        content.append({"type": "input_text", "text": f"Image {number}:"})
        content.append({"type": "input_image", "image_url": data_url})
    response = client.responses.parse(model="gpt-4o-mini", input=[{"role": "user", "content": content}], text_format=BatchScreeningResult)
    if response.output_parsed is None:
        raise ValueError("batch grouping returned no decision")
    result = response.output_parsed
    all_numbers = [number for group in result.groups for number in group.image_numbers]
    expected = list(range(1, len(data_urls) + 1))
    if sorted(all_numbers) != expected or len(set(all_numbers)) != len(all_numbers):
        raise ValueError("batch grouping did not assign every image exactly once")
    if result.unique_product_count != len(result.groups):
        raise ValueError("batch grouping count does not match its groups")
    return result


def analyze_product_images(image_bytes_list: list[bytes], *, api_key: str | None = None, model: str = "gpt-4o-mini", run_safety_check: bool = True) -> BatchAnalysisResult:
    """Screen a batch and report how many unique fashion products it contains."""
    if not image_bytes_list:
        raise ValueError("at least one image is required")
    images = [prescreen_image(image_bytes) for image_bytes in image_bytes_list]
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    data_urls = [_data_url(image) for image in images]
    rejected: list[int] = []
    for number, data_url in enumerate(data_urls, start=1):
        if run_safety_check:
            moderation = client.moderations.create(model="omni-moderation-latest", input=[{"type": "image_url", "image_url": {"url": data_url}}])
            if moderation.results[0].flagged:
                rejected.append(number)
                continue
        screening = screen_product_image(client, data_url)
        if not screening.passed or screening.item_count != 1 or not screening.primary_item_clear:
            rejected.append(number)
    if rejected:
        return BatchAnalysisResult(passed=False, unique_product_count=0, rejected_images=rejected, reason=f"Images {', '.join(map(str, rejected))} did not each contain exactly one clearly identifiable fashion product.")
    grouping = group_product_images(client, data_urls)
    products = []
    for group in grouping.groups:
        representative = image_bytes_list[group.image_numbers[0] - 1]
        analysis = analyze_product_image(representative, api_key=api_key, model=model, run_safety_check=False, screen_already=True)
        products.append(IdentifiedProduct(product_number=group.product_number, image_numbers=group.image_numbers, grouping_reason=group.reason, analysis=analysis))
    return BatchAnalysisResult(passed=True, unique_product_count=len(products), products=products, reason="All images were grouped and each unique product was analysed.")


def analyze_product_image(image_bytes: bytes, *, api_key: str | None = None, model: str = "gpt-4o-mini", run_safety_check: bool = True, screen_already: bool = False) -> ProductAnalysis:
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

    categorization = categorize_product_image(client, data_url)
    instructions = f"""Analyse this approved wearable fashion product photograph for an ecommerce catalogue.
The separate categorization step identified the product as category '{categorization.category}' and type '{categorization.product_type}'. Use those values unless the image clearly disproves them.

Return only the requested structured fields.
- Use the category and product type supplied by the categorization step.
- Make product_type highly specific, for example '3/4 length dark green leather jacket with a belted waist'.
- Describe colours specifically, including the dominant colour and important secondary colours.
- Name only materials visible or strongly supported by the image. Say 'appears to be' when uncertain.
- List every visible commercial feature: pattern, pockets, zips, buttons, seams, straps, laces, sole, collar, cuffs, hardware, and so on.
- Write a factual 30–40 word description. Do not invent brand, size, price, or hidden features.
- Confidence must reflect how clearly the image supports the result, from 0 to 1.
"""
    content = [{"type": "input_text", "text": instructions}, {"type": "input_image", "image_url": data_url}]
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.responses.parse(model=model, input=[{"role": "user", "content": content}], text_format=ProductAnalysis)
            if response.output_parsed is None:
                raise ValueError("AI returned no structured product analysis")
            return response.output_parsed
        except ValidationError as exc:
            last_error = exc
            content[0]["text"] = instructions + "\nYour previous answer failed validation. The description must contain exactly 35 space-separated words. Write the description first, count every word, then return it."
    raise ValueError("AI returned product details that did not meet the required format") from last_error
