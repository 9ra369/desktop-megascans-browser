import pytest

from helpers import load_manifest
from megascans_browser.core.manifest import category_paths, parse_manifest, search_text_for


@pytest.mark.parametrize(
    ("asset_id", "asset_type", "name"),
    [
        ("wlrvaf3", "surface", "Concrete Pavement"),
        ("xiwcfassc", "3d", "Industrial Junkyard Storage Pallet Wood Tarp"),
        ("wfypejzha", "3dplant", "Dragon Tree"),
    ],
)
def test_parse_manifest_takes_the_type_from_the_first_category(
    asset_id: str, asset_type: str, name: str
) -> None:
    asset = parse_manifest(load_manifest(asset_id))

    assert asset.id == asset_id
    assert asset.type == asset_type
    assert asset.name == name


def test_parse_manifest_keeps_the_average_color() -> None:
    assert parse_manifest(load_manifest("xiwcfassc")).average_color == "#564E40"


def test_parse_manifest_keeps_scan_area_in_the_meta() -> None:
    asset = parse_manifest(load_manifest("wlrvaf3"))

    assert asset.meta["scanArea"] == "2x2 m"
    assert asset.meta["tileable"] is True


def test_parse_manifest_does_not_keep_lod_distance_in_the_meta() -> None:
    # 設計: ポリゴン数、色空間、バリエーション、マップ種類、LODはDBに持たない
    assert "lodDistance" not in parse_manifest(load_manifest("wfypejzha")).meta


@pytest.mark.parametrize(
    ("asset_id", "expected"),
    [
        ("wlrvaf3", ["surface", "surface/concrete", "surface/concrete/rough"]),
        ("xiwcfassc", ["3d", "3d/industrial", "3d/industrial/storage"]),
        ("wfypejzha", ["3dplant", "3dplant/houseplant", "3dplant/houseplant/flowerless"]),
    ],
)
def test_category_paths_include_every_parent_level(asset_id: str, expected: list[str]) -> None:
    assert category_paths(load_manifest(asset_id)["assetCategories"]) == expected


def test_category_paths_rename_the_roots() -> None:
    assert category_paths({"3D asset": {}}) == ["3d"]
    assert category_paths({"3D plant": {}}) == ["3dplant"]
    assert category_paths({"surface": {}}) == ["surface"]


def test_category_paths_cover_every_branch() -> None:
    tree = {"3D asset": {"nature": {"rock": {}, "plant": {}}, "industrial": {}}}

    assert category_paths(tree) == [
        "3d",
        "3d/industrial",
        "3d/nature",
        "3d/nature/plant",
        "3d/nature/rock",
    ]


def test_parse_manifest_uses_the_category_paths() -> None:
    assert parse_manifest(load_manifest("wlrvaf3")).category_paths == [
        "surface",
        "surface/concrete",
        "surface/concrete/rough",
    ]


@pytest.mark.parametrize(
    ("asset_id", "words"),
    [
        ("wlrvaf3", ["concrete", "pavement", "wlrvaf3", "surface", "rough", "urban", "americas"]),
        ("xiwcfassc", ["industrial", "junkyard", "tarp", "xiwcfassc", "3d", "sweden", "europe"]),
        ("wfypejzha", ["dragon", "tree", "wfypejzha", "3dplant", "dracaena", "marginata", "asia"]),
    ],
)
def test_search_text_contains_the_words_of_every_source_field(
    asset_id: str, words: list[str]
) -> None:
    text = search_text_for(load_manifest(asset_id))

    for word in words:
        assert word in text.split(), word


def test_search_text_is_lowercase_and_deduplicated() -> None:
    text = search_text_for(load_manifest("wlrvaf3"))
    tokens = text.split()

    assert text == text.lower()
    assert tokens == sorted(set(tokens))


def test_search_text_does_not_contain_field_names() -> None:
    text = search_text_for(load_manifest("wlrvaf3")).split()

    for field in ["semantictags", "assetcategories", "subject_matter", "biome", "maxsize"]:
        assert field not in text


def test_search_text_keeps_the_keys_of_the_location_taxonomy() -> None:
    text = search_text_for(load_manifest("xiwcfassc")).split()

    assert "sweden" in text
    assert "europe" in text
