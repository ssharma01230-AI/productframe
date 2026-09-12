import pytest

from productframe_api.category_registry import (
    BOTTOMS_FAMILY_SUBTYPE_MAP,
    CATEGORIES,
    CHANNELS,
    controlled_subtype_label,
    get_bottoms_family_for_subtype,
    get_category_definition,
    get_tops_family_for_subtype,
    validate_category_channel,
    validate_category_details,
)


def test_controlled_subtype_labels_never_use_long_product_type():
    cases = [
        ("tops", "t-shirts-casual-tops", "long sleeve cotton crew neck t-shirt with print", "T-Shirt"),
        ("footwear", "heels", "red suede pointed toe pumps with mid heel", "Heels"),
        ("bottoms", "leggings", "black high-waisted full-length leggings", "Leggings"),
        ("outerwear", "jackets", "long waterproof hooded shell jacket", "Jacket"),
        ("accessories", "belts", "wide leather belt with brushed buckle", "Belt"),
        ("tops", None, None, "Unclassified"),
    ]
    for category, family, product_type, expected in cases:
        assert controlled_subtype_label(category=category, family=family, subtype=None, product_type=product_type) == expected


def test_registry_contains_all_supported_categories_and_channels():
    assert {"tops", "outerwear", "bottoms", "underwear", "socks", "footwear", "scarves", "gloves", "rings", "neckwear", "watches", "bracelets", "earrings", "belts"} <= set(CATEGORIES)
    assert {"ecommerce", "lifestyle", "campaign"} == set(CHANNELS)


def test_tops_definition_has_required_fields_and_rules():
    tops = get_category_definition("TOPS")

    assert "category_details.neckline_type" in tops.required_analysis_fields
    assert "category_details.sleeve_type" in tops.required_analysis_fields
    assert any("V-neck" in rule for rule in tops.prompt_rules)


def test_bottoms_definition_captures_all_ecommerce_template_identity_fields():
    bottoms = get_category_definition("BOTTOMS")

    for field in (
        "category_details.waist_height",
        "category_details.fly_or_closure",
        "category_details.leg_width",
        "category_details.garment_length",
        "category_details.hem_details",
        "category_details.fit_and_silhouette",
    ):
        assert field in bottoms.required_analysis_fields
    for field in (
        "category_details.pocket_details",
        "category_details.belt_loops",
        "category_details.panel_or_seam_details",
    ):
        assert field in bottoms.optional_analysis_fields
    assert any("lower midsection" in rule for rule in bottoms.prompt_rules)


def test_underwear_definition_and_details_cover_identity_fields():
    underwear = get_category_definition("underwear")
    for field in (
        "category_details.coverage",
        "category_details.fit_and_silhouette",
    ):
        assert field in underwear.required_analysis_fields
    for field in (
        "category_details.support_details",
        "category_details.cup_shape",
    ):
        assert field in underwear.optional_analysis_fields

    details = validate_category_details("underwear", {
        "subtype": "boxers",
        "coverage": "mid-thigh coverage",
        "waist_height": "mid-rise",
        "rise": "standard rise",
        "strap_type": "not applicable",
        "strap_width": "not applicable",
        "support_details": "pouch construction visible; support level uncertain",
        "cup_shape": "not applicable",
        "elastic_details": "covered elastic waistband",
        "closure_details": [],
        "seam_details": ["front centre seam", "side seams"],
        "fabric_appearance": "soft grey stretch jersey",
        "fit_and_silhouette": "close-fitting boxer brief silhouette",
        "visible_uncertainties": [],
    })
    assert details["subtype"] == "boxers"


def test_bottoms_family_is_nullable_and_controlled():
    base = {
        "subtype": "jeans",
        "waistband_type": "fixed waistband",
        "waist_height": "mid-rise",
        "fly_or_closure": "zip fly and button",
        "leg_shape": "straight",
        "leg_width": "regular",
        "garment_length": "full length",
        "hem_details": "plain hem",
        "pocket_details": ["front pockets"],
        "pleats_or_darts": [],
        "belt_loops": "visible",
        "panel_or_seam_details": ["side seams"],
        "fit_and_silhouette": "straight-leg silhouette",
        "visible_uncertainties": [],
    }

    assert validate_category_details("bottoms", {**base, "family": "structured_bottoms"})["family"] == "structured_bottoms"
    assert validate_category_details("bottoms", base)["family"] is None
    with pytest.raises(ValueError):
        validate_category_details("bottoms", {**base, "family": "jeans"})


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


def test_tops_descriptive_subtypes_route_to_family_packs():
    cases = {
        "button-down shirt with chest pocket": "shirts",
        "short sleeve t-shirt with graphic print": "t-shirts-casual-tops",
        "sleeveless vest top": "sleeveless-tops",
        "knitted sleeveless sweater vest": "sleeveless-tops",
        "chunky knit sweater with ribbed cuffs": "knitwear",
        "zip-up hoodie with drawstring hood and front pockets": "hoodies",
    }
    for subtype, family in cases.items():
        assert get_tops_family_for_subtype(subtype) == family


def test_bottoms_subtypes_have_one_controlled_rendering_family():
    bottoms = get_category_definition("bottoms")

    assert set(BOTTOMS_FAMILY_SUBTYPE_MAP) == set(bottoms.subtypes)
    assert get_bottoms_family_for_subtype(" Jeans ") == "structured_bottoms"
    assert get_bottoms_family_for_subtype("joggers") == "casual_bottoms"
    assert get_bottoms_family_for_subtype("wide leg drawstring pants") == "casual_bottoms"
    assert get_bottoms_family_for_subtype("leggings") == "leggings"
    assert get_bottoms_family_for_subtype("skirt") == "skirts"
    assert get_bottoms_family_for_subtype("unknown lower-body garment") is None
    assert get_bottoms_family_for_subtype(None) is None


def test_unknown_category_or_channel_is_rejected():
    with pytest.raises(ValueError, match="Unsupported product category"):
        get_category_definition("bags")
    with pytest.raises(ValueError, match="Unsupported output channel"):
        validate_category_channel("tops", "social")
