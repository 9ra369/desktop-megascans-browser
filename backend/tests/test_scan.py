from pathlib import Path

import pytest

from downloaded import make_asset, make_downloaded, write_file
from megascans_browser.core.scan import ScannedAsset, scan_downloaded


@pytest.fixture
def downloaded(tmp_path: Path) -> Path:
    return make_downloaded(tmp_path)


def by_id(assets: list[ScannedAsset]) -> dict[str, ScannedAsset]:
    return {asset.id: asset for asset in assets}


def test_scan_finds_every_asset(downloaded: Path) -> None:
    result = scan_downloaded(downloaded)

    assert sorted(by_id(result.assets)) == ["wfypejzha", "wlrvaf3", "xiwcfassc"]


def test_scan_skips_the_excluded_roots(downloaded: Path) -> None:
    result = scan_downloaded(downloaded)

    assert all("atlas" not in asset.rel_dir for asset in result.assets)
    assert all(asset.type in ("3d", "3dplant", "surface") for asset in result.assets)


def test_scan_records_the_relative_folder_with_forward_slashes(downloaded: Path) -> None:
    asset = by_id(scan_downloaded(downloaded).assets)["wlrvaf3"]

    assert asset.rel_dir == "surface/concrete_rough_wlrvaf3"
    assert asset.type == "surface"


def test_scan_records_the_manifest_path(downloaded: Path) -> None:
    asset = by_id(scan_downloaded(downloaded).assets)["wlrvaf3"]

    assert asset.manifest_path.name == "wlrvaf3.json"
    assert asset.manifest_path.is_file()


def test_scan_collects_the_files_below_the_asset_folder(downloaded: Path) -> None:
    asset = by_id(scan_downloaded(downloaded).assets)["wfypejzha"]
    paths = {file.rel_path for file in asset.files}

    assert "Var1/Var1_LOD0.fbx" in paths
    assert "Textures/Atlas/wfypejzha_4K_Albedo.jpg" in paths
    assert all("\\" not in path for path in paths)


def test_scan_reads_the_resolutions_from_the_real_files(downloaded: Path) -> None:
    assets = by_id(scan_downloaded(downloaded).assets)

    # 本体は4Kだけ。`Thumbs/` の1K/2K は数えない。
    assert assets["wlrvaf3"].resolutions == ["4K"]
    assert assets["xiwcfassc"].resolutions == ["4K"]


def test_scan_excludes_billboard_from_the_resolutions(downloaded: Path) -> None:
    # BillboardもAtlasも4K。`Thumbs/` の1K/2K は数えない。
    assert by_id(scan_downloaded(downloaded).assets)["wfypejzha"].resolutions == ["4K"]


def test_scan_produces_a_fingerprint(downloaded: Path) -> None:
    asset = by_id(scan_downloaded(downloaded).assets)["wlrvaf3"]

    assert len(asset.fingerprint) == 64


def test_the_fingerprint_changes_when_a_file_is_added(downloaded: Path, tmp_path: Path) -> None:
    before = by_id(scan_downloaded(downloaded).assets)["wlrvaf3"].fingerprint

    write_file(downloaded / "surface" / "concrete_rough_wlrvaf3" / "wlrvaf3_8K_Albedo.jpg")
    after = by_id(scan_downloaded(downloaded).assets)["wlrvaf3"].fingerprint

    assert before != after


def test_the_fingerprint_ignores_thumbs_db(downloaded: Path) -> None:
    before = by_id(scan_downloaded(downloaded).assets)["wlrvaf3"].fingerprint

    write_file(downloaded / "surface" / "concrete_rough_wlrvaf3" / "Thumbs.db")
    write_file(downloaded / "surface" / "concrete_rough_wlrvaf3" / "desktop.ini")
    after = by_id(scan_downloaded(downloaded).assets)["wlrvaf3"].fingerprint

    assert before == after


def test_scan_skips_a_folder_without_a_manifest_and_logs_it(tmp_path: Path) -> None:
    downloaded = make_downloaded(tmp_path, asset_ids=[])
    make_asset(downloaded, "wlrvaf3", manifest=False)

    result = scan_downloaded(downloaded)

    assert result.assets == []
    assert any("wlrvaf3" in message for message in result.skipped)


def test_scan_skips_a_folder_whose_name_has_no_id(tmp_path: Path) -> None:
    downloaded = make_downloaded(tmp_path, asset_ids=[])
    (downloaded / "surface" / "NoIdHere").mkdir(parents=True)

    result = scan_downloaded(downloaded)

    assert result.assets == []
    assert any("NoIdHere" in message for message in result.skipped)


def test_scan_logs_files_that_do_not_match_the_resolution_rule(tmp_path: Path) -> None:
    downloaded = make_downloaded(tmp_path, asset_ids=[])
    make_asset(downloaded, "wlrvaf3", extra_files=["wlrvaf3_Weird_Albedo.jpg"])

    result = scan_downloaded(downloaded)

    assert any("wlrvaf3_Weird_Albedo.jpg" in message for message in result.unmatched)


def test_scan_does_not_log_meshes_as_unmatched(tmp_path: Path) -> None:
    downloaded = make_downloaded(tmp_path, asset_ids=["xiwcfassc"])

    result = scan_downloaded(downloaded)

    assert not any(".fbx" in message for message in result.unmatched)


def test_scan_finds_the_preview(downloaded: Path) -> None:
    asset = by_id(scan_downloaded(downloaded).assets)["wlrvaf3"]

    assert asset.preview_path is not None
    assert asset.preview_path.name == "wlrvaf3_Preview.png"


def test_the_preview_is_none_when_missing(tmp_path: Path) -> None:
    downloaded = make_downloaded(tmp_path, asset_ids=[])
    make_asset(downloaded, "wlrvaf3", preview=False)

    assert by_id(scan_downloaded(downloaded).assets)["wlrvaf3"].preview_path is None


def test_scan_ignores_a_missing_type_folder(tmp_path: Path) -> None:
    downloaded = tmp_path / "Downloaded"
    downloaded.mkdir()

    assert scan_downloaded(downloaded).assets == []


def test_scan_raises_when_downloaded_does_not_exist(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        scan_downloaded(tmp_path / "missing")


def test_scan_does_not_recurse_past_the_asset_folder(tmp_path: Path) -> None:
    downloaded = make_downloaded(tmp_path, asset_ids=["wlrvaf3"])
    nested = downloaded / "surface" / "concrete_rough_wlrvaf3" / "Inner_abc"
    write_file(nested / "abc.json", b"{}")

    assert sorted(by_id(scan_downloaded(downloaded).assets)) == ["wlrvaf3"]
