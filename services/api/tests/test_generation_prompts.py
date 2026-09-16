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


def test_tshirt_family_prompt_uses_structured_sections_and_template_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-tops-t-shirts-casual-tops-05", channel="ecommerce",
        product=ProductContext(
            name="Graphic T-shirt", category="tops", product_type="Graphic tee",
            colours="Black", materials="Cotton jersey", features=("Short sleeves",),
            description="A black graphic T-shirt.",
            category_details={"family": "t-shirts-casual-tops", "subtype": "graphic tee"},
            presentation="unisex",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="shirt.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/reference.png"),),
    ))
    assert [image.role for image in result.reference_images] == ["product_reference", "template_reference"]
    assert "TEMPLATE REFERENCE" in result.prompt
    assert "Replace the template garment completely" in result.prompt
    assert "PRESENTATION MODE" in result.prompt
    assert "OUTPUT DETAILS" in result.prompt
    assert result.prompt.index("PRODUCT") < result.prompt.index("PRESENTATION MODE") < result.prompt.index("OUTPUT DETAILS") < result.prompt.index("NEGATIVE PROMPTS")


def test_skirts_prompt_uses_structured_sections_and_template_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-bottoms-skirts-05", channel="ecommerce",
        product=ProductContext(
            name="Black pleated skirt", category="bottoms", product_type="Skirt",
            colours="Black", materials="Woven fabric", features=("Pleats",),
            description="A black pleated skirt with a flared silhouette.",
            category_details={"family": "skirts", "subtype": "skirt"},
            presentation="unisex",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="skirt.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/skirt.png"),),
    ))
    assert [image.role for image in result.reference_images] == ["product_reference", "template_reference"]
    assert "TEMPLATE REFERENCE" in result.prompt
    assert "Replace the template garment completely" in result.prompt
    assert "OUTPUT DETAILS" in result.prompt
    assert "Slight front three-quarter" in result.prompt
    assert "#C8C1B6" in result.prompt


def test_leggings_prompt_uses_structured_sections_and_template_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-bottoms-leggings-04", channel="ecommerce",
        product=ProductContext(
            name="Cream leggings", category="bottoms", product_type="Leggings",
            colours="Cream", materials="Stretch jersey", features=("High-rise waistband",),
            description="Cream fitted leggings with a high-rise waistband.",
            category_details={"family": "leggings", "subtype": "leggings"},
            presentation="unisex",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="leggings.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/leggings.png"),),
    ))
    assert [image.role for image in result.reference_images] == ["product_reference", "template_reference"]
    assert "TEMPLATE REFERENCE" in result.prompt
    assert "Replace the template garment completely" in result.prompt
    assert "OUTPUT DETAILS" in result.prompt
    assert "Front three-quarter" in result.prompt
    assert "#C8C1B6" in result.prompt


def test_joggers_prompt_uses_structured_sections_and_template_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-bottoms-joggers-06", channel="ecommerce",
        product=ProductContext(
            name="Cream joggers", category="bottoms", product_type="Joggers",
            colours="Cream", materials="Cotton fleece", features=("Drawcord", "Cuffed hems"),
            description="Cream joggers with a drawcord and cuffed hems.",
            category_details={"family": "casual_bottoms", "subtype": "joggers"},
            presentation="unisex",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="joggers.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/joggers.png"),),
    ))
    assert [image.role for image in result.reference_images] == ["product_reference", "template_reference"]
    assert "TEMPLATE REFERENCE" in result.prompt
    assert "Replace the template garment completely" in result.prompt
    assert "OUTPUT DETAILS" in result.prompt
    assert "Front three-quarter" in result.prompt
    assert "#C8C1B6" in result.prompt


def test_shorts_prompt_uses_structured_sections_and_template_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-bottoms-shorts-03", channel="ecommerce",
        product=ProductContext(
            name="Navy cotton shorts", category="bottoms", product_type="Shorts",
            colours="Navy", materials="Cotton", features=("Drawcord", "Side pockets"),
            description="Navy cotton shorts with a drawcord and side pockets.",
            category_details={"family": "shorts", "subtype": "shorts"},
            presentation="unisex",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="shorts.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/shorts.png"),),
    ))
    assert [image.role for image in result.reference_images] == ["product_reference", "template_reference"]
    assert "TEMPLATE REFERENCE" in result.prompt
    assert "Replace the template garment completely" in result.prompt
    assert "OUTPUT DETAILS" in result.prompt
    assert "Front three-quarter" in result.prompt
    assert "let the actual drawstrings fall naturally with gravity" in result.prompt
    assert "#C8C1B6" in result.prompt


