from types import SimpleNamespace

from productframe_api.description_utils import concise_product_description


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
    assert "light blue" in result
    assert "V-neck neckline" in result
    assert not result.endswith("T-shirt.") or result.endswith(".")
