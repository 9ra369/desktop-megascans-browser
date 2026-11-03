"""テスト用に ``Downloaded`` と同じ構成のフォルダを作るヘルパー。"""

from __future__ import annotations

import json
from pathlib import Path

from helpers import load_manifest

#: フィクスチャのアセットIDと、実際のフォルダに置かれるファイルの構成。
#:
#: 実機のDownloadedで確認した形に合わせている。本体のテクスチャは4Kだけで、
#: `Thumbs/{1k,2k,4k}/` にはBridgeの画面用の縮小画像、`previews/` にはプレビュー画像が
#: 入る。フォルダ名は `{カテゴリ}_{サブカテゴリ}_{id}` で、末尾が `{id}`。
LAYOUTS: dict[str, tuple[str, str, list[str]]] = {
    "wlrvaf3": (
        "surface",
        "concrete_rough_wlrvaf3",
        [
            "wlrvaf3_4K_Albedo.jpg",
            "wlrvaf3_4K_Normal.jpg",
            "wlrvaf3_4K_Displacement.exr",
            "previews/wlrvaf3_Popup_3840_sp.jpg",
            "Thumbs/1k/wlrvaf3_1K_Albedo.jpg",
            "Thumbs/2k/wlrvaf3_2K_Albedo.jpg",
            "Thumbs/4k/wlrvaf3_4K_Albedo.jpg",
        ],
    ),
    "xiwcfassc": (
        "3d",
        "industrial_storage_xiwcfassc",
        [
            "xiwcfassc_4K_Albedo.jpg",
            "xiwcfassc_4K_Normal_LOD0.jpg",
            "xiwcfassc_High.fbx",
            "xiwcfassc_LOD0.fbx",
            "previews/xiwcfassc_Thumb_HighPoly_Retina_sp.jpg",
            "Thumbs/1k/xiwcfassc_1K_Albedo.jpg",
            "Thumbs/2k/xiwcfassc_2K_Albedo.jpg",
            "Thumbs/4k/xiwcfassc_4K_Albedo.jpg",
        ],
    ),
    "wfypejzha": (
        "3dplant",
        "3dplant_houseplant_wfypejzha",
        [
            "Textures/Atlas/wfypejzha_4K_Albedo.jpg",
            "Textures/Atlas/wfypejzha_4K_Normal.jpg",
            "Textures/Billboard/Billboard_4K_Albedo.jpg",
            "Var1/Var1_LOD0.fbx",
            "Var2/Var2_LOD0.fbx",
            "previews/Render_Preview_Retina_sp.jpg",
            "Thumbs/1k/wfypejzha_1K_Albedo.jpg",
            "Thumbs/2k/wfypejzha_2K_Albedo.jpg",
            "Thumbs/4k/wfypejzha_4K_Albedo.jpg",
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