def test_structured_bottoms_prompt_uses_structured_sections_and_template_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-bottoms-side-angle-product", channel="ecommerce",
        product=ProductContext(
            name="Black tailored trousers", category="bottoms", product_type="Trousers",
            colours="Black", materials="Wool blend", features=("Straight leg",),
            description="Black tailored trousers with a straight leg.",
            category_details={"family": "structured_bottoms", "subtype": "trousers"},
            presentation="unisex",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="trousers.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/bottoms.png"),),
    ))
    assert [image.role for image in result.reference_images] == ["product_reference", "template_reference"]
    assert "TEMPLATE REFERENCE" in result.prompt
    assert "Replace the template garment completely" in result.prompt
    assert "Use one adult model" in result.prompt
    assert "OUTPUT DETAILS" in result.prompt
    assert "#C8C1B6" in result.prompt


def test_hoodie_family_prompt_uses_structured_sections_and_template_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-tops-hoodies-09", channel="ecommerce",
        product=ProductContext(
            name="Black hoodie", category="tops", product_type="Pullover hoodie",
            colours="Black", materials="Cotton fleece", features=("Hood", "Long sleeves"),
            description="A black pullover hoodie.",
            category_details={"family": "hoodies", "subtype": "pullover hoodie"},
            presentation="unisex",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="hoodie.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/hoodie.png"),),
    ))
    assert [image.role for image in result.reference_images] == ["product_reference", "template_reference"]
    assert "TEMPLATE REFERENCE" in result.prompt
    assert "Replace the template garment completely" in result.prompt
    assert "OUTPUT DETAILS" in result.prompt
    assert "Both hands holding hood edges" in result.prompt
    assert "#C8C1B6" in result.prompt


def test_knitwear_family_prompt_uses_structured_sections_and_template_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-tops-knitwear-04", channel="ecommerce",
        product=ProductContext(
            name="Navy knit jumper", category="tops", product_type="Knitwear",
            colours="Navy", materials="Wool blend knit", features=("Long sleeves",),
            description="A navy knitted jumper.",
            category_details={"family": "knitwear", "subtype": "jumper"},
            presentation="unisex",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="knitwear.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/knitwear.png"),),
    ))
    assert [image.role for image in result.reference_images] == ["product_reference", "template_reference"]
    assert "TEMPLATE REFERENCE" in result.prompt
    assert "Replace the template garment completely" in result.prompt
    assert "Use one adult model" in result.prompt
    assert "OUTPUT DETAILS" in result.prompt
    assert "#C8C1B6" in result.prompt


def test_sleeveless_family_prompt_uses_structured_sections_and_template_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-tops-sleeveless-tops-04", channel="ecommerce",
        product=ProductContext(
            name="Black sleeveless top", category="tops", product_type="Sleeveless top",
            colours="Black", materials="Cotton jersey", features=("Sleeveless cut",),
            description="A black sleeveless top.",
            category_details={"family": "sleeveless-tops", "subtype": "tank top"},
            presentation="unisex",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="top.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/sleeveless.png"),),
    ))
    assert [image.role for image in result.reference_images] == ["product_reference", "template_reference"]
    assert "TEMPLATE REFERENCE" in result.prompt
    assert "Replace the template garment completely" in result.prompt
    assert "visible headless mannequin" in result.prompt
    assert "OUTPUT DETAILS" in result.prompt
    assert "#C8C1B6" in result.prompt


def test_shirts_family_prompt_uses_structured_presentation_sections():
    request = GenerationRequest(
        template_id="ecommerce-tops-shirts-08", channel="ecommerce",
        product=ProductContext(
            name="White shirt", category="tops", product_type="Button-up shirt",
            colours="White", materials="Cotton", features=("Pointed collar", "Long sleeves"),
            description="A white cotton button-up shirt.",
            category_details={"family": "shirts", "subtype": "shirt"},
            presentation="unisex",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="shirt.webp"),),
    )
    result = build_generation_prompt(request)
    assert "PRESENTATION MODE" in result.prompt
    assert "completely invisible mannequin" in result.prompt
    assert "OUTPUT DETAILS" in result.prompt
    assert "#C8C1B6" in result.prompt
    assert "MODEL AND MANNEQUIN PRESENTATION" not in result.prompt
    assert "PROMPT FORMAT RULES" not in result.prompt
    assert "headless mannequin torso" in result.negative_prompt
    assert result.prompt.index("PRODUCT") < result.prompt.index("PRODUCT FIDELITY PRESERVATION") < result.prompt.index("PRESENTATION MODE") < result.prompt.index("OUTPUT DETAILS") < result.prompt.index("NEGATIVE PROMPTS")


