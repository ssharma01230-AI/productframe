import base64
import io
from types import SimpleNamespace

from PIL import Image

from productframe_api.generation_prompts import (
    GenerationRequest,
    ProductContext,
    ReferenceImage,
    build_generation_prompt,
)
from productframe_worker.openai_image_provider import OpenAIImageGenerationProvider


class Body:
    def __init__(self, value): self.value = value
    def read(self): return self.value
    def close(self): pass


def test_openai_image_provider_sends_both_references(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    valid_image = io.BytesIO()
    Image.new("RGB", (32, 32), "navy").save(valid_image, format="WEBP")
    objects = {
        "product.webp": {"Body": Body(valid_image.getvalue()), "ContentType": "image/webp"},
        "templates/ecommerce/tops/front-view/reference.webp": {"Body": Body(valid_image.getvalue()), "ContentType": "image/webp"},
    }

    class ObjectClient:
        def get_object(self, *, Bucket, Key): return objects[Key]

    class Images:
        def __init__(self): self.kwargs = None
        def edit(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(b"output").decode())])

    class Client:
        def __init__(self): self.images = Images()

    client = Client()
    provider = OpenAIImageGenerationProvider(client=client, object_client=ObjectClient())
    request = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-tops-front-view", channel="ecommerce",
        product=ProductContext(
            name="Blue top", category="tops", product_type="Short-sleeve top",
            colours="Muted blue", materials="Unknown", features=("Short sleeves",),
            description="A muted blue short-sleeve top.",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="product.webp"),),
    ))

    result = provider.generate(request)

    assert result.content == b"output"
    assert result.provider == "gpt-image-1"
    assert client.images.kwargs["model"] == "gpt-image-1"
    assert len(client.images.kwargs["image"]) == 1
    assert "white background" in client.images.kwargs["prompt"]


def test_openai_provider_normalizes_reference_orientation(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    source = Image.new("RGB", (40, 80), "navy")
    exif = Image.Exif()
    exif[274] = 6
    encoded_source = io.BytesIO()
    source.save(encoded_source, format="JPEG", exif=exif)

    class ObjectClient:
        def get_object(self, *, Bucket, Key):
            return {"Body": Body(encoded_source.getvalue()), "ContentType": "image/jpeg"}

    class Images:
        def __init__(self): self.kwargs = None
        def edit(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(b"output").decode())])

    client = SimpleNamespace(images=Images())
    provider = OpenAIImageGenerationProvider(client=client, object_client=ObjectClient())
    request = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-tops-front-view", channel="ecommerce",
        product=ProductContext(
            name="Graphic top", category="tops", product_type="Graphic t-shirt",
            colours="Navy", materials="Cotton", features=("Printed artwork",),
            description="A navy graphic t-shirt with a prominent printed illustration.",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="source.jpg"),),
    ))

    provider.generate(request)

    _, sent, sent_type = client.images.kwargs["image"][0]
    with Image.open(io.BytesIO(sent)) as normalized:
        assert normalized.size == (80, 40)
        assert normalized.getexif().get(274) is None
    assert sent_type == "image/jpeg"
