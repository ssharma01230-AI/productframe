"""Canonical image decoding used at every model boundary."""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError


@dataclass(frozen=True, slots=True)
class NormalizedImage:
    content: bytes
    content_type: str
    width: int
    height: int


def normalize_image_orientation(image_bytes: bytes, *, quality: int = 95, rotation_degrees: int = 0) -> NormalizedImage:
    """Apply EXIF orientation and return model-safe pixels without orientation metadata."""
    if not image_bytes:
        raise ValueError("image is empty")
    try:
        with Image.open(io.BytesIO(image_bytes)) as opened:
            image = ImageOps.exif_transpose(opened)
            if rotation_degrees not in {0, 90, 180, 270}:
                raise ValueError("rotation must be 0, 90, 180, or 270 degrees")
            if rotation_degrees:
                image = image.rotate(-rotation_degrees, expand=True)
            has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
            output = io.BytesIO()
            if has_alpha:
                image.convert("RGBA").save(output, format="PNG", optimize=True)
                content_type = "image/png"
            else:
                image.convert("RGB").save(
                    output,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                    subsampling=0,
                )
                content_type = "image/jpeg"
            return NormalizedImage(
                content=output.getvalue(),
                content_type=content_type,
                width=image.width,
                height=image.height,
            )
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("file is not a readable image") from exc
