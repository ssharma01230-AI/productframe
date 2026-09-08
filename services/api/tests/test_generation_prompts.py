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


def test_underwear_prompt_requires_the_lower_body_family_for_boxer_templates():
    product = ProductContext(
        name="Grey boxer briefs", category="underwear",
        product_type="Men's boxer briefs", colours="Grey",
        materials="Stretch jersey", features=("Covered elastic waistband",),
        description="Grey stretch boxer briefs with a covered elastic waistband and close fit.",
        category_details={
            "family": "lower_body_underwear",
            "subtype": "boxers",
            "coverage": "mid-thigh",
            "waist_height": "mid-rise",
            "rise": "standard",
            "elastic_details": "covered elastic",
            "fabric_appearance": "soft stretch jersey",
            "fit_and_silhouette": "close fit",
        },
    )
    request = GenerationRequest(
        template_id="ecommerce-underwear-front-product", channel="ecommerce",
        product=product,
        product_reference_images=(ReferenceImage(role="product_reference", object_key="boxers.png", asset_id="boxers"),),
    )
    result = build_generation_prompt(request)
    assert result.template_id == "ecommerce-underwear-front-product"
    assert "lower_body_underwear" in result.prompt

    product.category_details["family"] = "bra"
    with pytest.raises(ValueError, match="product family"):
        build_generation_prompt(request)


def test_bottoms_prompt_applies_family_policy_without_extra_request():
    product = ProductContext(
        name="Black leggings", category="bottoms",
        product_type="Black high-waisted leggings", colours="Black",
        materials="Stretch jersey", features=("High waistband", "Close fit"),
        description="Black high-waisted stretch leggings with a close-fitting silhouette.",
        category_details={
            "family": "leggings", "subtype": "leggings",
            "waist_height": "high", "waistband_type": "elastic",
            "fly_or_closure": "not applicable", "leg_shape": "close-fitting",
            "leg_width": "close", "garment_length": "ankle length",
            "hem_details": "plain hem", "pocket_details": [],
            "pleats_or_darts": [], "belt_loops": "not applicable",
            "panel_or_seam_details": ["side seams"],
            "fit_and_silhouette": "close-fitting", "visible_uncertainties": [],
        },
    )
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-bottoms-front-view", channel="ecommerce",
        product=product,
        product_reference_images=(ReferenceImage(role="product_reference", object_key="leggings.png"),),
    ))

    assert "BOTTOMS FAMILY RENDERING POLICY" in result.prompt
    assert "Do not assume a fly, belt loops, rigid denim" in result.prompt


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
