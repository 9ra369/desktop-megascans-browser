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
    assert asset.meta["texelDensity"] == "4096 px/m"


def test_parse_manifest_does_not_keep_lod_distance_in_the_meta() -> None:
    # 設計: ポリゴン数、色空間、バリエーション、マップ種類、LODはDBに持たない
    assert "lodDistance" not in parse_manifest(load_manifest("wfypejzha")).meta


@pytest.mark.parametrize("key", ["scanner", "tileable", "calibration"])
def test_parse_manifest_does_not_keep_the_unused_surface_meta(key: str) -> None:
    # 設計: 閲覧の判断に使わないメタデータはDBに持たない
    assert key not in parse_manifest(load_manifest("wlrvaf3")).meta


# --------------------------------------------- semanticTags からの補足情報


def semantic(**tags: object) -> dict[str, object]:
    """``semanticTags`` だけ差し替えた最小の `{id}.json`。"""
    return {"id": "aaa", "name": "A", "categories": ["surface"], "semanticTags": tags}


def test_parse_manifest_takes_the_size_region_and_environment_from_semantic_tags() -> None:
    meta = parse_manifest(load_manifest("wfypejzha")).meta

    assert meta["size"] == "0.27〜1.1 m"
    assert meta["region"] == "Asia / Pakistan"
    assert meta["environment"] == ["rural", "urban", "forest biome"]


def test_parse_manifest_shows_one_size_when_the_two_bounds_match() -> None:
    assert parse_manifest(load_manifest("wlrvaf3")).meta["size"] == "2 m"


@pytest.mark.parametrize("key", ["size", "region", "environment"])
def test_parse_manifest_leaves_out_an_item_without_semantic_tags(key: str) -> None:
    assert key not in parse_manifest(semantic()).meta


def test_parse_manifest_leaves_out_the_environment_when_the_asset_has_none() -> None:
    # xiwcfassc の semanticTags には environment が無い。
    assert "environment" not in parse_manifest(load_manifest("xiwcfassc")).meta


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ({"minSize": 0.27, "maxSize": 1.1}, "0.27〜1.1 m"),
        ({"minSize": 0.27}, "0.27 m"),
        ({"maxSize": 1.1}, "1.1 m"),
        ({"minSize": 2, "maxSize": 2}, "2 m"),
        ({"minSize": 2.0, "maxSize": 4.0}, "2〜4 m"),
    ],
)
def test_parse_manifest_builds_the_size_from_the_bounds_it_has(
    tags: dict[str, object], expected: str
) -> None:
    assert parse_manifest(semantic(**tags)).meta["size"] == expected


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ({"region": "Asia", "country": "Pakistan"}, "Asia / Pakistan"),
        ({"region": "Asia"}, "Asia"),
        ({"country": "Pakistan"}, "Pakistan"),
    ],
)
def test_parse_manifest_builds_the_region_from_the_parts_it_has(
    tags: dict[str, object], expected: str
) -> None:
    assert parse_manifest(semantic(**tags)).meta["region"] == expected


def test_parse_manifest_ignores_the_top_level_environment() -> None:
    # 設計: トップレベルの environment は使わない。biome に "undefined" が入る。
    manifest = semantic()
    manifest["environment"] = {"biome": "undefined", "region": "Asia"}

    assert "environment" not in parse_manifest(manifest).meta


def test_parse_manifest_ignores_the_top_level_environment_even_with_a_biome() -> None:
    manifest = semantic()
    manifest["environment"] = {"biome": "urban", "region": "Americas"}

    assert "environment" not in parse_manifest(manifest).meta


@pytest.mark.parametrize(
    "tags",
    [
        {"minSize": "0.27", "maxSize": "1.1"},
        {"minSize": None, "maxSize": None},
        {"minSize": [], "maxSize": {}},
        {"minSize": True, "maxSize": False},
    ],
)
def test_parse_manifest_leaves_out_a_size_of_an_unexpected_type(tags: dict[str, object]) -> None:
    assert "size" not in parse_manifest(semantic(**tags)).meta


