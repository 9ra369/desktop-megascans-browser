"""テスト用に ``Downloaded`` と同じ構成のフォルダを作るヘルパー。"""

from __future__ import annotations

import json
from pathlib import Path

from helpers import load_manifest

#: フィクスチャのアセットIDと、実際のフォルダに置かれるファイルの構成。
LAYOUTS: dict[str, tuple[str, str, list[str]]] = {
    "wlrvaf3": (
        "surface",
        "Concrete Pavement_wlrvaf3",
        [
            "wlrvaf3_2K_Albedo.jpg",
            "wlrvaf3_2K_Normal.exr",
            "wlrvaf3_4K_Albedo.jpg",
            "wlrvaf3_4K_Normal.exr",
        ],
    ),
    "xiwcfassc": (
        "3d",
        "Industrial Junkyard Storage Pallet Wood Tarp_xiwcfassc",
        [
            "xiwcfassc_High.fbx",
            "xiwcfassc_LOD0.fbx",
            "xiwcfassc_8K_Normal_LOD0.exr",
            "xiwcfassc_4K_Albedo.jpg",
        ],
    ),
    "wfypejzha": (
        "3dplant",
        "Dragon Tree_wfypejzha",
        [
            "Var1/Var1_LOD0.fbx",
            "Textures/Atlas/wfypejzha_4K_Albedo.jpg",
            "Textures/Atlas/wfypejzha_2K_Albedo.jpg",
            "Textures/Billboard/Billboard_8K_Albedo.jpg",
        ],
    ),
}


def write_file(path: Path, content: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def preview_png() -> bytes:
    """``{id}_Preview.png`` の中身として使う、小さな本物のPNG。"""
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (600, 400), (12, 34, 56)).save(buffer, format="PNG")
    return buffer.getvalue()


def make_asset(
    downloaded: Path,
    asset_id: str,
    *,
    manifest: bool = True,
    preview: bool = True,
    extra_files: list[str] | None = None,
) -> Path:
    """フィクスチャ1件ぶんのアセットフォルダを作り、そのパスを返す。"""
    asset_type, folder_name, files = LAYOUTS[asset_id]
    folder = downloaded / asset_type / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    for name in [*files, *(extra_files or [])]:
        write_file(folder / name)
    if manifest:
        (folder / f"{asset_id}.json").write_text(
            json.dumps(load_manifest(asset_id), ensure_ascii=False), encoding="utf-8"
        )
    if preview:
        write_file(folder / f"{asset_id}_Preview.png", preview_png())
    return folder


def make_downloaded(root: Path, asset_ids: list[str] | None = None) -> Path:
    """``Downloaded`` 相当のフォルダを作る。走査しないフォルダも置く。"""
    downloaded = root / "Downloaded"
    for name in ("atlas", "brush", "DHI"):
        write_file(downloaded / name / "Should Not Be Scanned_zzz" / "zzz.json", b"{}")
    (downloaded / "assetsData.json").write_text("{}", encoding="utf-8")

    for asset_id in asset_ids if asset_ids is not None else list(LAYOUTS):
        make_asset(downloaded, asset_id)
    return downloaded
