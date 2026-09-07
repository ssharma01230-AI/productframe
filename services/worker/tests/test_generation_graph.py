from productframe_api.generation_prompts import (
    GenerationRequest,
    ProductContext,
    ReferenceImage,
)
from productframe_worker.generation_graph import run_single_generation
from productframe_worker.image_provider import FakeImageGenerationProvider


def test_one_job_graph_builds_prompt_and_generates_image():
    provider = FakeImageGenerationProvider()
    request = GenerationRequest(
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

    result = run_single_generation(request, provider=provider)

    assert result["status"] == "completed"
    assert result["prompt"].template_id == "ecommerce-tops-front-view"
    assert result["generated_image"].provider == "fake"
    assert len(provider.requests) == 1
