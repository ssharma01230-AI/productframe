"""Isolated A/B experiment: Shirts text-only vs template-reference generation.

This script deliberately does not create API jobs or modify production prompt
compilation. It reads one existing product and writes experiment outputs locally.
Run from the repository root with the worker virtualenv and API source path.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import boto3
import psycopg
from openai import OpenAI

from productframe_api.generation_prompts import GenerationRequest, ProductContext, ReferenceImage, build_generation_prompt
from productframe_worker.openai_image_provider import DEFAULT_IMAGE_MODEL

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_FILES = {
    "ecommerce-tops-shirts-06": ROOT / "apps/web/public/output-examples/tops/shirts/shirts-ecom-07-detail-barrel-cuff.png",
    "ecommerce-tops-shirts-07": ROOT / "apps/web/public/output-examples/tops/shirts/shirts-ecom-08-detail-poplin-fabric-fold.png",
    "ecommerce-tops-shirts-12": ROOT / "apps/web/public/output-examples/tops/shirts/shirts-ecom-13-side-three-quarter-product.png",
}
EXPERIMENT_INSTRUCTION = (
    "This is a strict image replacement and editing task, not a new creative fashion generation. "
    "Use the template reference as a locked visual layout: preserve its camera angle, framing, "
    "pose, product position, scale, lighting and background. Completely remove and discard the "
    "template garment's identity, then replace it with the exact shirt shown in the product "
    "reference image. The final image must be recognisably the uploaded Blue slim fit shirt, "
    "not a redesigned or reinterpreted version. Transfer only the presentation layout; never "
    "transfer the template garment's colour, material, texture, collar, cuffs, buttons, pockets, "
    "seams, artwork, branding, proportions or any other product-specific detail. Do not invent "
    "or optimise any product feature."
)


def remove_confidence_section(prompt: str) -> str:
    """Keep confidence metadata internal to the compiler, not model-facing."""
    start = prompt.find("CONFIDENCE AND UNCERTAINTY")
    end = prompt.find("PRODUCT FIDELITY PRESERVATION")
    if start >= 0 and end > start:
        return prompt[:start] + prompt[end:]
    return prompt


def env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"')
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-id", default="c672ffee-fbbc-4be0-b3fe-cb811542cff2")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/results/shirts-template-reference-ab/test 2")
    args = parser.parse_args()
    api_env = env_file(ROOT / "services/api/.env")
    worker_env = env_file(ROOT / "services/worker/.env")
    database_url = api_env["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("select name,category,product_type,colours,materials,features,description,global_details,category_details,confidence_details from products where id=%s", (args.product_id,))
        row = cursor.fetchone()
        cursor.execute("select object_key,id from source_assets where product_id=%s order by created_at limit 1", (args.product_id,))
        source = cursor.fetchone()
    if not row or not source:
        raise SystemExit("Product or source image not found")
    fields = ["name", "category", "product_type", "colours", "materials", "features", "description", "global_details", "category_details", "confidence_details"]
    product = dict(zip(fields, row))
    context = ProductContext(**product, presentation="male")
    request = GenerationRequest(
        template_id="ecommerce-tops-shirts-06", channel="ecommerce", product=context,
        product_reference_images=(ReferenceImage(role="product_reference", object_key=source[0], asset_id=str(source[1])),),
    )
    s3 = boto3.client(
        "s3", endpoint_url=worker_env.get("MINIO_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=worker_env.get("MINIO_ACCESS_KEY", "productframe"),
        aws_secret_access_key=worker_env.get("MINIO_SECRET_KEY", "productframe-local-password"),
        region_name="us-east-1",
    )
    product_bytes = s3.get_object(Bucket=worker_env.get("MINIO_BUCKET", "productframe-local"), Key=source[0])["Body"].read()
    client = OpenAI(api_key=worker_env["OPENAI_API_KEY"])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"product_id": args.product_id, "product": product, "model": worker_env.get("OPENAI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL), "jobs": []}
    for template_id, template_path in TEMPLATE_FILES.items():
        request = GenerationRequest(template_id=template_id, channel="ecommerce", product=context, product_reference_images=request.product_reference_images)
        compiled = build_generation_prompt(request)
        base_prompt = remove_confidence_section(compiled.prompt)
        template_bytes = template_path.read_bytes()
        for variant, prompt, images in (
            ("text-only", base_prompt, [("product_reference.jpg", product_bytes, "image/jpeg")]),
            ("template-reference", EXPERIMENT_INSTRUCTION + "\n\n" + base_prompt, [("product_reference.jpg", product_bytes, "image/jpeg"), ("template_reference.png", template_bytes, "image/png")]),
        ):
            response = client.images.edit(model=manifest["model"], image=images, prompt=prompt + "\n\nNegative prompt:\n" + compiled.negative_prompt, size="1024x1024", quality="medium")
            image = response.data[0]
            output = args.output_dir / f"{template_id}-{variant}.png"
            output.write_bytes(__import__("base64").b64decode(image.b64_json))
            (args.output_dir / f"{template_id}-{variant}.prompt.txt").write_text(prompt)
            manifest["jobs"].append({"template_id": template_id, "variant": variant, "output": str(output), "template_reference": str(template_path) if variant == "template-reference" else None})
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    print(f"Wrote {len(manifest['jobs'])} outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
