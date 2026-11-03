"""アセットの差分検知に使うフィンガープリント。

元にする情報は相対パス、サイズ、更新日時だけ。絶対パス、最終アクセス日時、
ファイルの中身は使わない。
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import NamedTuple


class FileEntry(NamedTuple):
    """アセットフォルダ配下の1ファイル。``rel_path`` はアセットフォルダからの相対パス。"""

    rel_path: str
    size: int
    mtime_ns: int


def normalize_rel_path(rel_path: str) -> str:
    """区切りを ``/`` に統一する。"""
    return rel_path.replace("\\", "/")


def compute_fingerprint(files: Iterable[FileEntry]) -> str:
    """ファイルの一覧からSHA-256のハッシュ値を返す。並び順には依存しない。"""
    lines = sorted(
        "\0".join((normalize_rel_path(file.rel_path), str(file.size), str(file.mtime_ns)))
        for file in files
    )
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()
