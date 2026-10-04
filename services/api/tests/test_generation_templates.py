from pathlib import Path

import pytest

from productframe_api.generation_templates import (
    TOPS_CLEAN_PRODUCT_SHOT,
    TOPS_FRONT_VIEW,
    get_generation_template,
    list_generation_templates,
    validate_generation_template,
)


def test_tops_ecommerce_template_is_registered():
    template = get_generation_template("ecommerce-clean-product-shot")

    assert template == TOPS_CLEAN_PRODUCT_SHOT
    assert template.category == "tops"
    assert template.channel == "ecommerce"
    assert template.version == 1
    assert template.reference_object_key is None
    assert template.prompt_instructions
    assert template.negative_prompt


def test_all_footwear_templates_forbid_multi_image_outputs():
    footwear = [template for template in list_generation_templates() if template.category == "footwear"]
    assert footwear
    for template in footwear:
        negative = template.negative_prompt.lower()
        assert "single-frame photograph only" in negative
        assert "collages" in negative
        assert "multiple views" in negative
    assert "camera angle" in get_generation_template("ecommerce-footwear-sole-view").prompt_instructions
    rear = get_generation_template("ecommerce-footwear-rear-view").prompt_instructions.lower()
    assert "strictly straight-on" in rear
    assert "optical axis perpendicular" in rear
    assert "no outer or inner side profile" in rear


def test_heels_have_reviewed_details_modes_evidence_and_local_benchmarks():
    templates = list_generation_templates(category="footwear", channel="ecommerce", product_family="heels")
    assert [template.name for template in templates] == ["Three-Quarter Product", "Side Profile — Toe Left", "Side Profile — Toe Right", "Front View", "Rear View", "Top View", "Front on Feet", "Side on Feet"]
    assert [template.presentation_mode for template in templates] == ["garment"] * 6 + ["model", "model"]
    assert [template.required_evidence for template in templates] == [("front_view", "side_view"), ("side_view",), ("side_view",), ("front_view", "top_view"), ("rear_view", "sole_or_underside"), ("top_view",), ("front_view",), ("side_view", "rear_view")]
    repo_root = Path(__file__).parents[3]
    assert all(template.output_details and template.reference_object_key and (repo_root / template.reference_object_key).is_file() for template in templates)
    assert "Do not infer numeric heel height" in templates[0].prompt_format_rules[2]


def test_shoes_share_the_canonical_footwear_pack():
    templates = list_generation_templates(category="footwear", channel="ecommerce", product_family="shoes")
    assert len(templates) == 17
    assert all(template.applicable_families == ("shoes",) for template in templates)
    repo_root = Path(__file__).parents[3]
    assert all(template.output_details and template.reference_object_key and (repo_root / template.reference_object_key).is_file() for template in templates)
    assert validate_generation_template("ecommerce-footwear-flats-loafers-01", category="footwear", channel="ecommerce", subtype="flat shoes", product_family="shoes").version == 2


def test_mens_tailoring_suit_jackets_are_comprehensive_and_presentation_specific():
    templates = list_generation_templates(category="tailoring", channel="ecommerce", product_family="suit-jackets")
    assert [template.id for template in templates] == [
        "ecommerce-mens-tailoring-suit-jackets-02",
        "ecommerce-mens-tailoring-suit-jackets-03",
        "ecommerce-mens-tailoring-suit-jackets-04",
        "ecommerce-mens-tailoring-suit-jackets-05",
        "ecommerce-mens-tailoring-suit-jackets-06",
        "ecommerce-mens-tailoring-suit-jackets-07",
        "ecommerce-mens-tailoring-suit-jackets-08",
    ]
    repo_root = Path(__file__).parents[3]
    assert all(template.output_details and len(template.output_details) > 1000 for template in templates)
    assert all(template.reference_object_key and (repo_root / template.reference_object_key).is_file() for template in templates)
    assert all("Evidence and uncertainty:" in template.output_details for template in templates)
    model_templates = templates[:4]
    assert all(template.presentation_mode == "model" for template in model_templates)
    assert all("do not use a mannequin" in template.negative_prompt.lower() for template in model_templates)
    assert all("do not show a human model" not in template.negative_prompt.lower() for template in model_templates)
    product_templates = templates[4:]
    assert all(template.presentation_mode in ("garment", "invisible_mannequin") for template in product_templates)
    assert all("do not show a human model" in template.negative_prompt.lower() for template in product_templates)
    with pytest.raises(ValueError, match="product family"):
        validate_generation_template(
            "ecommerce-mens-tailoring-suit-jackets-02",
            category="tailoring", channel="ecommerce", product_family="waistcoats",
        )


