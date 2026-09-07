import pytest

from productframe_api.generation_prompts import (
    GenerationRequest,
    ProductContext,
    ReferenceImage,
    build_generation_prompt,
)


@pytest.fixture
def tops_request() -> GenerationRequest:
    return GenerationRequest(
        template_id="ecommerce-tops-front-view",
        channel="ecommerce",
        product=ProductContext(
            name="Blue short-sleeve top",
            category="tops",
            product_type="Short-sleeve crew-neck top",
            colours="Muted blue",
            materials="Not clearly visible",
            features=("Short sleeves", "Round neckline", "Plain blue colour"),
            description="A muted blue short-sleeve top with a round neckline.",
        ),
        product_reference_images=(
            ReferenceImage(
                role="product_reference",
                object_key="workspaces/demo/products/product-1/source.webp",
                asset_id="source-1",
            ),
        ),
    )


def test_prompt_combines_product_and_template_references(tops_request):
    result = build_generation_prompt(tops_request)

    assert "Blue short-sleeve top" in result.prompt
    assert "Muted blue" in result.prompt
    assert "straight-on ecommerce front view" in result.prompt
    assert "product_reference" == result.reference_images[0].role
    assert result.reference_images[0].asset_id == "source-1"
    assert len(result.reference_images) == 1
    assert result.reference_images[0].role == "product_reference"
    assert result.aspect_ratio == "1:1"
    assert result.template_id == "ecommerce-tops-front-view"
    assert "watermarks" in result.negative_prompt


def test_prompt_requires_product_reference(tops_request):
    request = GenerationRequest(
        template_id=tops_request.template_id,
        channel=tops_request.channel,
        product=tops_request.product,
        product_reference_images=(),
    )

    with pytest.raises(ValueError, match="reference image"):
        build_generation_prompt(request)


def test_tops_prompt_locks_non_text_artwork_identity(tops_request):
    result = build_generation_prompt(tops_request)

    assert "immutable product identity" in result.prompt
    assert "component count, geometry, topology" in result.prompt
    assert "identifying an animal or object does not permit drawing a different instance" in result.prompt
    assert "graphic geometry" in result.negative_prompt


def test_prompt_carries_artwork_geometry_and_template_policy(tops_request):
    product = ProductContext(
        name=tops_request.product.name, category="tops",
        product_type=tops_request.product.product_type, colours=tops_request.product.colours,
        materials=tops_request.product.materials, features=("Printed illustration",),
        description=tops_request.product.description,
        global_details={"branding": {"artwork_regions": [{
            "artwork_type": "illustration", "description": "Detailed printed illustration",
            "source_bounds": [0.2, 0.3, 0.4, 0.35],
            "garment_relative_bounds": [0.2, 0.25, 0.5, 0.4],
            "visible_fraction": 1.0, "extraction_confidence": 0.95,
        }]}},
    )
    request = GenerationRequest(
        template_id=tops_request.template_id, channel="ecommerce", product=product,
        product_reference_images=tops_request.product_reference_images,
    )

    result = build_generation_prompt(request)

    assert len(result.artwork_regions) == 1
    assert result.artwork_visibility == "full"
    assert result.artwork_surface_mode == "flat"


def test_prompt_rejects_wrong_category(tops_request):
    product = ProductContext(
        name=tops_request.product.name,
        category="footwear",
        product_type=tops_request.product.product_type,
        colours=tops_request.product.colours,
        materials=tops_request.product.materials,
        features=tops_request.product.features,
        description=tops_request.product.description,
    )
    request = GenerationRequest(
        template_id=tops_request.template_id,
        channel=tops_request.channel,
        product=product,
        product_reference_images=tops_request.product_reference_images,
    )

    with pytest.raises(ValueError, match="not available"):
        build_generation_prompt(request)
