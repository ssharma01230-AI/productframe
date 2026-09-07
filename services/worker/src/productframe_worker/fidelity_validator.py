"""Reference-to-output identity validation for generated product images."""
from __future__ import annotations

import base64
import io
import os
from typing import Any

import boto3
from openai import OpenAI
from pydantic import BaseModel, Field
from PIL import Image, ImageEnhance, ImageFilter

from productframe_api.config import get_settings
from productframe_api.generation_prompts import GenerationPrompt
from productframe_api.image_processing import normalize_image_orientation

from .image_provider import GeneratedImage


class FidelityAssessment(BaseModel):
    same_sellable_product: bool
    artwork_preserved: bool
    construction_preserved: bool
    colour_preserved: bool
    score: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list, max_length=8)


class ProductFidelityError(RuntimeError):
    pass


def finish_generated_image(image: GeneratedImage) -> GeneratedImage:
    """Apply conservative photographic finishing without changing image geometry."""
    source = Image.open(io.BytesIO(image.content))
    source_format = source.format or "PNG"
    alpha = source.getchannel("A") if "A" in source.getbands() else None
    finished = source.convert("RGB")
    finished = ImageEnhance.Contrast(finished).enhance(1.055)
    finished = ImageEnhance.Color(finished).enhance(1.075)
    finished = finished.filter(ImageFilter.UnsharpMask(radius=1.15, percent=72, threshold=4))

    save_options: dict[str, Any] = {}
    if source_format == "PNG":
        if alpha is not None:
            finished.putalpha(alpha)
        save_options["optimize"] = True
    elif source_format in {"JPEG", "JPG"}:
        source_format = "JPEG"
        save_options.update(quality=95, subsampling=0, optimize=True)
    elif source_format == "WEBP":
        if alpha is not None:
            finished.putalpha(alpha)
        save_options.update(quality=95, method=6)
    else:
        source_format = "PNG"
        if alpha is not None:
            finished.putalpha(alpha)
        save_options["optimize"] = True

    output = io.BytesIO()
    finished.save(output, format=source_format, **save_options)
    content_type = {
        "JPEG": "image/jpeg",
        "WEBP": "image/webp",
        "PNG": "image/png",
    }[source_format]
    return GeneratedImage(
        content=output.getvalue(),
        content_type=content_type,
        filename=image.filename,
        provider=image.provider,
        request_id=image.request_id,
    )