def test_mens_tailoring_waistcoats_have_five_exact_reviewed_contracts():
    templates = list_generation_templates(category="tailoring", channel="ecommerce", product_family="waistcoats")
    assert [template.id for template in templates] == [
        "ecommerce-mens-tailoring-waistcoats-01",
        "ecommerce-mens-tailoring-waistcoats-02",
        "ecommerce-mens-tailoring-waistcoats-03",
        "ecommerce-mens-tailoring-waistcoats-04",
        "ecommerce-mens-tailoring-waistcoats-05",
    ]
    assert [template.presentation_mode for template in templates] == [
        "invisible_mannequin", "model", "model", "model", "garment",
    ]
    assert [template.required_evidence for template in templates] == [
        ("front_view",), ("front_view",), ("front_view", "side_view"),
        ("detail", "front_view"), ("detail", "front_view"),
    ]
    repo_root = Path(__file__).parents[3]
    assert all(template.output_details and len(template.output_details) > 1000 for template in templates)
    assert all("Evidence and uncertainty:" in template.output_details for template in templates)
    assert all(template.reference_object_key and (repo_root / template.reference_object_key).is_file() for template in templates)
    with pytest.raises(ValueError, match="product family"):
        validate_generation_template(
            templates[0].id, category="tailoring", channel="ecommerce", product_family="suit-jackets",
        )


def test_mens_sleepwear_pyjamas_have_six_exact_reviewed_contracts():
    templates = list_generation_templates(category="sleepwear_loungewear", channel="ecommerce", product_family="pyjamas")
    assert [template.id for template in templates] == [
        "ecommerce-sleepwear-pyjamas-01", "ecommerce-sleepwear-pyjamas-02", "ecommerce-sleepwear-pyjamas-03",
        "ecommerce-sleepwear-pyjamas-04", "ecommerce-sleepwear-pyjamas-05", "ecommerce-sleepwear-pyjamas-06",
    ]
    repo_root = Path(__file__).parents[3]
    assert all(template.reference_object_key and (repo_root / template.reference_object_key).is_file() for template in templates)
    assert all(template.output_details and "uploaded pyjama" in template.output_details.lower() for template in templates)
    assert [template.presentation_mode for template in templates] == ["garment", "model", "model", "model", "garment", "model"]
    assert validate_generation_template(
        "ecommerce-sleepwear-pyjamas-04", category="sleepwear_loungewear", channel="ecommerce", subtype="pyjama set", product_family="pyjamas",
    ).category == "sleepwear_loungewear"
    with pytest.raises(ValueError, match="product family"):
        validate_generation_template(
            "ecommerce-sleepwear-pyjamas-01", category="sleepwear_loungewear", channel="ecommerce", product_family="unregistered-sleepwear",
        )


def test_accessories_headwear_have_five_exact_reviewed_contracts():
    templates = list_generation_templates(category="headwear", channel="ecommerce", product_family="headwear")
    assert [template.id for template in templates] == [f"ecommerce-accessories-headwear-{index:02d}" for index in range(1, 6)]
    repo_root = Path(__file__).parents[3]
    assert all(template.reference_object_key and (repo_root / template.reference_object_key).is_file() for template in templates)
    assert [template.required_evidence for template in templates] == [("front_view",), ("front_view",), ("side_view",), ("rear_view",), ("front_view", "side_view")]
    assert [template.presentation_mode for template in templates] == ["garment", "model", "model", "model", "model"]
    assert validate_generation_template("ecommerce-accessories-headwear-01", category="headwear", channel="ecommerce", product_family="headwear")