def test_prompt_strengthens_material_fidelity_and_adaptive_styling():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-bottoms-skirts-05", channel="ecommerce",
        product=ProductContext(
            name="Light blue and white skirt", category="bottoms", product_type="Skirt",
            colours="Light blue and white", materials="Woven fabric", features=("Pleats",),
            description="A light blue and white skirt.",
            category_details={"family": "skirts", "subtype": "pleated_mini_skirt"},
            presentation="unisex",
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="skirt.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/skirt.png"),),
    ))
    assert "generic AI-generated texture" in result.prompt
    assert "Every clearly visible construction detail" in result.prompt
    assert "neckline stitching" in result.prompt
    assert "adapt their colours and materials" in result.prompt
    assert "medium-light grey lower garment" in result.prompt
    assert "consistent across every model-worn output" in result.prompt
    assert "SECONDARY STYLING OVERRIDE" in result.prompt
    assert "non-authoritative" in result.prompt


def test_heels_prompt_uses_product_and_matching_template_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-footwear-heels-08", channel="ecommerce",
        product=ProductContext(
            name="Black heels", category="footwear", product_type="heels",
            colours="Black", materials="Leather-like upper", features=("High heel",),
            description="Black high heels.",
            category_details={"family": "heels", "subtype": "heels", "toe_shape": "pointed", "sole_type": "high heel"},
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="shoe.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/heels.png"),),
    ))
    assert [image.role for image in result.reference_images] == ["product_reference", "template_reference"]
    assert "Low side view" in result.prompt
    assert "Do not infer numeric heel height" in result.prompt
    assert result.prompt.index("PRODUCT") < result.prompt.index("PRESENTATION MODE") < result.prompt.index("OUTPUT DETAILS") < result.prompt.index("NEGATIVE PROMPTS")


def test_flats_loafers_prompt_uses_product_and_matching_template_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-footwear-flats-loafers-08", channel="ecommerce",
        product=ProductContext(
            name="Black loafers", category="footwear", product_type="Loafers",
            colours="Black", materials="Leather-like upper", features=("Slip-on",),
            description="Black loafers with a low sole.",
            category_details={"family": "flats-loafers", "subtype": "loafers", "toe_shape": "rounded", "sole_type": "low sole"},
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="shoe.webp"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="file:///repo/flats.png"),),
    ))
    assert [image.role for image in result.reference_images] == ["product_reference", "template_reference"]
    assert "PRESENTATION MODE" in result.prompt and "OUTPUT DETAILS" in result.prompt
    assert "Low side view" in result.prompt
    assert "Do not add tassels" in result.prompt
    assert result.prompt.index("PRODUCT") < result.prompt.index("PRESENTATION MODE") < result.prompt.index("OUTPUT DETAILS") < result.prompt.index("NEGATIVE PROMPTS")


@pytest.mark.parametrize(
    ("colours", "expected"),
    [
        ("White", "do not default to white"),
        ("Black", "dark product"),
        ("Red and blue geometric pattern", "restrained mid-neutral"),
        ("", "restrained mid-neutral"),
    ],
)
def test_secondary_styling_is_adaptive_and_deterministic(tops_request, colours, expected):
    request = GenerationRequest(
        template_id="ecommerce-footwear-flats-loafers-07", channel="ecommerce",
        product=ProductContext(
            name="Test product", category="footwear", product_type="loafer", colours=colours,
            materials="Unknown", features=(), description="Test product",
            category_details={"family": "flats-loafers", "subtype": "loafers", "toe_shape": "unknown", "sole_type": "unknown"},
        ),
        product_reference_images=tops_request.product_reference_images,
    )
    first = build_generation_prompt(request).prompt
    second = build_generation_prompt(request).prompt
    assert first == second
    assert expected in first
    assert "consistent across every model-worn output" in first


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
        template_id="ecommerce-bottoms-leggings-05", channel="ecommerce",
        product=product,
        product_reference_images=(ReferenceImage(role="product_reference", object_key="leggings.png"),),
    ))

    assert "BOTTOMS FAMILY RENDERING POLICY" in result.prompt
    assert "Do not assume a fly, belt loops, rigid denim" in result.prompt


def test_selected_presentation_applies_to_models_and_mannequins_across_families(tops_request):
    product = ProductContext(
        name="Navy shorts", category="bottoms", product_type="Shorts",
        colours="Navy", materials="Cotton blend", features=("Elastic waistband",),
        description="Navy casual shorts.", category_details={"family": "shorts"}, presentation="female",
    )
    reference = (ReferenceImage(role="product_reference", object_key="shorts.png"),)
    for template_id, expected_mode in (
        ("ecommerce-bottoms-shorts-02", "completely invisible mannequin"),
        ("ecommerce-bottoms-shorts-05", "one adult model"),
    ):
        result = build_generation_prompt(GenerationRequest(
            template_id=template_id, channel="ecommerce", product=product,
            product_reference_images=reference,
        ))
        assert expected_mode in result.prompt
        assert "OUTPUT DETAILS" in result.prompt
        assert "selected user presentation overrides" not in result.prompt


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
