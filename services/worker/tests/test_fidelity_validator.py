import base64
import io
from types import SimpleNamespace

import pytest
from PIL import Image
from PIL import ImageDraw

from productframe_api.generation_prompts import GenerationPrompt, ReferenceImage
from productframe_worker.fidelity_validator import (
    FidelityAssessment,
    OpenAIProductFidelityValidator,
    ProductFidelityError,
    finish_generated_image,
)
from productframe_worker.image_provider import GeneratedImage


class Body:
    def __init__(self, value): self.value = value
    def read(self): return self.value
    def close(self): pass


def png_bytes(colour="navy"):
    output = io.BytesIO()
    Image.new("RGB", (32, 32), colour).save(output, format="PNG")
    return output.getvalue()


def prompt():
    return GenerationPrompt(
        prompt="preserve product", negative_prompt="do not redraw", aspect_ratio="1:1",
        template_id="template", template_version=1,
        reference_images=(ReferenceImage(role="product_reference", object_key="source.png"),),
    )


def validator_for(assessment):
    class Responses:
        def __init__(self): self.kwargs = None
        def parse(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(output_parsed=assessment)
    client = SimpleNamespace(responses=Responses())
    objects = SimpleNamespace(get_object=lambda **kwargs: {"Body": Body(png_bytes()), "ContentType": "image/png"})
    return OpenAIProductFidelityValidator(client=client, object_client=objects), client


def generated():
    return GeneratedImage(content=png_bytes(), content_type="image/png", filename="output.png", provider="test")


def test_final_finishing_preserves_geometry_alpha_and_identity_metadata():
    source = Image.new("RGBA", (64, 48), (120, 105, 115, 180))
    ImageDraw.Draw(source).rectangle((12, 10, 50, 38), fill=(135, 45, 85, 180))
    encoded = io.BytesIO()
    source.save(encoded, format="PNG")
    generated_image = GeneratedImage(
        content=encoded.getvalue(), content_type="image/png", filename="output.png",
        provider="test", request_id="request-1",
    )

    result = finish_generated_image(generated_image)
    finished = Image.open(io.BytesIO(result.content))

    assert finished.size == source.size
    assert finished.getchannel("A").tobytes() == source.getchannel("A").tobytes()
    assert result.filename == generated_image.filename
    assert result.provider == generated_image.provider
    assert result.request_id == generated_image.request_id
    assert result.content != generated_image.content


def test_validator_passes_same_sellable_product_and_sends_both_images():
    validator, client = validator_for(FidelityAssessment(
        same_sellable_product=True, artwork_preserved=True, construction_preserved=True,
        colour_preserved=True, score=0.96, reasons=[],
    ))

    result = validator.validate(prompt(), generated())

    assert result.score == 0.96
    images = [part for part in client.responses.kwargs["input"][0]["content"] if part["type"] == "input_image"]
    assert len(images) == 2
    assert all(base64.b64decode(item["image_url"].split(",", 1)[1]) for item in images)


def test_validator_rejects_redrawn_artwork():
    validator, _ = validator_for(FidelityAssessment(
        same_sellable_product=False, artwork_preserved=False, construction_preserved=True,
        colour_preserved=True, score=0.42, reasons=["The illustration was redrawn."],
    ))

    with pytest.raises(ProductFidelityError, match="illustration was redrawn"):
        validator.validate(prompt(), generated())


def test_restore_transfers_only_source_artwork_mask_and_keeps_surrounding_pixels():
    fabric = (15, 55, 65)
    source = Image.new("RGB", (100, 100), fabric)
    ImageDraw.Draw(source).rectangle((30, 30, 59, 59), fill=(230, 95, 45))
    source_bytes = io.BytesIO()
    source.save(source_bytes, format="PNG")
    target = Image.new("RGB", (100, 100), "white")
    ImageDraw.Draw(target).rectangle((10, 10, 89, 89), fill=fabric)
    target_bytes = io.BytesIO()
    target.save(target_bytes, format="PNG")

    objects = SimpleNamespace(get_object=lambda **kwargs: {
        "Body": Body(source_bytes.getvalue()), "ContentType": "image/png",
    })
    validator = OpenAIProductFidelityValidator(client=SimpleNamespace(), object_client=objects)
    request = GenerationPrompt(
        prompt="preserve", negative_prompt="do not redraw", aspect_ratio="1:1",
        template_id="ecommerce-tops-front-view", template_version=1,
        reference_images=(ReferenceImage(role="product_reference", object_key="source.png"),),
        artwork_regions=({
            "artwork_type": "illustration", "description": "orange rectangular test artwork",
            "source_bounds": [0.3, 0.3, 0.3, 0.3],
            "garment_relative_bounds": [0.25, 0.25, 0.375, 0.375],
            "visible_fraction": 1.0, "extraction_confidence": 0.98,
        },),
        artwork_visibility="full", artwork_surface_mode="flat",
    )
    generated_image = GeneratedImage(
        content=target_bytes.getvalue(), content_type="image/png",
        filename="output.png", provider="test",
    )

    restored = Image.open(io.BytesIO(validator.restore(request, generated_image).content)).convert("RGB")

    assert restored.getpixel((42, 42))[0] > 180
    assert restored.getpixel((20, 20)) == fabric
    assert restored.getpixel((5, 5)) == (255, 255, 255)


def test_restore_fails_closed_when_artwork_extraction_is_uncertain():
    validator, _ = validator_for(FidelityAssessment(
        same_sellable_product=True, artwork_preserved=True, construction_preserved=True,
        colour_preserved=True, score=0.95, reasons=[],
    ))
    request = GenerationPrompt(
        prompt="preserve", negative_prompt="do not redraw", aspect_ratio="1:1",
        template_id="ecommerce-tops-front-view", template_version=1,
        reference_images=(ReferenceImage(role="product_reference", object_key="source.png"),),
        artwork_regions=({
            "source_bounds": [0.2, 0.2, 0.4, 0.4],
            "garment_relative_bounds": [0.2, 0.2, 0.4, 0.4],
            "extraction_confidence": 0.4,
        },), artwork_visibility="full", artwork_surface_mode="flat",
    )

    with pytest.raises(ProductFidelityError, match="confidence is too low"):
        validator.restore(request, generated())