def test_accessories_ties_have_seven_exact_reviewed_contracts():
    templates = list_generation_templates(category="neckwear", channel="ecommerce", product_family="ties")
    assert [template.id for template in templates] == [f"ecommerce-accessories-ties-{index:02d}" for index in range(1, 8)]
    repo_root = Path(__file__).parents[3]
    assert all(template.reference_object_key and (repo_root / template.reference_object_key).is_file() for template in templates)
    assert all(template.aspect_ratio == "1:1" and template.output_details for template in templates)
    assert [template.presentation_mode for template in templates] == ["model", "model", "garment", "garment", "garment", "model", "model"]


def test_unclassified_belt_family_uses_belt_template():
    template = validate_generation_template(
        "ecommerce-accessories-belts-01",
        category="accessories",
        channel="ecommerce",
        subtype="leather belt",
        product_family="unclassified",
    )
    assert template.id == "ecommerce-accessories-belts-01"


def test_accessories_belts_have_four_exact_contracts():
    templates = list_generation_templates(category="accessories", channel="ecommerce", product_family="belts")
    assert [template.id for template in templates] == [f"ecommerce-accessories-belts-{index:02d}" for index in (1, 3, 4, 5)]
    repo_root = Path(__file__).parents[3]
    assert all(template.reference_object_key and (repo_root / template.reference_object_key).is_file() for template in templates)
    assert all(template.aspect_ratio == "4:5" and template.output_details for template in templates)
    assert [template.presentation_mode for template in templates] == ["garment", "garment", "garment", "model"]


def test_accessories_gloves_have_four_exact_contracts():
    templates = list_generation_templates(category="accessories", channel="ecommerce", product_family="gloves")
    assert [template.id for template in templates] == [f"ecommerce-accessories-gloves-{index:02d}" for index in range(1, 5)]
    repo_root = Path(__file__).parents[3]
    assert all(template.reference_object_key and (repo_root / template.reference_object_key).is_file() for template in templates)
    assert all(template.aspect_ratio == "4:5" and template.output_details for template in templates)
    assert [template.presentation_mode for template in templates] == ["garment", "garment", "model", "model"]


def test_unclassified_glove_family_uses_glove_template():
    template = validate_generation_template(
        "ecommerce-accessories-gloves-01",
        category="accessories",
        channel="ecommerce",
        subtype="gloves",
        product_family="unclassified",
    )
    assert template.id == "ecommerce-accessories-gloves-01"
    assert validate_generation_template(
        "ecommerce-accessories-gloves-01",
        category="gloves",
        channel="ecommerce",
        subtype="Black thermal grip gloves",
        product_family="unclassified",
    ).id == "ecommerce-accessories-gloves-01"


def test_accessories_scarves_have_three_exact_contracts():
    templates = list_generation_templates(category="accessories", channel="ecommerce", product_family="scarves")
    assert [template.id for template in templates] == [f"ecommerce-accessories-scarves-{index:02d}" for index in range(1, 4)]
    repo_root = Path(__file__).parents[3]
    assert all(template.reference_object_key and (repo_root / template.reference_object_key).is_file() for template in templates)
    assert [template.presentation_mode for template in templates] == ["garment", "garment", "model"]


def test_mens_sleepwear_robes_have_six_exact_reviewed_contracts():
    templates = list_generation_templates(category="sleepwear_loungewear", channel="ecommerce", product_family="robes")
    assert [template.id for template in templates] == [f"ecommerce-sleepwear-robes-{index:02d}" for index in range(1, 7)]
    repo_root = Path(__file__).parents[3]
    assert all(template.reference_object_key and (repo_root / template.reference_object_key).is_file() for template in templates)
    assert [template.required_evidence for template in templates] == [("front_view|flat_lay",), ("front_view|flat_lay",), ("front_view|flat_lay",), ("rear_view",), ("front_view|flat_lay",), ("front_view|flat_lay",)]
    assert [template.presentation_mode for template in templates] == ["model", "garment", "model", "model", "invisible_mannequin", "model"]
    assert validate_generation_template(
        "ecommerce-sleepwear-robes-05", category="sleepwear_loungewear", channel="ecommerce", subtype="robe", product_family="robes",
    ).category == "sleepwear_loungewear"


