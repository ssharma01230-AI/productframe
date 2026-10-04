"""Run the new structured tie prompts against all active tie templates."""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "docs/ties-output-details/references"
DEFAULT_MODEL = "gpt-image-2.5-sunburst"
TEMPLATE_IDS = [f"ecommerce-accessories-ties-{index:02d}" for index in range(1, 8)]


def env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"").strip("'")
    return values


def product_facts(analysis: dict[str, object]) -> str:
    colours = analysis.get("colour_details") or {}
    global_details = analysis.get("global_details") or {}
    materials = global_details.get("materials") or {}
    construction = global_details.get("construction") or {}
    category = analysis.get("category_details") or {}
    gender = global_details.get("gender") or {}
    return f"""PRODUCT FACTS

Identity:
- Category: {analysis.get('category')}
- Family: {analysis.get('product_family')}
- Subtype: {category.get('subtype')}
- Product type: {analysis.get('product_type')}
- Visual signature: {analysis.get('description')}

Colour:
- Primary colour: {colours.get('primary_colour')}
- Secondary colours: {', '.join(colours.get('secondary_colours') or [])}
- Pattern: {colours.get('pattern')}
- Distribution: {colours.get('colour_distribution')}
- Finish: {colours.get('colour_finish')}
- Tonal variation: {colours.get('tonal_variation')}

Material:
- Appearance: {materials.get('appearance')}
- Texture: {materials.get('texture')}
- Weight and thickness: {materials.get('weight')}; {materials.get('thickness')}
- Finish: {materials.get('finish')}
- Stretch or flexibility: {materials.get('stretch_or_flexibility')}
- Drape: {materials.get('drape_or_rigidity')}

Construction:
- Silhouette: {construction.get('silhouette')}
- Shape: {construction.get('shape')}
- Proportions: {construction.get('proportions')}
- Visible construction: {'; '.join(construction.get('construction_details') or [])}
- Functional details: {'; '.join(construction.get('functional_details') or []) or 'none visible'}
- Category details: {category.get('shape')}; {category.get('length_and_width')}; {category.get('edge_finish')}

Artwork and branding:
- Pattern/artwork: {category.get('pattern_or_print')}
- Branding: {', '.join(category.get('visible_branding') or []) or 'not visible'}
- Gender presentation: {gender.get('user_confirmed') or gender.get('assumed')}

Evidence and uncertainty:
- Supported source view: front product view
- Unknown details: {', '.join(category.get('visible_uncertainties') or []) or 'none recorded'}
""".strip()


def template_sections(template_id: str, template) -> tuple[str, str]:
    details = template.prompt_instructions.replace("Create the requested ecommerce presentation of the uploaded tie. ", "")
    output = template.output_details
    composition = f"""COMPOSITION LOCK

Match the template reference exactly.

{output}

The template reference controls composition only. Preserve its camera angle,
crop, framing, lighting, background, surrounding clothing, and product position.
The uploaded product reference controls the tie’s identity and visible details.
If the references conflict, the uploaded product reference controls product identity.
"""
    positive = f"""PRESENTATION

{details}

{composition}

REPLACEMENT TASK

Replace the template tie or tie arrangement with the uploaded tie.
Preserve the uploaded tie’s authentic colour, pattern, motif scale, density,
material, proportions, blade and tail widths, tip shape, edges, and visible construction.
Do not transfer any template-specific product identity to the uploaded tie.

UNCERTAINTY POLICY

Details hidden by the knot, fold, roll, crop, or surrounding clothing remain unknown.
Do not invent them.
"""
    negative = template.negative_prompt + " Match the template reference exactly for composition; do not alter its crop, camera, framing, lighting, background, or surrounding presentation. Do not copy the template tie’s identity, colour, pattern, material, texture, construction, proportions, or branding. Do not reinterpret, enlarge, simplify, sparsify, stylise, recolour, or redesign the uploaded tie. Do not invent hidden details."
    return positive.strip(), negative.strip()


def compile_prompt(analysis: dict[str, object], template) -> tuple[str, str]:
    presentation, negative = template_sections(template.id, template)
    prompt = f"""TASK

Create one square 1:1 ecommerce image by performing a precise image edit.

IMAGE ROLES

- TEMPLATE REFERENCE controls composition, camera, crop, framing, lighting, background, and presentation structure.
- PRODUCT REFERENCE controls the uploaded tie’s identity, colour, pattern, material, proportions, construction, and branding.
- The template reference must not influence the uploaded tie’s identity or pattern.

PRODUCT AUTHORITY

The uploaded product reference is the sole authority for the tie’s identity.
Preserve every clearly visible product feature on its original surface.

{product_facts(analysis)}

PRODUCT FIDELITY

Copy the uploaded tie’s visible pattern literally as a textile pattern.
Preserve motif geometry, scale, density, spacing, colour, orientation,
weave, sheen, edges, proportions, and continuity across visible surfaces.
Do not interpret the pattern semantically or replace it with a category default.

{presentation}

STRICT EXCLUSIONS

Do not add unsupported products, duplicate ties, unrelated accessories,
props, text, labels, watermarks, collages, insets, split screens, or multiple views.
"""
    return prompt.strip(), negative


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-image", type=Path, required=True)
    parser.add_argument("--recognition", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    from productframe_api.generation_templates import get_generation_template

    worker_env = env_file(ROOT / "services/worker/.env")
    api_key = worker_env.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    model = worker_env.get("OPENAI_IMAGE_MODEL", DEFAULT_MODEL)
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required")
    result = json.loads(args.recognition.read_text())
    analysis = result["analysis"]
    args.output_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(args.product_image, args.output_dir / "product-reference.png")
    shutil.copy2(args.recognition, args.output_dir / "recognition.json")
    product_bytes = args.product_image.read_bytes()
    client = OpenAI(api_key=api_key, max_retries=0)
    manifest = {"model": model, "size": "1024x1024", "quality": "high", "product_reference": str(args.product_image), "tests": []}
    for template_id in TEMPLATE_IDS:
        template = get_generation_template(template_id)
        if template is None or not template.reference_object_key:
            raise SystemExit(f"Missing template reference: {template_id}")
        template_path = ROOT / template.reference_object_key
        prompt, negative = compile_prompt(analysis, template)
        case_dir = args.output_dir / template_id
        case_dir.mkdir()
        shutil.copy2(template_path, case_dir / "template-reference.png")
        (case_dir / "prompt.txt").write_text(prompt + "\n")
        (case_dir / "negative-prompt.txt").write_text(negative + "\n")
        response = client.images.edit(
            model=model,
            image=[
                ("product-reference.png", product_bytes, "image/png"),
                ("template-reference.png", template_path.read_bytes(), "image/png"),
            ],
            prompt=prompt + "\n\nNegative prompt:\n" + negative,
            size="1024x1024",
            quality="high",
        )
        output = case_dir / "output.png"
        output.write_bytes(base64.b64decode(response.data[0].b64_json, validate=True))
        case_manifest = {"template_id": template_id, "name": template.name, "model": model, "size": "1024x1024", "quality": "high", "template_reference": str(template_path), "output": str(output)}
        (case_dir / "manifest.json").write_text(json.dumps(case_manifest, indent=2))
        manifest["tests"].append(case_manifest)
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(args.output_dir)


if __name__ == "__main__":
    main()
