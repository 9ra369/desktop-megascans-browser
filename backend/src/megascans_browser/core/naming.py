"""ファイル名とフォルダ名の解析。

設計の「解像度の取得」と「同期のルール」に対応する。JSONのファイル一覧は使わず、
実ファイルの名前だけから解像度を読み取る。
"""

from __future__ import annotations

import re
from collections.abc import Iterable

#: 走査するDownloaded直下のフォルダ。`atlas`、`brush`、`DHI` は対象外。
ASSET_TYPES: tuple[str, ...] = ("3d", "3dplant", "surface")

#: フィンガープリントと解像度の集計から外すファイル。
IGNORED_FILE_NAMES = frozenset({"thumbs.db", "desktop.ini"})

#: `{id}_8K_Normal.exr` のような名前に含まれる解像度。
_RESOLUTION_RE = re.compile(r"(?:^|_)(\d+)K(?=_|\.|$)")

#: Bridgeがアセットフォルダ内に置く、アセット本体のテクスチャではないフォルダ。
#:
#: 実機のDownloadedで確認した構成。`Thumbs/{1k,2k,4k}/` にはBridgeの画面用の縮小画像が
#: 入っていて、実際にダウンロードした解像度とは関係ない。これを数えると、4Kだけを
#: 持つアセットが1K/2K/4Kを持っているように見える。`previews/` も同様に本体ではない。
_NON_TEXTURE_DIRS = ("thumbs", "previews")


def _file_name(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def parse_resolution(path: str) -> str | None:
    """ファイル名から解像度を返す。規則に合わなければ ``None``。"""
    match = _RESOLUTION_RE.search(_file_name(path))
    return f"{int(match.group(1))}K" if match else None


def is_billboard(path: str) -> bool:
    """パスに ``Billboard`` を含むか。解像度の集計から外すために使う。"""
    return "billboard" in path.replace("\\", "/").lower()


def is_non_texture_path(path: str) -> bool:
    """Bridgeの補助フォルダ（``Thumbs/``、``previews/``）の中のファイルか。"""
    parts = path.replace("\\", "/").lower().split("/")[:-1]
    return any(part in _NON_TEXTURE_DIRS for part in parts)


def is_ignored_file(name: str) -> bool:
    return _file_name(name).lower() in IGNORED_FILE_NAMES


def asset_id_from_folder_name(folder_name: str) -> str | None:
    """フォルダ名の末尾 ``_{id}`` からアセットIDを返す。"""
    _, separator, asset_id = folder_name.rpartition("_")
    return asset_id if separator and asset_id else None


def collect_resolutions(paths: Iterable[str]) -> list[str]:
    """実ファイルのパスから持っている解像度を昇順で集計する。

    Billboardのファイルは本体より高い解像度を持つことがあるため除外する。
    ``Thumbs/`` と ``previews/`` はBridgeの補助ファイルなので同じく除外する。
    """
    found = {
        resolution
        for path in paths
        if not is_billboard(path)
        and not is_non_texture_path(path)
        and (resolution := parse_resolution(path)) is not None
    }
    return sorted(found, key=lambda value: int(value[:-1]))
