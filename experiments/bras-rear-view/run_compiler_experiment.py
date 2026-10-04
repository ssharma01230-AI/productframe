from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
import psycopg
from openai import OpenAI

from productframe_api.generation_prompts import (
    GenerationRequest,
    ProductContext,
    ReferenceImage,
    build_generation_prompt,
)

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRODUCT_NAME = os.environ.get("EXPERIMENT_PRODUCT_NAME", "Navy lace bralette")
TEMPLATE_ID = "ecommerce-underwear-bra-08"
TEMPLATE_PATH = ROOT / "docs/bras-output-details/references/08_rear_model.png"


def env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_product(api_env: dict[str, str]) -> tuple[dict[str, object], dict[str, str]]:
    database_url = api_env["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "select id,name,category,product_type,colours,materials,features,description,global_details,category_details,confidence_details "
            "from products where name=%s order by created_at desc limit 1",
            (PRODUCT_NAME,),
        )
        row = cursor.fetchone()
        cursor.execute(
            "select id,object_key from source_assets where product_id=%s order by created_at,id limit 1",
            (row[0],) if row else (None,),
        )
        source = cursor.fetchone()
    if not row or not source:
        raise SystemExit("Navy lace bralette product or source image was not found")
    fields = ["id", "name", "category", "product_type", "colours", "materials", "features", "description", "global_details", "category_details", "confidence_details"]
    product = dict(zip(fields, row))
    return product, {"id": str(source[0]), "object_key": source[1]}


def make_request(product: dict[str, object], source: dict[str, str], template_id: str = TEMPLATE_ID, include_template: bool = True) -> tuple[GenerationRequest, object]:
    from productframe_api.generation_templates import get_generation_template

    template = get_generation_template(template_id)
    if template is None or not template.reference_object_key:
        raise SystemExit(f"Template/reference is unavailable: {TEMPLATE_ID}")
    context = ProductContext(
        name=product["name"], category=product["category"], product_type=product["product_type"],
        colours=product["colours"], materials=product["materials"], features=tuple(product["features"]),
        description=product["description"], colour_details=(product["global_details"] or {}).get("colour"),
        global_details=product["global_details"], category_details=product["category_details"],
        confidence_details=product["confidence_details"], presentation="female",
    )
    request = GenerationRequest(
        template_id=template_id, channel="ecommerce", product=context,
        product_reference_images=(ReferenceImage("product_reference", source["object_key"], source["id"]),),
        template_reference_images=(ReferenceImage("template_reference", template.reference_object_key),) if include_template else (),
    )
    return request, template


def minio_image(worker_env: dict[str, str], key: str) -> bytes:
    client = boto3.client(
        "s3", endpoint_url=worker_env.get("MINIO_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=worker_env.get("MINIO_ACCESS_KEY", "productframe"),
        aws_secret_access_key=worker_env.get("MINIO_SECRET_KEY", "productframe-local-password"),
        region_name="us-east-1",
    )
    response = client.get_object(Bucket=worker_env.get("MINIO_BUCKET", "productframe-local"), Key=key)
    return response["Body"].read()


def initialise() -> None:
    api_env = env_file(ROOT / "services/api/.env")
    product, source = load_product(api_env)
    request, template = make_request(product, source)
    compiled = build_generation_prompt(request)
    (HERE / "input.prompt.txt").write_text(compiled.prompt)
    (HERE / "negative.prompt.txt").write_text(compiled.negative_prompt)
    (HERE / "product.snapshot.json").write_text(json.dumps(product, indent=2, default=str))
    (HERE / "references.json").write_text(json.dumps({
        "product": source, "template": {"role": "template_reference", "path": template.reference_object_key},
    }, indent=2))
    print("Initialised test environment without calling an image provider.")


def run(provider: str, template_id: str, include_template: bool = True, template_image: Path | None = None, product_image: Path | None = None) -> None:
    api_env = env_file(ROOT / "services/api/.env")
    worker_env = env_file(ROOT / "services/worker/.env")
    product, source = load_product(api_env)
    request, template = make_request(product, source, template_id, include_template)
    prompt = (HERE / "input.prompt.txt").read_text()
    negative = (HERE / "negative.prompt.txt").read_text()
    product_bytes = product_image.read_bytes() if product_image else minio_image(worker_env, source["object_key"])
    template_bytes = (template_image or (ROOT / template.reference_object_key)).read_bytes() if include_template else None
    full_prompt = prompt + "\n\nNegative prompt:\n" + negative
    if provider == "gemini":
        import httpx
        parts = [
            {"text": full_prompt},
            {"text": "Product reference:"}, {"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(product_bytes).decode()}},
            *([] if template_bytes is None else [{"text": "Template reference:"}, {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(template_bytes).decode()}}]),
        ]
        model = os.environ.get("GEMINI_IMAGE_MODEL", worker_env.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-lite-image"))
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": os.environ.get("GEMINI_API_KEY", worker_env["GEMINI_API_KEY"]), "Content-Type": "application/json"},
            json={"contents": [{"role": "user", "parts": parts}], "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1"}}},
            timeout=300,
        )
        if not response.is_success:
            raise RuntimeError(f"Gemini HTTP {response.status_code}: {response.text[:2000]}")
        payload = response.json()
        image_part = next(part for part in payload["candidates"][0]["content"]["parts"] if part.get("inlineData"))
        image_bytes = base64.b64decode(image_part["inlineData"]["data"], validate=True)
        request_id = response.headers.get("x-request-id") or response.headers.get("x-goog-request-id")
        settings = {"aspect_ratio": "1:1"}
    else:
        model = worker_env.get("OPENAI_IMAGE_MODEL", "gpt-image-2.5-sunburst")
        response = OpenAI(api_key=worker_env["OPENAI_API_KEY"], max_retries=0).images.edit(
            model=model,
            image=[("product_reference.jpeg" if product_image else "product_reference.jpg", product_bytes, "image/jpeg")] + ([] if template_bytes is None else [("template_reference.png", template_bytes, "image/png")]),
            prompt=full_prompt, size="1024x1024", quality="high",
        )
        image_bytes = base64.b64decode(response.data[0].b64_json, validate=True)
        request_id = getattr(response, "_request_id", None)
        settings = {"size": "1024x1024", "quality": "high"}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = HERE / "results" / f"{stamp}-{provider}-{template_id.split('-')[-1]}"
    output_dir.mkdir(parents=True)
    output = output_dir / f"{template_id}.png"
    output.write_bytes(image_bytes)
    manifest = {
        "product": product, "template_id": template_id, "provider": provider, "model": model,
        "settings": settings,
        "references": {"product": str(product_image or source["object_key"]), "template": str(template_image or (ROOT / template.reference_object_key)) if include_template else None},
        "prompt_file": str(HERE / "input.prompt.txt"), "negative_prompt_file": str(HERE / "negative.prompt.txt"),
        "provider_request_id": request_id, "output": str(output),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    (output_dir / "prompt.txt").write_text(prompt + "\n\nNegative prompt:\n" + negative)
    print(f"Wrote {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--provider", choices=("openai", "gemini"), default="openai")
    parser.add_argument("--template-id", default=TEMPLATE_ID)
    parser.add_argument("--no-template", action="store_true")
    parser.add_argument("--template-image", type=Path)
    parser.add_argument("--product-image", type=Path)
    args = parser.parse_args()
    if args.init == args.run:
        parser.error("choose exactly one of --init or --run")
    initialise() if args.init else run(args.provider, args.template_id, not args.no_template, args.template_image, args.product_image)
