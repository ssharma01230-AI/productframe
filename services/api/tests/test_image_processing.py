import io

from PIL import Image

from productframe_api.image_processing import normalize_image_orientation
from productframe_api.image_recognition import prescreen_image


def oriented_jpeg() -> bytes:
    image = Image.new("RGB", (40, 80), "red")
    exif = Image.Exif()
    exif[274] = 6
    output = io.BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return output.getvalue()


def test_normalize_image_orientation_applies_exif_and_removes_tag():
    normalized = normalize_image_orientation(oriented_jpeg())

    assert (normalized.width, normalized.height) == (80, 40)
    with Image.open(io.BytesIO(normalized.content)) as image:
        assert image.size == (80, 40)
        assert image.getexif().get(274) is None


def test_prescreen_reports_display_orientation_dimensions():
    result = prescreen_image(oriented_jpeg())

    assert (result.width, result.height) == (80, 40)


def test_normalize_image_orientation_applies_content_rotation_after_exif():
    image = Image.new("RGB", (30, 40), "red")
    for y in range(20, 40):
        for x in range(30):
            image.putpixel((x, y), (0, 0, 255))
    source = io.BytesIO()
    image.save(source, format="PNG")

    normalized = normalize_image_orientation(source.getvalue(), rotation_degrees=180)

    with Image.open(io.BytesIO(normalized.content)) as rotated:
        top = rotated.convert("RGB").getpixel((15, 5))
        bottom = rotated.convert("RGB").getpixel((15, 35))
    assert top[2] > top[0]
    assert bottom[0] > bottom[2]
