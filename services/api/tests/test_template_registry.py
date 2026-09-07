import pytest

from productframe_api.generation_templates import (
    TOPS_FRONT_VIEW,
    get_generation_template,
    list_generation_templates,
    validate_generation_template,
)


def test_tops_ecommerce_front_view_is_a_text_only_product_template():
    template = get_generation_template("ecommerce-tops-front-view")

    assert template.id == TOPS_FRONT_VIEW.id
    assert template.required_evidence == ("front_view",)
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


def test_outerwear_front_medium_accepts_zip_up_hoodie_subtype():
    template = validate_generation_template(
        "ecommerce-outerwear-front-medium",
        category="outerwear",
        channel="ecommerce",
        subtype="zip up hoodie sweatshirt with front pockets",
    )
    assert template.name == "Front Medium"


def test_front_view_rejects_wrong_category_or_channel_but_allows_unknown_subtype():
    with pytest.raises(ValueError):
        validate_generation_template("ecommerce-tops-front-view", category="footwear", channel="ecommerce")
    with pytest.raises(ValueError):
        validate_generation_template("ecommerce-tops-front-view", category="tops", channel="lifestyle")
    assert validate_generation_template(
        "ecommerce-tops-front-view", category="tops", channel="ecommerce", subtype="zip-up hoodie sweatshirt"
    ).id == "ecommerce-tops-front-view"
