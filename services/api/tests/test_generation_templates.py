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
    assert len(templates) == 65
    assert {family: len(list_generation_templates(category="tops", channel="ecommerce", product_family=family)) for family in (
        "shirts", "t-shirts-casual-tops", "sleeveless-tops", "knitwear", "hoodies",
    )} == {
        "shirts": 15, "t-shirts-casual-tops": 10, "sleeveless-tops": 7,
        "knitwear": 11, "hoodies": 12,
    }
    listed_front = next(template for template in templates if template.id == TOPS_FRONT_VIEW.id)
    assert listed_front.id == TOPS_FRONT_VIEW.id
    assert listed_front.required_evidence == ("front_view",)
    assert len(list_generation_templates(category="outerwear", channel="ecommerce")) == 10
    assert len(list_generation_templates(category="footwear", channel="ecommerce")) == 10
    assert len(list_generation_templates(category="socks", channel="ecommerce")) == 8
    assert len(list_generation_templates(category="bottoms", channel="ecommerce")) == 9
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

    for family in ("structured_bottoms", "casual_bottoms", "leggings", "skirts", None):
        assert validate_generation_template(
            template_id,
            category="bottoms",
            channel="ecommerce",
            product_family=family,
        ).category == "bottoms"

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
        "t-shirts-casual-tops": (10, "front_view", "rear_view"),
        "sleeveless-tops": (7, "front_view", "rear_view"),
        "knitwear": (11, "front_view", "rear_view"),
        "hoodies": (12, "front_view", "rear_view"),
    }
    for family, (count, _, _) in expected.items():
        templates = list_generation_templates(category="tops", channel="ecommerce", product_family=family)
        assert len(templates) == count
        assert all(template.applicable_families == (family,) for template in templates)
        assert all(template.required_evidence in (("front_view",), ("rear_view",)) for template in templates)

    assert "product-only" in get_generation_template("ecommerce-tops-sleeveless-tops-04").prompt_instructions
    assert "side or three-quarter" in get_generation_template("ecommerce-tops-t-shirts-casual-tops-05").prompt_instructions
    assert "side or three-quarter angle" in get_generation_template("ecommerce-tops-hoodies-07").prompt_instructions
    assert get_generation_template("ecommerce-tops-sleeveless-tops-04").required_evidence == ("front_view",)
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-06").required_evidence == ("rear_view",)
    assert get_generation_template("ecommerce-tops-hoodies-03").required_evidence == ("rear_view",)

    assert get_generation_template("ecommerce-tops-sleeveless-tops-04").output_presentation == "product_only"
    assert get_generation_template("ecommerce-tops-t-shirts-casual-tops-05").output_presentation == "product_only"
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
    assert templates["ecommerce-tops-fabric"].artwork_visibility == "conditional"


def test_bottoms_templates_cover_all_subtypes_and_keep_folded_flat_lay_policy():
    templates = list_generation_templates(category="bottoms", channel="ecommerce")
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

    for family in ("structured_bottoms", "casual_bottoms", "leggings", "skirts", None):
        templates = {
            template.id: template
            for template in list_generation_templates(
                category="bottoms", channel="ecommerce", product_family=family,
            )
        }
        assert {template_id for template_id, template in templates.items() if template.required_evidence == ("front_view",)} == expected_front
        assert {template_id for template_id, template in templates.items() if template.required_evidence == ("rear_view",)} == expected_rear

    for subtype in ("shorts", "skirt", "leggings", "trousers", "jeans", "cargo trousers", "joggers", "chinos"):
        assert validate_generation_template(
            "ecommerce-bottoms-front-view",
            category="bottoms",
            channel="ecommerce",
            subtype=subtype,
        ).category == "bottoms"
