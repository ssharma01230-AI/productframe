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
    assert len(templates) == 10
    assert next(template for template in templates if template.id == TOPS_FRONT_VIEW.id) == TOPS_FRONT_VIEW
    assert len(list_generation_templates(category="outerwear", channel="ecommerce")) == 10
    assert len(list_generation_templates(category="footwear", channel="ecommerce")) == 10
    assert len(list_generation_templates(category="socks", channel="ecommerce")) == 8
    assert get_generation_template("ecommerce-footwear-sole-view").category == "footwear"
    assert get_generation_template("ecommerce-socks-knit-texture").category == "socks"


def test_tops_templates_define_artwork_visibility_and_surface_policy():
    templates = {template.id: template for template in list_generation_templates(category="tops", channel="ecommerce")}

    assert templates["ecommerce-tops-front-view"].artwork_visibility == "full"
    assert templates["ecommerce-tops-folded-view"].artwork_surface_mode == "folded"
    assert templates["ecommerce-tops-side-angle-model"].artwork_visibility == "partial"
    assert templates["ecommerce-tops-back"].artwork_visibility == "none"
    assert templates["ecommerce-tops-back-model"].artwork_visibility == "none"
    assert templates["ecommerce-tops-fabric"].artwork_visibility == "conditional"
