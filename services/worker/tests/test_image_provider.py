from productframe_api.generation_prompts import (
    GenerationRequest,
    ProductContext,
    ReferenceImage,
    build_generation_prompt,
)
from productframe_worker.image_provider import FakeImageGenerationProvider


def test_fake_provider_records_request_and_returns_png():
    prompt = build_generation_prompt(
        GenerationRequest(
            template_id="ecommerce-tops-front-view",
            channel="ecommerce",
            product=ProductContext(
                name="Blue short-sleeve top",
                category="tops",
                product_type="Short-sleeve crew-neck top",
                colours="Muted blue",
                materials="Not clearly visible",
                features=("Short sleeves", "Round neckline"),
                description="A muted blue short-sleeve top with a round neckline.",
            ),
            product_reference_images=(
                ReferenceImage(
                    role="product_reference",
                    object_key="products/product-1/source.webp",
                ),
            ),
        )
    )
    provider = FakeImageGenerationProvider()

    result = provider.generate(prompt)

    assert result.provider == "fake"
    assert result.content_type == "image/png"
    assert result.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert result.filename == "ecommerce-tops-front-view.png"
    assert provider.requests == [prompt]