@pytest.mark.parametrize(
    "tags",
    [
        {"region": "", "country": "   "},
        {"region": 1, "country": ["Pakistan"]},
        {"region": None, "country": None},
        {"region": "undefined", "country": "undefined"},
    ],
)
def test_parse_manifest_leaves_out_a_region_of_an_unexpected_type(tags: dict[str, object]) -> None:
    assert "region" not in parse_manifest(semantic(**tags)).meta


@pytest.mark.parametrize(
    "tags",
    [
        {"environment": []},
        {"environment": ["", "  ", "undefined"]},
        {"environment": {"biome": "urban"}},
        {"environment": None},
        {"environment": 1},
    ],
)
def test_parse_manifest_leaves_out_an_environment_of_an_unexpected_type(
    tags: dict[str, object],
) -> None:
    assert "environment" not in parse_manifest(semantic(**tags)).meta


def test_parse_manifest_keeps_the_usable_parts_of_a_mixed_environment() -> None:
    meta = parse_manifest(semantic(environment=["rural", "", 1, "undefined", "urban"])).meta

    assert meta["environment"] == ["rural", "urban"]


def test_parse_manifest_survives_semantic_tags_of_an_unexpected_type() -> None:
    manifest = semantic()
    manifest["semanticTags"] = ["rural"]

    meta = parse_manifest(manifest).meta

    assert {"size", "region", "environment"}.isdisjoint(meta)


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ({"minSize": 0.27, "region": None, "environment": []}, {"size"}),
        ({"minSize": "x", "region": "Asia", "environment": None}, {"region"}),
        ({"minSize": None, "country": "", "environment": ["urban"]}, {"environment"}),
    ],
)
def test_parse_manifest_keeps_the_good_items_beside_the_broken_ones(
    tags: dict[str, object], expected: set[str]
) -> None:
    # 同期を止めず、壊れている項目だけを未設定にする。
    meta = parse_manifest(semantic(**tags)).meta

    assert {"size", "region", "environment"} & set(meta) == expected


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


def test_parse_manifest_does_not_keep_whether_a_billboard_exists() -> None:
    # 設計: 詳細パネルにはBillboardの有無とLODは表示しない
    assert "useBillboardMaterial" not in parse_manifest(load_manifest("wfypejzha")).meta


def test_parse_manifest_does_not_keep_per_variation_data() -> None:
    # 設計: バリエーションはDBに持たない。`dimensions` はバリエーション別の寸法。
    assert "dimensions" not in parse_manifest(load_manifest("wfypejzha")).meta


def test_parse_manifest_keeps_the_plain_meta_of_a_3d_asset() -> None:
    meta = parse_manifest(load_manifest("xiwcfassc")).meta

    assert meta["length"] == "1.5m"
    assert meta["texelDensity"] == "3 px/m"


def test_parse_manifest_does_not_keep_the_polygon_count() -> None:
    # 設計: ポリゴン数はDBに持たない。`points` がそれ。
    assert "points" not in parse_manifest(load_manifest("xiwcfassc")).meta
    assert "points" not in parse_manifest(load_manifest("wfypejzha")).meta


def test_parse_manifest_does_not_keep_submesh_splitting() -> None:
    assert "splitSubmeshes" not in parse_manifest(load_manifest("xiwcfassc")).meta


def test_parse_manifest_keeps_no_color_space_or_map_type() -> None:
    # 設計: 色空間、マップ種類はDBに持たない。
    for asset_id in ("wlrvaf3", "xiwcfassc", "wfypejzha"):
        meta = parse_manifest(load_manifest(asset_id)).meta
        assert not any("colorspace" in key.lower() for key in meta), asset_id
        assert "maps" not in meta
        assert "components" not in meta
