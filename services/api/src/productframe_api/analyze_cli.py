import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from .image_recognition import ImageRejectedError, analyze_product_image, analyze_product_images


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Analyse a ProductFrame product image")
    parser.add_argument("image", type=Path, nargs="+")
    args = parser.parse_args()
    if len(args.image) > 1:
        result = analyze_product_images([path.read_bytes() for path in args.image])
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        if not result.passed:
            raise SystemExit(2)
        return
    try:
        result = analyze_product_image(args.image[0].read_bytes())
    except ImageRejectedError as exc:
        print(json.dumps(exc.screening.model_dump(mode="json"), indent=2))
        raise SystemExit(2)
    print(json.dumps({"passed": True, "analysis": result.model_dump(mode="json")}, indent=2))


if __name__ == "__main__":
    main()
