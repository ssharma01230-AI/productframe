from pathlib import Path

from productframe_api.category_registry import get_outerwear_family_for_subtype
from productframe_api.generation_prompts import GenerationRequest, ProductContext, ReferenceImage, build_generation_prompt
from productframe_api.generation_templates import list_generation_templates


ROOT = Path(__file__).resolve().parents[3]


def test_outerwear_subtypes_route_to_their_controlled_families():
    assert get_outerwear_family_for_subtype("leather jacket with zip pockets") == "jackets"
    assert get_outerwear_family_for_subtype("long trench coat") == "coats"
    assert get_outerwear_family_for_subtype("hooded padded vest") == "gilets-padded-vests"


def test_jackets_and_coats_have_separate_reviewed_outerwear_packs():
    jackets = list_generation_templates(category="outerwear", channel="ecommerce", product_family="jackets")
    assert len(jackets) == 9
    assert all(template.applicable_families == ("jackets",) for template in jackets)
    assert all(template.presentation_mode for template in jackets)
    assert all(template.output_details for template in jackets)
    assert all(template.reference_object_key for template in jackets)
    assert all((ROOT / template.reference_object_key).is_file() for template in jackets)

    coats = list_generation_templates(category="outerwear", channel="ecommerce", product_family="coats")
    assert len(coats) == 11
    assert all(template.applicable_families == ("coats",) for template in coats)
    assert all(template.presentation_mode and template.output_details and template.reference_object_key for template in coats)
    assert all((ROOT / template.reference_object_key).is_file() for template in coats)
    gilets = list_generation_templates(category="outerwear", channel="ecommerce", product_family="gilets-padded-vests")
    assert len(gilets) == 10
    assert all(template.applicable_families == ("gilets-padded-vests",) for template in gilets)
    assert all(template.presentation_mode and template.output_details and template.reference_object_key for template in gilets)
    assert all((ROOT / template.reference_object_key).is_file() for template in gilets)


def test_jackets_prompt_compiles_with_product_then_benchmark_reference():
    result = build_generation_prompt(GenerationRequest(
        template_id="ecommerce-outerwear-front-model",
        channel="ecommerce",
        product=ProductContext(
            name="Leather jacket", category="outerwear", product_type="jacket",
            colours="Black", materials="Leather", features=("Zip closure",),
            description="A black leather jacket.",
            category_details={"family": "jackets", "subtype": "jacket"},
        ),
        product_reference_images=(ReferenceImage(role="product_reference", object_key="product.jpg"),),
        template_reference_images=(ReferenceImage(role="template_reference", object_key="template.png"),),
    ))
    assert result.reference_images[0].role == "product_reference"
    assert result.reference_images[1].role == "template_reference"
    assert "OUTPUT DETAILS" in result.prompt
    assert "PRESENTATION MODE" in result.prompt
    assert "Replace the template garment completely" in result.prompt
