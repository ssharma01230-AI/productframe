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
    assert len(templates) == 63
    assert {family: len(list_generation_templates(category="tops", channel="ecommerce", product_family=family)) for family in (
        "shirts", "t-shirts-casual-tops", "sleeveless-tops", "knitwear", "hoodies",
    )} == {
            "shirts": 15, "t-shirts-casual-tops": 9, "sleeveless-tops": 6,
        "knitwear": 11, "hoodies": 12,
    }
    listed_front = next(template for template in templates if template.id == TOPS_FRONT_VIEW.id)
    assert listed_front.id == TOPS_FRONT_VIEW.id
    assert listed_front.required_evidence == ("front_view",)
    assert len(list_generation_templates(category="outerwear", channel="ecommerce")) == 10
    assert len(list_generation_templates(category="footwear", channel="ecommerce")) == 9
    assert len(list_generation_templates(category="socks", channel="ecommerce")) == 8
    assert len(list_generation_templates(category="bottoms", channel="ecommerce")) == 41
    assert len(list_generation_templates(category="bottoms", channel="ecommerce", product_family="leggings")) == 8
    assert len(list_generation_templates(category="bottoms", channel="ecommerce", product_family="shorts")) == 9
    assert len(list_generation_templates(category="bottoms", channel="ecommerce", product_family="casual_bottoms")) == 9
    assert get_generation_template("ecommerce-footwear-sole-view").category == "footwear"
    assert get_generation_template("ecommerce-socks-knit-texture").category == "socks"


def test_underwear_templates_cover_the_seven_ecommerce_views():
    templates = list_generation_templates(category="underwear", channel="ecommerce")
    assert [template.id for template in templates] == [
        "ecommerce-underwear-front-model",
        "ecommerce-underwear-front-flat-lay",
        "ecommerce-underwear-back-flat-lay",
        "ecommerce-underwear-rear-three-quarter",
        "ecommerce-underwear-front-product",
        "ecommerce-underwear-side-profile",
        "ecommerce-underwear-waistband-detail",
    ]
    assert templates[0].output_presentation == "worn_product"
    assert templates[0].artwork_surface_mode == "worn"
    assert templates[2].required_evidence == ("rear_view",)
    assert templates[3].required_evidence == ("rear_view",)
    assert templates[6].artwork_surface_mode == "detail"
    assert "category_details.elastic_details" in templates[6].required_product_fields
    assert "category_details.fabric_appearance" in templates[6].required_product_fields
    assert validate_generation_template(
        "ecommerce-underwear-front-product",
        category="underwear",
        channel="ecommerce",
        subtype="boxers",
        product_family="lower_body_underwear",
    ).category == "underwear"
    for family in (None, "bra", "lingerie", "base_layer", "underwear_set"):
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
            product_family="underwear_set",
        )


def test_underwear_readiness_uses_only_front_and_rear_evidence():
    templates = {template.id: template for template in list_generation_templates(category="underwear", channel="ecommerce")}
    assert templates["ecommerce-underwear-front-product"].required_evidence == ("front_view",)
    assert templates["ecommerce-underwear-back-flat-lay"].required_evidence == ("rear_view",)
    assert templates["ecommerce-underwear-waistband-detail"].required_evidence == ("front_view",)


def test_tops_family_templates_follow_explicit_asset_compositions():
    expected = {
        "shirts": (15, "front_view", "rear_view"),
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

    assert "mannequin" in get_generation_template("ecommerce-tops-sleeveless-tops-04").prompt_instructions
    assert "side or three-quarter" in get_generation_template("ecommerce-tops-t-shirts-casual-tops-08").prompt_instructions
    assert "side or three-quarter angle" in get_generation_template("ecommerce-tops-hoodies-07").prompt_instructions
    assert get_generation_template("ecommerce-tops-sleeveless-tops-04").required_evidence == ("front_view",)
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-06").required_evidence == ("rear_view",)
    assert get_generation_template("ecommerce-tops-hoodies-03").required_evidence == ("rear_view",)

    assert get_generation_template("ecommerce-tops-sleeveless-tops-04").output_presentation == "product_only"
    assert get_generation_template("ecommerce-tops-sleeveless-tops-04").name == "Front Invisible Mannequin"
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-05").output_presentation == "product_only"
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-10").required_evidence == ("rear_view",)
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-10").name == "Rear Invisible Mannequin"
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-07") is None


def test_tshirt_family_templates_follow_the_frontend_benchmark_contract():
    templates = list_generation_templates(
        category="tops", channel="ecommerce", product_family="t-shirts-casual-tops",
    )
    assert [template.name for template in templates] == [
        "Front Product (Shaped)", "Hem & Fit Detail", "Folded T-Shirt", "Front Model (Hand in Pocket)",
        "Front Invisible Mannequin", "Rear Model", "Side / Three-Quarter Invisible Mannequin",
        "Fabric Texture Detail", "Rear Invisible Mannequin",
    ]
    assert [template.version for template in templates] == [2] * 9
    assert [template.output_presentation for template in templates] == [
        "product_only", "worn_product", "product_only", "worn_product", "product_only",
        "worn_product", "product_only", "product_only", "product_only",
    ]
    assert "naturally three-dimensionally shaped" in templates[0].prompt_instructions
    assert "hem and fit" in templates[1].prompt_instructions
    assert "neatly folded" in templates[2].prompt_instructions
    assert "one hand resting inside a trouser pocket" in templates[3].prompt_instructions
    assert "complete T-shirt" in templates[4].prompt_instructions
    assert "invisible/headless mannequin" in templates[4].prompt_instructions
    assert "rear-facing" in templates[5].prompt_instructions
    assert "invisible/headless mannequin" in templates[6].prompt_instructions
    assert "side or three-quarter" in templates[6].prompt_instructions
    assert "actual T-shirt's fabric surface" in templates[7].prompt_instructions
    assert "slight controlled twist" in templates[7].prompt_instructions
    assert "invisible/headless mannequin" in templates[8].prompt_instructions
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


def test_bottoms_evidence_is_front_or_rear_only_for_every_family():
    expected_front = {
        "ecommerce-bottoms-front-view", "ecommerce-bottoms-side-angle-product",
        "ecommerce-bottoms-folded-product-flat-lay", "ecommerce-bottoms-front-model",
        "ecommerce-bottoms-waistband-closure-detail", "ecommerce-bottoms-pocket-panel-detail",
        "ecommerce-bottoms-hem-leg-detail",
    }
    expected_rear = {"ecommerce-bottoms-back-view", "ecommerce-bottoms-back-model"}

    for family in ("structured_bottoms", None):
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
