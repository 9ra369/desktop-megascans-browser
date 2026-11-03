"""Downloadedの走査。

走査範囲は ``Downloaded/{3d,3dplant,surface}/{folder}/`` の2階層。アセットの判定は
フォルダ名の末尾 ``_{id}`` から ``{id}.json`` を探す。Downloaded配下へは書き込まない。
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .fingerprint import FileEntry, compute_fingerprint, normalize_rel_path
from .naming import (
    ASSET_TYPES,
    asset_id_from_folder_name,
    collect_resolutions,
    is_billboard,
    is_ignored_file,
    is_non_texture_path,
    parse_resolution,
)

#: 解像度を持たないのが普通で、規則外として記録しないファイルの拡張子。
_NON_TEXTURE_SUFFIXES = frozenset({".abc", ".fbx", ".json", ".mtl", ".obj", ".ztl"})


@dataclass(frozen=True)
class ScannedAsset:
    """ディスク上の1アセット。``{id}.json`` はまだ読んでいない。"""

    id: str
    type: str
    #: Downloadedからの相対パス。区切りは ``/``。
    rel_dir: str
    folder: Path
    manifest_path: Path
    preview_path: Path | None
    files: list[FileEntry]
    resolutions: list[str]
    fingerprint: str


@dataclass
class ScanResult:
    assets: list[ScannedAsset] = field(default_factory=list)
    #: ``{id}.json`` がない、またはIDが取れないフォルダ。
    skipped: list[str] = field(default_factory=list)
    #: 解像度の規則に合わないファイル。
    unmatched: list[str] = field(default_factory=list)


def _files_below(folder: Path) -> Iterator[tuple[str, Path]]:
    for path in folder.rglob("*"):
        if not path.is_file() or is_ignored_file(path.name):
            continue
        yield normalize_rel_path(str(path.relative_to(folder))), path


def _is_unmatched(rel_path: str) -> bool:
    # Bridgeの補助フォルダはテクスチャではないので、規則外として数えない。
    if is_non_texture_path(rel_path):
        return False
    if is_billboard(rel_path) or parse_resolution(rel_path) is not None:
        return False
    name = rel_path.rsplit("/", 1)[-1]
    if name.lower().endswith("_preview.png"):
        return False
    return Path(name).suffix.lower() not in _NON_TEXTURE_SUFFIXES


def _scan_asset_folder(folder: Path, asset_type: str, downloaded: Path, result: ScanResult) -> None:
    asset_id = asset_id_from_folder_name(folder.name)
    if asset_id is None:
        result.skipped.append(f"フォルダ名からIDが取れない: {folder.name}")
        return

    manifest_path = folder / f"{asset_id}.json"
    if not manifest_path.is_file():
        result.skipped.append(f"{asset_id}.json がない: {folder.name}")
        return

    files: list[FileEntry] = []
    paths: list[str] = []
    preview_path: Path | None = None
    for rel_path, path in _files_below(folder):
        stat = path.stat()
        files.append(FileEntry(rel_path=rel_path, size=stat.st_size, mtime_ns=stat.st_mtime_ns))
        paths.append(rel_path)
        if rel_path == f"{asset_id}_Preview.png":
            preview_path = path
        if _is_unmatched(rel_path):
            result.unmatched.append(f"解像度の規則に合わない: {folder.name}/{rel_path}")

    result.assets.append(
        ScannedAsset(
            id=asset_id,
            type=asset_type,
            rel_dir=normalize_rel_path(str(folder.relative_to(downloaded))),
            folder=folder,
            manifest_path=manifest_path,
            preview_path=preview_path,
            files=files,
            resolutions=collect_resolutions(paths),
            fingerprint=compute_fingerprint(files),
        )
    )


def scan_downloaded(downloaded: Path | str) -> ScanResult:
    """``Downloaded`` を2階層走査して、ダウンロード済みのアセットを返す。"""
    root = Path(downloaded)
    if not root.is_dir():
        raise FileNotFoundError(f"Downloadedが見つからない: {root}")

    result = ScanResult()
    for asset_type in ASSET_TYPES:
        type_folder = root / asset_type
        if not type_folder.is_dir():
            continue
        for folder in sorted(type_folder.iterdir()):
            if folder.is_dir():
                _scan_asset_folder(folder, asset_type, root, result)
    return result