def test_template_can_be_validated_for_tops_ecommerce():
    template = validate_generation_template(
        "ecommerce-clean-product-shot",
        category="TOPS",
        channel="Ecommerce",
    )

    assert template.name == "Clean Product Shot"


def test_template_rejects_wrong_category_or_channel():
    for category, channel in [("footwear", "ecommerce"), ("tops", "lifestyle")]:
        try:
            validate_generation_template(
                "ecommerce-clean-product-shot",
                category=category,
                channel=channel,
            )
        except ValueError as error:
            assert "not available" in str(error)
        else:
            raise AssertionError("Expected template validation to fail")


def test_listing_filters_templates():
    templates = list_generation_templates(category="tops", channel="ecommerce")
    assert len(templates) == 62
    assert {family: len(list_generation_templates(category="tops", channel="ecommerce", product_family=family)) for family in (
        "shirts", "t-shirts-casual-tops", "sleeveless-tops", "knitwear", "hoodies",
    )} == {
            "shirts": 14, "t-shirts-casual-tops": 9, "sleeveless-tops": 6,
        "knitwear": 11, "hoodies": 12,
    }
    listed_front = next(template for template in templates if template.id == TOPS_FRONT_VIEW.id)
    assert listed_front.id == TOPS_FRONT_VIEW.id
    assert listed_front.required_evidence == ("front_view",)
    assert len(list_generation_templates(category="outerwear", channel="ecommerce")) == 30
    assert len(list_generation_templates(category="outerwear", channel="ecommerce", product_family="jackets")) == 9
    assert len(list_generation_templates(category="outerwear", channel="ecommerce", product_family="coats")) == 11
    assert len(list_generation_templates(category="outerwear", channel="ecommerce", product_family="gilets-padded-vests")) == 10
    assert len(list_generation_templates(category="footwear", channel="ecommerce")) == 34
    assert len(list_generation_templates(category="footwear", channel="ecommerce", product_family="shoes")) == 17
    assert len(list_generation_templates(category="footwear", channel="ecommerce", product_family="heels")) == 8
    assert len(list_generation_templates(category="footwear", channel="ecommerce", product_family="boots")) == 9
    assert len(list_generation_templates(category="socks", channel="ecommerce")) == 8
    assert len(list_generation_templates(category="bottoms", channel="ecommerce")) == 41
    assert len(list_generation_templates(category="bottoms", channel="ecommerce", product_family="leggings")) == 8
    assert len(list_generation_templates(category="bottoms", channel="ecommerce", product_family="shorts")) == 9
    assert len(list_generation_templates(category="bottoms", channel="ecommerce", product_family="casual_bottoms")) == 9
    assert get_generation_template("ecommerce-footwear-sole-view").category == "footwear"
    assert get_generation_template("ecommerce-socks-knit-texture").category == "socks"


