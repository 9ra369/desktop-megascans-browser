"""``{id}.json`` の解析。

アセット単位のメタデータにだけ使う。ファイル一覧は入手可能なファイルのカタログで
あって、ダウンロード済みの一覧ではないため、解像度はここから取らない。
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

#: 取り出すメタデータの版。``_DROPPED_META_KEYS`` など、同じ `{id}.json` から
#: 取り出す内容を変えたら上げる。同期が既存のDBを作り直す目印に使う。
META_VERSION = "2"

#: ``META_VERSION`` を入れる ``app_meta`` のキー。
META_VERSION_KEY = "meta_version"

#: `categories[0]` と `assetCategories` のルート名の対応。
_CATEGORY_ROOTS = {"3D asset": "3d", "3D plant": "3dplant"}

#: DBに持たないメタデータ。
#:
#: 設計の「ポリゴン数、色空間、バリエーション、マップ種類、LODはDBに持たない」と、
#: 「詳細パネルにはBillboardの有無とLODは表示しない」に対応する。
#: ``dimensions`` はバリエーション別の寸法なので落とす。
#: ``scanner``、``tileable``、``calibration`` は閲覧の判断に使わないので落とす。
_DROPPED_META_KEYS = frozenset(
    {
        "lodDistance",
        "points",
        "splitSubmeshes",
        "useBillboardMaterial",
        "dimensions",
        "scanner",
        "tileable",
        "calibration",
    }
)

#: `search_text` の元にするフィールド。
_SEARCH_FIELDS = ("name", "id", "categories", "tags", "environment", "semanticTags")

_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class AssetMeta:
    """``{id}.json`` から取り出した、DBに入れる情報。"""

    id: str
    name: str
    type: str
    category_paths: list[str]
    search_text: str
    average_color: str
    meta: dict[str, Any] = field(default_factory=dict)


def normalize_category_root(name: str) -> str:
    return _CATEGORY_ROOTS.get(name, name)


def category_paths(asset_categories: dict[str, Any]) -> list[str]:
    """``assetCategories`` を親階層を含むパスの一覧にする。

    ``{"3D asset": {"nature": {"rock": {}}}}`` なら ``3d``、``3d/nature``、
    ``3d/nature/rock`` の3件になる。絞り込みを完全一致だけで済ませるため。
    """

    def walk(node: dict[str, Any], prefix: str) -> Iterator[str]:
        for name, children in node.items():
            path = f"{prefix}/{name}" if prefix else normalize_category_root(name)
            yield path
            if isinstance(children, dict):
                yield from walk(children, path)

    return sorted(walk(asset_categories, ""))


def _keys_deep(node: dict[str, Any]) -> Iterator[str]:
    """入れ子の辞書のキーを返す。``locations`` のような分類はキーが中身。"""
    for name, children in node.items():
        yield name
        if isinstance(children, dict):
            yield from _keys_deep(children)


def _strings_deep(node: Any) -> Iterator[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        yield from _keys_deep(node)
    elif isinstance(node, list):
        for value in node:
            yield from _strings_deep(value)


def _source_strings(manifest: dict[str, Any]) -> Iterator[str]:
    for name in _SEARCH_FIELDS:
        value = manifest.get(name)
        if isinstance(value, dict):
            # フィールド名は検索語にしないので、値だけを辿る。
            for inner in value.values():
                yield from _strings_deep(inner)
        else:
            yield from _strings_deep(value)
    yield from _keys_deep(manifest.get("assetCategories") or {})


def search_text_for(manifest: dict[str, Any]) -> str:
    """検索用の文字列を作る。小文字の語を重複なく並べたもの。"""
    words = {
        word for source in _source_strings(manifest) for word in _WORD_RE.findall(source.lower())
    }
    return " ".join(sorted(words))


def _meta_of(manifest: dict[str, Any]) -> dict[str, Any]:
    entries = manifest.get("meta") or []
    return {
        entry["key"]: entry["value"]
        for entry in entries
        if isinstance(entry, dict) and entry.get("key") not in _DROPPED_META_KEYS
    }


def parse_manifest(manifest: dict[str, Any]) -> AssetMeta:
    """``{id}.json`` を読み込んだ辞書から :class:`AssetMeta` を作る。"""
    return AssetMeta(
        id=manifest["id"],
        name=manifest.get("name") or manifest["id"],
        type=normalize_category_root(manifest["categories"][0]),
        category_paths=category_paths(manifest.get("assetCategories") or {}),
        search_text=search_text_for(manifest),
        average_color=manifest.get("averageColor") or "",
        meta=_meta_of(manifest),
    )
