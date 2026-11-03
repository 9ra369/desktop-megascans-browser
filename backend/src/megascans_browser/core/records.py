"""coreの各処理のあいだで受け渡す型。"""

from __future__ import annotations

from dataclasses import dataclass

from .manifest import AssetMeta


@dataclass(frozen=True)
class AssetRecord:
    """DBに入れる1アセット。``{id}.json`` と実ファイルの両方から組み立てる。"""

    meta: AssetMeta
    #: Downloadedからの相対パス。区切りは ``/``。
    rel_dir: str
    #: 実ファイルの名前から集計した解像度。昇順。
    resolutions: list[str]
    #: 差分検知用のハッシュ値。
    fingerprint: str