def test_underwear_templates_cover_the_six_ecommerce_views():
    templates = list_generation_templates(category="underwear", channel="ecommerce", product_family="lower_body_underwear")
    assert [template.id for template in templates] == [
        "ecommerce-underwear-front-model",
        "ecommerce-underwear-front-flat-lay",
        "ecommerce-underwear-rear-three-quarter",
        "ecommerce-underwear-front-product",
        "ecommerce-underwear-side-profile",
        "ecommerce-underwear-waistband-detail",
    ]
    assert templates[0].output_presentation == "worn_product"
    assert templates[0].artwork_surface_mode == "worn"
    assert templates[2].required_evidence == ("rear_view",)
    assert templates[5].artwork_surface_mode == "detail"
    assert "category_details.elastic_details" in templates[5].required_product_fields
    assert "category_details.fabric_appearance" in templates[5].required_product_fields
    assert validate_generation_template(
        "ecommerce-underwear-front-product",
        category="underwear",
        channel="ecommerce",
        subtype="boxers",
        product_family="lower_body_underwear",
    ).category == "underwear"
    for family in (None, "bra", "removed_family"):
        try:
            validate_generation_template(
                "ecommerce-underwear-front-product",
                category="underwear",
                channel="ecommerce",
                product_family=family,
            )
        except ValueError as error:
            assert "product family" in str(error)
        else:
            raise AssertionError("Expected lower-body template validation to fail")


def test_bottoms_templates_accept_known_families_and_generic_fallback():
    template_id = "ecommerce-bottoms-front-view"

    for family in ("structured_bottoms", None):
        assert validate_generation_template(
            template_id,
            category="bottoms",
            channel="ecommerce",
            product_family=family,
        ).category == "bottoms"

    assert validate_generation_template(
        "ecommerce-bottoms-shorts-01", category="bottoms", channel="ecommerce", product_family="shorts",
    ).version == 2
    shorts_templates = list_generation_templates(category="bottoms", channel="ecommerce", product_family="shorts")
    for template in shorts_templates[4:8]:
        assert "T-shirt" in template.prompt_instructions or "T-shirt" in template.prompt_instructions
    assert "shirtless" in get_generation_template("ecommerce-bottoms-shorts-07").prompt_instructions
    with pytest.raises(ValueError, match="product family"):
        validate_generation_template(
            template_id,
            category="bottoms",
            channel="ecommerce",
            product_family="removed_family",
        )


def test_bra_pack_is_locked_to_product_only_view():
    templates = list_generation_templates(category="underwear", channel="ecommerce", product_family="bra")
    assert [template.id for template in templates] == [
        "ecommerce-underwear-bra-01",
        "ecommerce-underwear-bra-front-construction-detail",
    ]
    assert all(template.presentation_mode == "garment" for template in templates)
    assert all(template.version == 2 and template.output_details for template in templates)
    assert templates[1].required_evidence == ("detail",)


def test_underwear_readiness_uses_only_front_and_rear_evidence():
    templates = {template.id: template for template in list_generation_templates(category="underwear", channel="ecommerce")}
    assert templates["ecommerce-underwear-front-product"].required_evidence == ("front_view",)
    assert templates["ecommerce-underwear-rear-three-quarter"].required_evidence == ("rear_view",)
    assert templates["ecommerce-underwear-waistband-detail"].required_evidence == ("front_view",)


