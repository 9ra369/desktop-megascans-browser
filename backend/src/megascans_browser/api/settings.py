"""サーバーの起動設定。

待ち受けは ``127.0.0.1`` のみ。トークンは起動ごとに生成する。
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from pathlib import Path

#: CORSで許可するオリジン。アプリの画面だけ。
#: ``file://`` から読み込まれたレンダラーは Origin を送らないか ``null`` を送る。
ALLOWED_ORIGINS: tuple[str, ...] = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

#: Downloadedの場所を入れる ``app_meta`` のキー。
DOWNLOADED_PATH_KEY = "downloaded_path"


@dataclass(frozen=True)
class ServerSettings:
    """起動ごとに決まる設定。"""

    #: 待ち受けアドレス。ループバック固定。
    host: str = "127.0.0.1"
    #: 0 を渡すとOSが空きポートを選ぶ。
    port: int = 0
    #: APIの認証に使うトークン。
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    #: SQLiteのファイル。Electronの ``userData`` の下に置く。
    db_path: Path | None = None
    allowed_origins: tuple[str, ...] = ALLOWED_ORIGINS