class OpenAIProductFidelityValidator:
    """Reject outputs that depict a materially different sellable product."""

    def __init__(self, *, client: Any | None = None, object_client: Any | None = None):
        settings = get_settings()
        self.model = os.environ.get("OPENAI_FIDELITY_MODEL", "gpt-4.1-mini")
        self._owns_client = client is None
        self.client = client or OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=90)
        self.bucket = settings.minio_bucket
        self.object_client = object_client or boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name="us-east-1",
        )

    def close(self) -> None:
        if self._owns_client and hasattr(self.client, "close"):
            self.client.close()

    @staticmethod
    def _data_url(content: bytes, content_type: str) -> str:
        return f"data:{content_type};base64,{base64.b64encode(content).decode('ascii')}"

    def _reference_url(self, object_key: str, rotation_degrees: int = 0) -> str:
        stored = self.object_client.get_object(Bucket=self.bucket, Key=object_key)
        body = stored["Body"]
        try:
            normalized = normalize_image_orientation(body.read(), rotation_degrees=rotation_degrees)
        finally:
            body.close()
        return self._data_url(normalized.content, normalized.content_type)

    def _reference_bytes(self, object_key: str, rotation_degrees: int = 0) -> bytes:
        stored = self.object_client.get_object(Bucket=self.bucket, Key=object_key)
        body = stored["Body"]
        try:
            return normalize_image_orientation(body.read(), rotation_degrees=rotation_degrees).content
        finally:
            body.close()

    @staticmethod
    def _pixel_bounds(bounds: list[float], width: int, height: int) -> tuple[int, int, int, int]:
        x, y, box_width, box_height = bounds
        left = max(0, min(width - 1, round(x * width)))
        top = max(0, min(height - 1, round(y * height)))
        right = max(left + 1, min(width, round((x + box_width) * width)))
        bottom = max(top + 1, min(height, round((y + box_height) * height)))
        return left, top, right, bottom

    @staticmethod
    def _median(values: list[int]) -> int:
        ordered = sorted(values)
        return ordered[len(ordered) // 2]

    @staticmethod
    def _pixels(image: Image.Image):
        flattened = getattr(image, "get_flattened_data", None)
        return flattened() if callable(flattened) else image.getdata()

    @classmethod
    def _surrounding_colour(cls, image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
        left, top, right, bottom = box
        margin = max(3, round(min(image.size) * 0.025))
        outer = (
            max(0, left - margin), max(0, top - margin),
            min(image.width, right + margin), min(image.height, bottom + margin),
        )
        pixels = image.load()
        samples: list[tuple[int, int, int]] = []
        for y in range(outer[1], outer[3]):
            for x in range(outer[0], outer[2]):
                if left <= x < right and top <= y < bottom:
                    continue
                samples.append(pixels[x, y][:3])
        if not samples:
            crop = image.crop(box)
            samples = list(cls._pixels(crop))
        return tuple(cls._median([pixel[channel] for pixel in samples]) for channel in range(3))

    @staticmethod
    def _colour_distance(pixel: tuple[int, ...], colour: tuple[int, int, int]) -> float:
        return sum((pixel[index] - colour[index]) ** 2 for index in range(3)) ** 0.5

    @classmethod
    def _artwork_layer(
        cls,
        source: Image.Image,
        box: tuple[int, int, int, int],
        fabric_colour: tuple[int, int, int],
    ) -> Image.Image:
        crop = source.crop(box).convert("RGBA")
        alpha = Image.new("L", crop.size)
        alpha.putdata([
            max(0, min(255, round((cls._colour_distance(pixel, fabric_colour) - 12) * 7)))
            for pixel in cls._pixels(crop)
        ])
        alpha_pixels = alpha.load()
        visited: set[tuple[int, int]] = set()
        stack = [
            (x, y)
            for x in range(crop.width)
            for y in (0, crop.height - 1)
            if alpha_pixels[x, y] > 24
        ] + [
            (x, y)
            for y in range(crop.height)
            for x in (0, crop.width - 1)
            if alpha_pixels[x, y] > 24
        ]
        while stack:
            point = stack.pop()
            if point in visited:
                continue
            visited.add(point)
            x, y = point
            if alpha_pixels[x, y] <= 24:
                continue
            alpha_pixels[x, y] = 0
            for neighbour in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= neighbour[0] < crop.width and 0 <= neighbour[1] < crop.height and neighbour not in visited:
                    stack.append(neighbour)
        coverage = sum(1 for value in cls._pixels(alpha) if value > 24) / max(1, crop.width * crop.height)
        if coverage < 0.01 or coverage > 0.88:
            raise ProductFidelityError("Artwork mask is not sufficiently isolated from the surrounding photograph")
        alpha = alpha.filter(ImageFilter.GaussianBlur(0.65))
        crop.putalpha(alpha)
        return crop

    @classmethod
    def _garment_bounds(cls, image: Image.Image, fabric_colour: tuple[int, int, int]) -> tuple[int, int, int, int] | None:
        rgb = image.convert("RGB")
        coordinates: list[tuple[int, int]] = []
        for y in range(rgb.height):
            for x in range(rgb.width):
                pixel = rgb.getpixel((x, y))
                if cls._colour_distance(pixel, fabric_colour) <= 78:
                    coordinates.append((x, y))
        minimum = max(100, round(rgb.width * rgb.height * 0.015))
        if len(coordinates) < minimum:
            return None
        xs, ys = zip(*coordinates)
        return min(xs), min(ys), max(xs) + 1, max(ys) + 1

    @staticmethod
    def _destination_box(
        garment_box: tuple[int, int, int, int],
        relative_bounds: list[float],
        image_size: tuple[int, int],
    ) -> tuple[int, int, int, int]:
        garment_left, garment_top, garment_right, garment_bottom = garment_box
        garment_width = garment_right - garment_left
        garment_height = garment_bottom - garment_top
        x, y, width, height = relative_bounds
        left = round(garment_left + x * garment_width)
        top = round(garment_top + y * garment_height)
        right = round(left + width * garment_width)
        bottom = round(top + height * garment_height)
        return (
            max(0, left), max(0, top), min(image_size[0], max(left + 1, right)),
            min(image_size[1], max(top + 1, bottom)),
        )

    @staticmethod
    def _padded_box(box: tuple[int, int, int, int], image_size: tuple[int, int], fraction: float = 0.06) -> tuple[int, int, int, int]:
        left, top, right, bottom = box
        horizontal = max(2, round((right - left) * fraction))
        vertical = max(2, round((bottom - top) * fraction))
        return (
            max(0, left - horizontal), max(0, top - vertical),
            min(image_size[0], right + horizontal), min(image_size[1], bottom + vertical),
        )

    @staticmethod
    def _apply_target_lighting(layer: Image.Image, target: Image.Image, fabric_colour: tuple[int, int, int]) -> Image.Image:
        result = layer.copy()
        source_luminance = max(1.0, sum(fabric_colour) / 3)
        source_pixels = list(OpenAIProductFidelityValidator._pixels(result))
        target_pixels = list(OpenAIProductFidelityValidator._pixels(target.convert("RGB")))
        adjusted = []
        for source_pixel, target_pixel in zip(source_pixels, target_pixels):
            lighting = max(0.65, min(1.35, (sum(target_pixel) / 3) / source_luminance))
            adjusted.append(tuple(max(0, min(255, round(channel * lighting))) for channel in source_pixel[:3]) + (source_pixel[3],))
        result.putdata(adjusted)
        return result

    def restore(self, prompt: GenerationPrompt, image: GeneratedImage) -> GeneratedImage:
        """Restore source artwork inside a tight mask while retaining target fabric lighting."""
        if prompt.artwork_visibility == "none" or not prompt.artwork_regions:
            return image
        if prompt.artwork_visibility == "conditional" and prompt.artwork_surface_mode == "detail":
            return image
        reference = prompt.reference_images[0]
        source = Image.open(io.BytesIO(self._reference_bytes(reference.object_key, prompt.reference_rotation_degrees))).convert("RGB")
        target = Image.open(io.BytesIO(image.content)).convert("RGBA")
        restored = target.copy()
        for region in prompt.artwork_regions:
            confidence = float(region.get("extraction_confidence", 0))
            if confidence < 0.75:
                raise ProductFidelityError("Artwork extraction confidence is too low for faithful restoration")
            source_bounds = region.get("source_bounds")
            relative_bounds = region.get("garment_relative_bounds")
            if not isinstance(source_bounds, list) or not isinstance(relative_bounds, list):
                raise ProductFidelityError("Artwork geometry is unavailable for faithful restoration")
            source_box = self._pixel_bounds(source_bounds, source.width, source.height)
            source_box = self._padded_box(source_box, source.size)
            fabric_colour = self._surrounding_colour(source, source_box)
            garment_box = self._garment_bounds(restored, fabric_colour)
            if garment_box is None:
                raise ProductFidelityError("Generated garment surface could not be located for artwork restoration")
            destination = self._destination_box(garment_box, relative_bounds, restored.size)
            destination = self._padded_box(destination, restored.size)
            layer = self._artwork_layer(source, source_box, fabric_colour)
            layer = layer.resize((destination[2] - destination[0], destination[3] - destination[1]), Image.Resampling.LANCZOS)
            layer = self._apply_target_lighting(layer, restored.crop(destination), fabric_colour)
            restored.alpha_composite(layer, (destination[0], destination[1]))
        output = io.BytesIO()
        restored.convert("RGB").save(output, format="PNG", optimize=True)
        return GeneratedImage(
            content=output.getvalue(), content_type="image/png", filename=image.filename,
            provider=image.provider, request_id=image.request_id,
        )

    def validate(self, prompt: GenerationPrompt, image: GeneratedImage) -> FidelityAssessment:
        content: list[dict[str, Any]] = [{
            "type": "input_text",
            "text": (
                "Compare the product references followed by the generated ecommerce image. "
                "Decide whether a customer would receive the exact same sellable product. "
                "Composition, background, pose and removal of a model may change. Product identity may not. "
                "For tops, any print, illustration, logo, embroidery or appliqué must retain its exact visible "
                "geometry, component count, arrangement, orientation, linework, internal details, colour boundaries, "
                "text, scale, placement and distress. Depicting the same general subject with newly drawn artwork is "
                "a failure. Materially changed neckline, sleeves, seams, silhouette, colour or surface treatment is "
                f"also a failure. This template expects artwork visibility={prompt.artwork_visibility} and "
                f"surface mode={prompt.artwork_surface_mode}; do not require front artwork in a rear view, and "
                "validate only naturally visible portions in partial or conditional views. Set same_sellable_product "
                "true only when all identity-critical visible details match."
            ),
        }]
        for reference in prompt.reference_images:
            content.append({"type": "input_image", "image_url": self._reference_url(reference.object_key, prompt.reference_rotation_degrees), "detail": "high"})
        content.append({"type": "input_image", "image_url": self._data_url(image.content, image.content_type), "detail": "high"})
        response = self.client.responses.parse(
            model=self.model,
            input=[{"role": "user", "content": content}],
            text_format=FidelityAssessment,
        )
        assessment = response.output_parsed
        if assessment is None:
            raise ProductFidelityError("Product fidelity validation returned no result")
        if not assessment.same_sellable_product or assessment.score < 0.85:
            reason = "; ".join(assessment.reasons[:3]) or "generated product identity differs from its references"
            raise ProductFidelityError(f"Generated image failed product fidelity validation: {reason}")
        return assessment
