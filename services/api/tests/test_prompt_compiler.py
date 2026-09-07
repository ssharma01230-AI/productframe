import pytest

from productframe_api.generation_prompts import (
    GenerationRequest,
    ProductContext,
    PromptCompilationError,
    ReferenceImage,
    compile_generation_prompt,
)


def request(**changes):
    product = ProductContext(
        name="Blue V-neck top",
        category="tops",
        product_type="Short-sleeve V-neck top",
        colours="Muted blue",
        materials="Smooth cotton jersey",
        features=("V-neck", "Short sleeves"),
        description="A muted blue short-sleeve V-neck top.",
        colour_details={"primary_colour": "Muted blue", "pattern": "Solid"},
        global_details={"materials": {"appearance": "Smooth jersey"}},
        category_details={
            "subtype": "t-shirt",
            "neckline_type": "V-neck",
            "sleeve_type": "set-in sleeves",
            "fit_and_silhouette": "Regular fit",
        },
        confidence_details={"colour": {"score": 0.95, "status": "clearly_visible", "uncertainties": []}},
    )
    values = {
        "template_id": "ecommerce-tops-front-view",
        "channel": "ecommerce",
        "product": product,
        "product_reference_images": (ReferenceImage(role="product_reference", object_key="product.webp"),),
    }
    values.update(changes)
    return GenerationRequest(**values)


def test_compiler_puts_product_identity_before_template_and_keeps_reference_only():
    compiled = compile_generation_prompt(request())

    assert compiled.prompt.index("PRODUCT IDENTITY") < compiled.prompt.index("TEMPLATE PRESENTATION")
    assert "V-neck" in compiled.prompt
    assert "white background" in compiled.prompt
    assert "template reference" not in compiled.prompt.lower()
    assert len(compiled.reference_images) == 1


def test_strict_compilation_rejects_missing_identity_fields():
    product = request().product
    incomplete = ProductContext(
        name=product.name,
        category=product.category,
        product_type=product.product_type,
        colours=product.colours,
        materials=product.materials,
        features=product.features,
        description=product.description,
    )

    with pytest.raises(PromptCompilationError, match="Missing required"):
        compile_generation_prompt(request(product=incomplete, strict=True))
