from pathlib import Path

from productframe_api.category_registry import get_footwear_family_for_subtype
from productframe_api.generation_templates import list_generation_templates

ROOT = Path(__file__).resolve().parents[3]


def test_footwear_subtypes_route_to_three_controlled_families():
    assert get_footwear_family_for_subtype("white low-top sneaker") == "shoes"
    assert get_footwear_family_for_subtype("leather ankle boot") == "boots"
    assert get_footwear_family_for_subtype("suede loafer") == "shoes"
    assert get_footwear_family_for_subtype("heeled sandal") == "heels"


def test_shoes_have_the_shared_reviewed_pack():
    shoes = list_generation_templates(category="footwear", channel="ecommerce", product_family="shoes")
    assert len(shoes) == 17
    assert all(t.applicable_families == ("shoes",) for t in shoes)
    assert all(t.presentation_mode and t.output_details and t.reference_object_key for t in shoes)
    assert all((ROOT / t.reference_object_key).is_file() for t in shoes)
