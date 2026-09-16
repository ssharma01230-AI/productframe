import re
from pathlib import Path

from productframe_api.generation_templates import list_generation_templates


REPO_ROOT = Path(__file__).parents[3]
FRONTEND_RECIPES = REPO_ROOT / "apps/web/app/studio/output-recipes.ts"
FAMILIES = ("shirts", "t-shirts-casual-tops", "sleeveless-tops", "knitwear", "hoodies")


def _key(match: tuple[str, ...]) -> str:
    return match[0] or match[1]


def _frontend_family_counts(source: str) -> dict[str, int]:
    block = source.split("const TOPS_FAMILY_EXAMPLES", 1)[1].split("// Evidence is explicit", 1)[0]
    counts: dict[str, int] = {}
    for match in re.finditer(
        r"(?:'([^']+)'|([A-Za-z][\w-]*)):\s*Array\.from\(\{\s*length:\s*(\d+)",
        block,
    ):
        counts[_key(match.groups())] = int(match.group(3))
    # Explicit arrays or numeric-map arrays are allowed for families whose
    # visual order is not a simple generated filename sequence.
    tshirt = re.search(r"'t-shirts-casual-tops':\s*\(\[([^\]]+)\].*?\)\.map", block, re.DOTALL)
    if tshirt:
        counts['t-shirts-casual-tops'] = len(re.findall(r'\d+', tshirt.group(1)))
    explicit = re.search(r"'sleeveless-tops':\s*\[(.*?)\n\s*\],", block, re.DOTALL)
    assert explicit is not None
    counts["sleeveless-tops"] = len(re.findall(r"/output-examples/tops/sleeveless/", explicit.group(1)))
    return counts


def _frontend_evidence(source: str) -> dict[str, tuple[str, ...]]:
    block = source.split("const TOPS_FAMILY_EVIDENCE", 1)[1].split("function topsTemplateEvidence", 1)[0]
    matches = re.findall(r"(?:'([^']+)'|([A-Za-z][\w-]*)):\s*\[([^\]]*)\]", block)
    return {
        _key(match): tuple(re.findall(r"'([^']+)'", match[2]))
        for match in matches
    }


def test_tops_frontend_and_backend_template_ids_and_evidence_match():
    source = FRONTEND_RECIPES.read_text()
    counts = _frontend_family_counts(source)
    evidence = _frontend_evidence(source)

    assert set(counts) == set(FAMILIES)
    assert set(evidence) == set(FAMILIES)

    for family in FAMILIES:
        backend = list_generation_templates(
            category="tops", channel="ecommerce", product_family=family,
        )
        assert len(backend) == counts[family]
        expected_numbers = [1, 2, 3, 4, 5, 6, 8, 9, 10] if family == 't-shirts-casual-tops' else list(range(1, counts[family] + 1))
        assert [template.id for template in backend] == [
            f"ecommerce-tops-{family}-{index:02d}" for index in expected_numbers
        ]
        assert tuple(template.required_evidence[0] for template in backend) == evidence[family]

    # Presentation names and contracts must not drift between the UI and the
    # backend registry for the corrected benchmark cases.
    assert "Front Headless Mannequin" in source
    shirts = list_generation_templates(category="tops", channel="ecommerce", product_family="shirts")
    assert shirts[2].presentation_mode == "garment"
    assert shirts[5].presentation_mode == "model"
    assert shirts[7].presentation_mode == "invisible_mannequin"
    assert shirts[12].required_evidence == ("rear_view",)
    assert shirts[13].required_evidence == ("rear_view",)
    sleeveless = list_generation_templates(category="tops", channel="ecommerce", product_family="sleeveless-tops")
    assert sleeveless[2].presentation_mode == "invisible_mannequin"
    assert sleeveless[3].presentation_mode == "mannequin"


def test_hoodie_templates_have_reviewed_details_modes_and_local_benchmarks():
    templates = list_generation_templates(
        category="tops", channel="ecommerce", product_family="hoodies",
    )
    assert [template.presentation_mode for template in templates] == [
        "garment", "invisible_mannequin", "invisible_mannequin", "invisible_mannequin",
        "model", "model", "model", "model", "model", "model", "model", "model",
    ]
    assert all(template.output_details for template in templates)
    assert all(
        template.reference_object_key
        and (REPO_ROOT / template.reference_object_key).is_file()
        for template in templates
    )


def test_knitwear_templates_have_reviewed_details_modes_and_local_benchmarks():
    templates = list_generation_templates(
        category="tops", channel="ecommerce", product_family="knitwear",
    )
    assert [template.presentation_mode for template in templates] == [
        "garment", "garment", "model", "model", "model", "garment",
        "model", "garment", "invisible_mannequin", "invisible_mannequin", "model",
    ]
    assert all(template.output_details for template in templates)
    assert all(
        template.reference_object_key
        and (REPO_ROOT / template.reference_object_key).is_file()
        for template in templates
    )


def test_sleeveless_templates_have_reviewed_details_modes_and_local_benchmarks():
    templates = list_generation_templates(
        category="tops", channel="ecommerce", product_family="sleeveless-tops",
    )
    assert [template.presentation_mode for template in templates] == [
        "model", "model", "invisible_mannequin", "mannequin", "garment", "model",
    ]
    assert all(template.output_details for template in templates)
    assert all(
        template.reference_object_key
        and (REPO_ROOT / template.reference_object_key).is_file()
        for template in templates
    )


def test_tshirt_templates_have_reviewed_details_modes_and_local_benchmarks():
    templates = list_generation_templates(
        category="tops", channel="ecommerce", product_family="t-shirts-casual-tops",
    )
    expected_modes = [
        "garment", "model", "garment", "model", "invisible_mannequin",
        "model", "invisible_mannequin", "garment", "invisible_mannequin",
    ]
    assert [template.presentation_mode for template in templates] == expected_modes
    assert all(template.output_details for template in templates)
    assert all(
        template.reference_object_key
        and (REPO_ROOT / template.reference_object_key).is_file()
        for template in templates
    )