def test_tops_family_templates_follow_explicit_asset_compositions():
    expected = {
        "shirts": (14, "front_view", "rear_view"),
        "t-shirts-casual-tops": (9, "front_view", "rear_view"),
        "sleeveless-tops": (6, "front_view", "rear_view"),
        "knitwear": (11, "front_view", "rear_view"),
        "hoodies": (12, "front_view", "rear_view"),
    }
    for family, (count, _, _) in expected.items():
        templates = list_generation_templates(category="tops", channel="ecommerce", product_family=family)
        assert len(templates) == count
        assert all(template.applicable_families == (family,) for template in templates)
        assert all(template.required_evidence in (("front_view",), ("rear_view",)) for template in templates)

    assert "visible fabric-covered headless mannequin" in get_generation_template("ecommerce-tops-sleeveless-tops-04").prompt_instructions
    angled_sleeveless = get_generation_template("ecommerce-tops-sleeveless-tops-03")
    assert "completely invisible mannequin" in angled_sleeveless.prompt_instructions
    assert "front three-quarter angle" in angled_sleeveless.prompt_instructions
    flat_sleeveless = get_generation_template("ecommerce-tops-sleeveless-tops-05")
    assert "laid flat" in flat_sleeveless.prompt_instructions
    assert "true overhead" in flat_sleeveless.prompt_instructions
    assert "do not inflate the bust" in flat_sleeveless.prompt_instructions
    flat_shirt = get_generation_template("ecommerce-tops-shirts-03")
    assert "laid flat" in flat_shirt.prompt_instructions
    assert "true overhead" in flat_shirt.prompt_instructions
    assert "do not inflate the chest" in flat_shirt.prompt_instructions
    assert "actual cuff" in get_generation_template("ecommerce-tops-shirts-06").prompt_instructions
    assert "collar and upper button placket" in get_generation_template("ecommerce-tops-shirts-09").prompt_instructions
    assert "being adjusted" in get_generation_template("ecommerce-tops-shirts-10").prompt_instructions
    assert "side or three-quarter" in get_generation_template("ecommerce-tops-t-shirts-casual-tops-08").prompt_instructions
    assert "side or three-quarter angle" in get_generation_template("ecommerce-tops-hoodies-07").prompt_instructions
    assert get_generation_template("ecommerce-tops-sleeveless-tops-04").required_evidence == ("front_view",)
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-06").required_evidence == ("rear_view",)
    assert get_generation_template("ecommerce-tops-hoodies-03").required_evidence == ("rear_view",)

    shirts_templates = list_generation_templates(category="tops", channel="ecommerce", product_family="shirts")
    assert len(shirts_templates) == 14
    assert [template.required_evidence for template in shirts_templates] == [("front_view",)] * 12 + [("rear_view",)] * 2
    assert get_generation_template("ecommerce-tops-sleeveless-tops-04").output_presentation == "product_only"
    assert get_generation_template("ecommerce-tops-sleeveless-tops-04").name == "Front Headless Mannequin"
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-05").output_presentation == "product_only"
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-10").required_evidence == ("rear_view",)
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-10").name == "Rear Invisible Mannequin"
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-07") is None


def test_tshirt_family_templates_follow_the_frontend_benchmark_contract():
    templates = list_generation_templates(
        category="tops", channel="ecommerce", product_family="t-shirts-casual-tops",
    )
    assert [template.name for template in templates] == [
        "Front Product", "Hem & Fit Detail", "Folded T-Shirt", "Front Model (Hand in Pocket)",
        "Front Invisible Mannequin", "Rear Model", "Side / Three-Quarter Invisible Mannequin",
        "Fabric Texture Detail", "Rear Invisible Mannequin",
    ]
    assert [template.version for template in templates] == [2] * 9
    assert [template.output_presentation for template in templates] == [
        "product_only", "worn_product", "product_only", "worn_product", "product_only",
        "worn_product", "product_only", "product_only", "product_only",
    ]
    assert "laid flat" in templates[0].prompt_instructions
    assert "do not inflate the chest" in templates[0].prompt_instructions
    assert "hem and fit" in templates[1].prompt_instructions
    assert "neatly folded" in templates[2].prompt_instructions
    assert "one hand resting inside a trouser pocket" in templates[3].prompt_instructions
    assert "complete T-shirt" in templates[4].prompt_instructions
    assert "completely invisible mannequin" in templates[4].prompt_instructions
    assert "not a visible headless mannequin" in templates[4].prompt_instructions
    assert "rear-facing" in templates[5].prompt_instructions
    assert "completely invisible mannequin" in templates[6].prompt_instructions
    assert "not a visible headless mannequin" in templates[6].prompt_instructions
    assert "side or three-quarter" in templates[6].prompt_instructions
    assert "actual T-shirt's fabric surface" in templates[7].prompt_instructions
    assert "slight controlled twist" in templates[7].prompt_instructions
    assert "completely invisible mannequin" in templates[8].prompt_instructions
    assert "not a visible headless mannequin" in templates[8].prompt_instructions
    assert "complete rear" in templates[8].prompt_instructions
    assert get_generation_template("ecommerce-tops-hoodies-07").output_presentation == "worn_product"
    assert get_generation_template("ecommerce-tops-hoodies-08").artwork_surface_mode == "rear"
    assert get_generation_template("ecommerce-tops-shirts-07").artwork_surface_mode == "detail"
    assert get_generation_template("ecommerce-tops-knitwear-01").artwork_surface_mode == "folded"


