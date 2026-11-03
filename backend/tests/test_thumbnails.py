from io import BytesIO
from pathlib import Path

from PIL import Image

from downloaded import preview_png, write_file
from megascans_browser.core.thumbnails import THUMBNAIL_SIZE, make_thumbnail


def test_make_thumbnail_returns_a_png(tmp_path: Path) -> None:
    path = tmp_path / "wlrvaf3_Preview.png"
    write_file(path, preview_png())

    image = Image.open(BytesIO(make_thumbnail(path)))

    assert image.format == "PNG"


def test_make_thumbnail_fits_inside_the_box(tmp_path: Path) -> None:
    path = tmp_path / "wlrvaf3_Preview.png"
    write_file(path, preview_png())

    image = Image.open(BytesIO(make_thumbnail(path)))

    assert max(image.size) == THUMBNAIL_SIZE
    assert image.size == (THUMBNAIL_SIZE, round(THUMBNAIL_SIZE * 400 / 600))


def test_make_thumbnail_does_not_enlarge_a_small_preview(tmp_path: Path) -> None:
    path = tmp_path / "small_Preview.png"
    buffer = BytesIO()
    Image.new("RGB", (40, 20), (1, 2, 3)).save(buffer, format="PNG")
    write_file(path, buffer.getvalue())

    assert Image.open(BytesIO(make_thumbnail(path))).size == (40, 20)


def test_make_thumbnail_returns_none_for_a_missing_file(tmp_path: Path) -> None:
    assert make_thumbnail(tmp_path / "missing.png") is None


def test_make_thumbnail_returns_none_for_a_broken_file(tmp_path: Path) -> None:
    path = tmp_path / "broken_Preview.png"
    write_file(path, b"not an image")

    assert make_thumbnail(path) is None


def test_make_thumbnail_does_not_touch_the_source(tmp_path: Path) -> None:
    path = tmp_path / "wlrvaf3_Preview.png"
    original = preview_png()
    write_file(path, original)

    make_thumbnail(path)

    assert path.read_bytes() == original
