import pytest

from productframe_api.generation_templates import (
    TOPS_FRONT_VIEW,
    get_generation_template,
    list_generation_templates,
    validate_generation_template,
)


def test_tops_ecommerce_front_view_is_a_text_only_product_template():
    template = get_generation_template("ecommerce-tops-front-view")

    assert template == TOPS_FRONT_VIEW
    assert template.category == "tops"
    assert template.channel == "ecommerce"
    assert template.reference_mode == "product_only"
    assert template.output_presentation == "front_studio_product"
    assert "category_details.neckline_type" in template.required_product_fields
    assert "Product identity data" in template.prompt_format_rules[0]


def test_front_view_supports_tops_subtypes():
    template = validate_generation_template(
        "ecommerce-tops-front-view",
        category="tops",
        channel="ecommerce",
        subtype="jumper",
    )
    assert template.id == "ecommerce-tops-front-view"
    assert list_generation_templates(category="tops", channel="ecommerce", subtype="hoodie")


def test_front_view_rejects_wrong_category_channel_or_subtype():
    with pytest.raises(ValueError):
        validate_generation_template("ecommerce-tops-front-view", category="footwear", channel="ecommerce")
    with pytest.raises(ValueError):
        validate_generation_template("ecommerce-tops-front-view", category="tops", channel="lifestyle")
    with pytest.raises(ValueError, match="subtype"):
        validate_generation_template("ecommerce-tops-front-view", category="tops", channel="ecommerce", subtype="jeans")