def test_tops_templates_define_artwork_visibility_and_surface_policy():
    templates = {template.id: template for template in list_generation_templates(category="tops", channel="ecommerce")}

    assert templates["ecommerce-tops-front-view"].artwork_visibility == "full"
    assert templates["ecommerce-tops-folded-view"].artwork_surface_mode == "folded"
    assert templates["ecommerce-tops-side-angle-model"].artwork_visibility == "partial"
    assert templates["ecommerce-tops-back"].artwork_visibility == "none"
    assert templates["ecommerce-tops-back-model"].artwork_visibility == "none"
    fabric = templates["ecommerce-tops-fabric"]
    assert fabric.artwork_visibility == "conditional"
    assert "ONE single-frame" in fabric.prompt_instructions
    assert "collage" in fabric.negative_prompt


def test_bottoms_templates_cover_all_subtypes_and_keep_folded_flat_lay_policy():
    templates = list_generation_templates(category="bottoms", channel="ecommerce", product_family="structured_bottoms")
    assert [template.name for template in templates] == [
        "Front View",
        "Back View",
        "Side / Three-Quarter Product",
        "Folded Product Flat Lay",
        "Front Model",
        "Back Model",
        "Waistband & Closure Detail",
        "Pocket Panel Detail",
        "Hem & Leg Detail",
    ]
    assert templates[2].output_presentation == "worn_product"
    assert templates[2].artwork_surface_mode == "angled"
    assert templates[3].id == "ecommerce-bottoms-folded-product-flat-lay"
    assert templates[3].artwork_surface_mode == "folded"
    assert templates[3].output_presentation == "product_only"
    assert templates[4].output_presentation == "worn_product"
    assert templates[5].output_presentation == "worn_product"
    assert templates[6].output_presentation == "worn_product"
    assert "category_details.belt_loops" in templates[6].required_product_fields
    assert templates[7].output_presentation == "product_only"
    assert "category_details.panel_or_seam_details" in templates[7].required_product_fields
    assert templates[8].artwork_surface_mode == "detail"
    assert get_generation_template("ecommerce-bottoms-fabric-surface-detail") is None


def test_skirts_have_reviewed_details_modes_evidence_and_local_benchmarks():
    templates = list_generation_templates(
        category="bottoms", channel="ecommerce", product_family="skirts",
    )
    assert [template.presentation_mode for template in templates] == [
        "garment", "garment", "model", "model", "model", "model",
    ]
    assert [template.required_evidence for template in templates] == [
        ("front_view",), ("rear_view",), ("front_view",),
        ("rear_view",), ("front_view",), ("front_view",),
    ]
    assert all(template.output_details for template in templates)
    repo_root = Path(__file__).parents[3]
    assert all(
        template.reference_object_key
        and (repo_root / template.reference_object_key).is_file()
        for template in templates
    )


def test_leggings_have_reviewed_details_modes_evidence_and_local_benchmarks():
    templates = list_generation_templates(
        category="bottoms", channel="ecommerce", product_family="leggings",
    )
    assert [template.presentation_mode for template in templates] == [
        "model", "garment", "invisible_mannequin", "invisible_mannequin",
        "invisible_mannequin", "garment", "model", "model",
    ]
    assert [template.required_evidence for template in templates] == [
        ("front_view",), ("front_view",), ("rear_view",), ("front_view",),
        ("front_view",), ("front_view",), ("rear_view",), ("front_view",),
    ]
    assert all(template.output_details for template in templates)
    repo_root = Path(__file__).parents[3]
    assert all(
        template.reference_object_key
        and (repo_root / template.reference_object_key).is_file()
        for template in templates
    )


