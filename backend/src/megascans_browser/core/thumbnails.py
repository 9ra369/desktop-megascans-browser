"""サムネイルの生成。

``{id}_Preview.png`` から作る。このファイルは ``previews.images`` に載っていないので、
JSONの一覧は使わずディスクで確認する。
"""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

#: グリッドの1枚に使う長辺の大きさ。
THUMBNAIL_SIZE = 320


def make_thumbnail(preview_path: Path | str, size: int = THUMBNAIL_SIZE) -> bytes | None:
    """プレビュー画像からPNGのサムネイルを作る。作れなければ ``None``。

    元の画像より大きくはしない。Downloaded配下へは書き込まない。
    """
    path = Path(preview_path)
    try:
        with Image.open(path) as image:
            image.load()
            thumbnail = image.convert("RGB")
            thumbnail.thumbnail((size, size), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            thumbnail.save(buffer, format="PNG", optimize=True)
            return buffer.getvalue()
    except (OSError, UnidentifiedImageError, ValueError) as error:
        logger.warning("サムネイルを作れなかった: %s (%s)", path, error)
        return None
