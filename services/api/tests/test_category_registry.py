import pytest

from productframe_api.category_registry import (
    CATEGORIES,
    CHANNELS,
    get_category_definition,
    validate_category_channel,
    validate_category_details,
)


def test_registry_contains_all_supported_categories_and_channels():
    assert {"tops", "outerwear", "bottoms", "underwear", "socks", "footwear", "scarves", "gloves", "rings", "neckwear", "watches", "bracelets", "earrings", "belts"} <= set(CATEGORIES)
    assert {"ecommerce", "lifestyle", "campaign"} == set(CHANNELS)


def test_tops_definition_has_required_fields_and_rules():
    tops = get_category_definition("TOPS")

    assert "category_details.neckline_type" in tops.required_analysis_fields
    assert "category_details.sleeve_type" in tops.required_analysis_fields
    assert any("V-neck" in rule for rule in tops.prompt_rules)


def test_category_details_are_validated_against_the_category_schema():
    details = validate_category_details("socks", {
        "subtype": "crew",
        "sock_length": "crew length",
        "cuff_height": "medium",
        "cuff_details": "ribbed",
        "toe_shape": "rounded",
        "heel_details": "reinforced heel",
        "toe_and_heel_reinforcement": "not clearly visible",
        "padding": "not visible",
        "ribbing_or_knit": "fine knit",
        "compression_features": [],
        "pattern": "solid",
        "fit_and_silhouette": "close fit",
        "visible_uncertainties": [],
    })

    assert details["subtype"] == "crew"


def test_unknown_category_or_channel_is_rejected():
    with pytest.raises(ValueError, match="Unsupported product category"):
        get_category_definition("bags")
    with pytest.raises(ValueError, match="Unsupported output channel"):
        validate_category_channel("tops", "social")