def test_joggers_have_reviewed_details_modes_evidence_and_local_benchmarks():
    templates = list_generation_templates(
        category="bottoms", channel="ecommerce", product_family="casual_bottoms",
    )
    assert [template.presentation_mode for template in templates] == [
        "garment", "invisible_mannequin", "invisible_mannequin", "invisible_mannequin",
        "model", "model", "model", "model", "garment",
    ]
    assert [template.required_evidence for template in templates] == [
        ("front_view",), ("front_view",), ("front_view",), ("rear_view",),
        ("front_view",), ("front_view",), ("rear_view",), ("front_view",),
        ("front_view",),
    ]
    assert all(template.output_details for template in templates)
    repo_root = Path(__file__).parents[3]
    assert all(
        template.reference_object_key
        and (repo_root / template.reference_object_key).is_file()
        for template in templates
    )


def test_shorts_have_reviewed_details_modes_evidence_and_local_benchmarks():
    templates = list_generation_templates(
        category="bottoms", channel="ecommerce", product_family="shorts",
    )
    assert [template.presentation_mode for template in templates] == [
        "garment", "invisible_mannequin", "invisible_mannequin", "invisible_mannequin",
        "model", "model", "model", "model", "garment",
    ]
    assert [template.required_evidence for template in templates] == [
        ("front_view",), ("front_view",), ("front_view",), ("rear_view",),
        ("front_view",), ("front_view",), ("rear_view",), ("front_view",),
        ("front_view",),
    ]
    assert all(template.output_details for template in templates)
    repo_root = Path(__file__).parents[3]
    assert all(
        template.reference_object_key
        and (repo_root / template.reference_object_key).is_file()
        for template in templates
    )


def test_structured_bottoms_have_reviewed_details_modes_and_local_benchmarks():
    templates = list_generation_templates(
        category="bottoms", channel="ecommerce", product_family="structured_bottoms",
    )
    assert [template.presentation_mode for template in templates] == [
        "garment", "garment", "model", "garment", "model",
        "model", "model", "garment", "garment",
    ]
    assert all(template.output_details for template in templates)
    repo_root = Path(__file__).parents[3]
    assert all(
        template.reference_object_key
        and (repo_root / template.reference_object_key).is_file()
        for template in templates
    )


def test_bottoms_evidence_is_front_or_rear_only_for_every_family():
    expected_front = {
        "ecommerce-bottoms-front-view", "ecommerce-bottoms-side-angle-product",
        "ecommerce-bottoms-folded-product-flat-lay", "ecommerce-bottoms-front-model",
        "ecommerce-bottoms-waistband-closure-detail", "ecommerce-bottoms-pocket-panel-detail",
        "ecommerce-bottoms-hem-leg-detail",
    }
    expected_rear = {"ecommerce-bottoms-back-view", "ecommerce-bottoms-back-model"}

    for family in ("structured_bottoms",):
        templates = {
            template.id: template
            for template in list_generation_templates(
                category="bottoms", channel="ecommerce", product_family=family,
            )
        }
        assert {template_id for template_id, template in templates.items() if template.required_evidence == ("front_view",)} == expected_front
        assert {template_id for template_id, template in templates.items() if template.required_evidence == ("rear_view",)} == expected_rear

    joggers = list_generation_templates(category="bottoms", channel="ecommerce", product_family="casual_bottoms")
    assert len(joggers) == 9
    assert joggers[3].artwork_surface_mode == "rear"
    assert joggers[8].artwork_surface_mode == "folded"
    leggings = list_generation_templates(category="bottoms", channel="ecommerce", product_family="leggings")
    assert len(leggings) == 8
    assert leggings[2].artwork_surface_mode == "rear"
    assert leggings[5].artwork_surface_mode == "folded"

    for subtype in ("shorts", "skirt", "leggings", "trousers", "jeans", "cargo trousers", "joggers", "chinos"):
        assert validate_generation_template(
            "ecommerce-bottoms-front-view",
            category="bottoms",
            channel="ecommerce",
            subtype=subtype,
        ).category == "bottoms"
