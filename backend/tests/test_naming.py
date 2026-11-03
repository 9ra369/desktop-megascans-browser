import pytest

from helpers import catalog_entries
from megascans_browser.core import naming


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("wlrvaf3_8K_Normal.exr", "8K"),
        ("wlrvaf3_1K_AO.jpg", "1K"),
        ("Textures/Atlas/wfypejzha_4K_Albedo.jpg", "4K"),
        ("Textures/Billboard/Billboard_8K_AO.exr", "8K"),
        ("xiwcfassc_8K_Normal_LOD0.exr", "8K"),
        ("xiwcfassc_16K_Albedo.jpg", "16K"),
        ("wlrvaf3_8K.exr", "8K"),
        ("xiwcfassc_High.fbx", None),
        ("Var1/Var1_LOD0.abc", None),
        ("wlrvaf3_Preview.png", None),
        ("wlrvaf3_Grid_360.png", None),
        ("wlrvaf3.json", None),
    ],
)
def test_parse_resolution(path: str, expected: str | None) -> None:
    assert naming.parse_resolution(path) == expected


def test_parse_resolution_matches_the_catalog_for_every_file(manifest: dict) -> None:
    entries = catalog_entries(manifest)
    assert entries, "カタログが空"

    for entry in entries:
        parsed = naming.parse_resolution(entry["uri"])
        if entry["resolution"] is None:
            # メッシュなど解像度を持たないファイル
            continue
        width = int(entry["resolution"].split("x")[0])
        assert parsed == f"{width // 1024}K", entry["uri"]


def test_catalog_file_counts_match_the_design(manifest: dict) -> None:
    expected = {"wlrvaf3": 72, "xiwcfassc": 143, "wfypejzha": 234}
    assert len(catalog_entries(manifest)) == expected[manifest["id"]]


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("Textures/Billboard/Billboard_8K_AO.exr", True),
        ("Textures/billboard/Billboard_8K_AO.exr", True),
        ("Textures/Atlas/wfypejzha_4K_Albedo.jpg", False),
        ("wlrvaf3_8K_Normal.exr", False),
    ],
)
def test_is_billboard(path: str, expected: bool) -> None:
    assert naming.is_billboard(path) is expected


@pytest.mark.parametrize(
    ("folder_name", "expected"),
    [
        ("Concrete Pavement_wlrvaf3", "wlrvaf3"),
        ("Industrial Junkyard Storage Pallet Wood Tarp_xiwcfassc", "xiwcfassc"),
        ("Dragon Tree_wfypejzha", "wfypejzha"),
        ("NoSeparator", None),
        ("Trailing_", None),
        ("", None),
    ],
)
def test_asset_id_from_folder_name(folder_name: str, expected: str | None) -> None:
    assert naming.asset_id_from_folder_name(folder_name) == expected


def test_collect_resolutions_sorts_ascending_and_drops_billboard() -> None:
    paths = [
        "Textures/Atlas/wfypejzha_4K_AO.jpg",
        "Textures/Atlas/wfypejzha_1K_AO.jpg",
        "Textures/Atlas/wfypejzha_2K_AO.jpg",
        "Textures/Billboard/Billboard_8K_AO.exr",
        "Var1/Var1_LOD0.fbx",
    ]
    assert naming.collect_resolutions(paths) == ["1K", "2K", "4K"]


def test_collect_resolutions_is_empty_without_textures() -> None:
    assert naming.collect_resolutions(["xiwcfassc_High.fbx"]) == []


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Thumbs.db", True), ("desktop.ini", True), ("DESKTOP.INI", True), ("a.jpg", False)],
)
def test_is_ignored_file(name: str, expected: bool) -> None:
    assert naming.is_ignored_file(name) is expected


def test_asset_types_are_the_three_scanned_roots() -> None:
    assert naming.ASSET_TYPES == ("3d", "3dplant", "surface")
