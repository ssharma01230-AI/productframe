from types import SimpleNamespace

from productframe_api.description_utils import bound_description, concise_product_description


def test_bound_description_never_exceeds_column_limit_or_splits_a_word():
    result = bound_description("word " * 100)
    assert len(result) <= 320
    assert result.endswith(".")
    assert "  " not in result


def test_category_aware_description_excludes_schema_syntax_and_styling():
    analysis = {
        "category": "footwear",
        "product_family": "heels",
        "colours": "red",
        "materials": "suede",
        "features": ["pointed toe", "mid-height heel", "white socks and trainers"],
        "description": "appearance='suede' stretch_or_flexibility='low stretch'",
        "category_details": {"subtype": "pointed toe red suede pumps", "toe_shape": "pointed", "heel_type": "mid-height", "closure_type": "not_visible"},
        "global_details": {"materials": {"appearance": "suede", "stretch_or_flexibility": "low stretch"}},
    }
    result = concise_product_description(analysis)
    assert "Red heels" in result
    assert "appearance=" not in result
    assert "stretch_or_flexibility" not in result
    assert "socks" not in result
    assert "trainers" not in result


def test_bottoms_description_joins_material_and_length_as_prose():
    analysis = {
        "category": "bottoms", "product_family": "casual_bottoms", "colours": "light blue",
        "materials": "smooth", "features": ["drawstring waistband"],
        "category_details": {"subtype": "casual shorts", "waist_height": "mid waist", "fit_and_silhouette": "relaxed fit", "garment_length": "above knee length", "panel_or_seam_details": ["side seams"]},
        "global_details": {},
    }
    result = concise_product_description(analysis)
    assert "appears to use smooth material and is above knee length" in result
    assert "uses smooth, with" not in result


def test_concise_description_prioritises_identity_and_visible_details():
    analysis = SimpleNamespace(
        description="x" * 500,
        product_type="short-sleeve V-neck T-shirt",
        colours="light blue",
        features=["V-neck neckline", "short sleeves", "straight hem"],
        materials="lightweight knit",
        category_details=SimpleNamespace(
            fit_and_silhouette="regular fit",
            hem_shape="straight hem",
            material_appearance="lightweight knit",
            surface_finish="matte",
        ),
        global_details=None,
    )
    result = concise_product_description(analysis)
    assert len(result) <= 320
    assert "light blue" in result.lower()
    assert "V-neck neckline" in result
    assert not result.endswith("T-shirt.") or result.endswith(".")
