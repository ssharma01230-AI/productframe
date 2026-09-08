import base64
import httpx

from productframe_api.generation_prompts import (
    GenerationRequest,
    ProductContext,
    ReferenceImage,
    build_generation_prompt,
)
from productframe_worker.gemini_image_provider import GeminiImageGenerationProvider


class Body:
    def __init__(self, value: bytes):
        self.value = value

    def read(self):
        return self.value

    def close(self):
        pass


def test_gemini_provider_sends_product_and_template_references(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    source_bytes = b"product-image"
    objects = {
        "products/source.webp": {"Body": Body(source_bytes), "ContentType": "image/webp"},
    }

    class ObjectClient:
        def get_object(self, *, Bucket, Key):
            return objects[Key]

    response_image = b"generated-image"
    captured = {}

    def handler(request):
        captured["body"] = request.read()
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"inlineData": {
                "mimeType": "image/png",
                "data": base64.b64encode(response_image).decode(),
            }}]}}]
        })

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GeminiImageGenerationProvider(client=client, object_client=ObjectClient())
    prompt = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-tops-front-view",
        channel="ecommerce",
        product=ProductContext(
            name="Blue top", category="tops", product_type="Short-sleeve top",
            colours="Muted blue", materials="Unknown", features=("Short sleeves",),
            description="A muted blue short-sleeve top.",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="products/source.webp"),),
    ))

    result = provider.generate(prompt)

    assert result.content == response_image
    assert result.provider == "gemini-3.1-flash-lite-image"
    assert result.content_type == "image/png"
    body = captured["body"].decode()
    assert "product reference" in body
    assert "template reference" not in body
    assert base64.b64encode(source_bytes).decode() in body
    provider.close()
