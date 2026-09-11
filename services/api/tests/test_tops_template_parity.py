import re
from pathlib import Path

from productframe_api.generation_templates import list_generation_templates


FRONTEND_RECIPES = Path(__file__).parents[3] / "apps/web/app/studio/output-recipes.ts"
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
    # Explicit arrays are allowed for a family whose visual order is not a
    # simple generated filename sequence.
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
        assert [template.id for template in backend] == [
            f"ecommerce-tops-{family}-{index:02d}"
            for index in range(1, counts[family] + 1)
        ]
        assert tuple(template.required_evidence[0] for template in backend) == evidence[family]
