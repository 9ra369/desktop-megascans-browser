"""SQLiteのスキーマと検索。

DBは再生成できるキャッシュとして扱う。同期中も検索できるようWALモードで使う。
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from .records import AssetRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    type          TEXT NOT NULL,
    rel_dir       TEXT NOT NULL,
    search_text   TEXT NOT NULL,
    average_color TEXT NOT NULL DEFAULT '',
    meta_json     TEXT NOT NULL DEFAULT '{}',
    resolutions   TEXT NOT NULL DEFAULT '',
    fingerprint   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS asset_categories (
    asset_id      TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    category_path TEXT NOT NULL,
    PRIMARY KEY (asset_id, category_path)
);

CREATE TABLE IF NOT EXISTS thumbnails (
    asset_id TEXT PRIMARY KEY REFERENCES assets(id) ON DELETE CASCADE,
    image    BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS app_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS assets_type_idx ON assets(type);
CREATE INDEX IF NOT EXISTS assets_name_idx ON assets(name);
CREATE INDEX IF NOT EXISTS asset_categories_path_idx ON asset_categories(category_path);
"""

#: `LIKE` のエスケープに使う文字。`%` と `_` を検索語として扱えるようにする。
_LIKE_ESCAPE = "\\"

#: 一覧で返す列。fingerprintは差分検知専用なので含めない。
_LIST_COLUMNS = (
    "id",
    "name",
    "type",
    "rel_dir",
    "average_color",
    "resolutions",
)


def _escape_like(value: str) -> str:
    for character in (_LIKE_ESCAPE, "%", "_"):
        value = value.replace(character, _LIKE_ESCAPE + character)
    return value


def _split_resolutions(value: str) -> list[str]:
    return [item for item in (part.strip() for part in value.split(",")) if item]


def _row_to_asset(row: sqlite3.Row) -> dict[str, Any]:
    asset = {key: row[key] for key in row.keys()}
    asset["resolutions"] = _split_resolutions(row["resolutions"])
    if "meta_json" in asset:
        asset["meta"] = json.loads(asset.pop("meta_json"))
    return asset


class Database:
    """1ファイルのSQLiteを扱う。

    FastAPIとElectronには依存しない。

    接続はスレッドごとに1本持つ。1本の ``sqlite3.Connection`` を複数スレッドで同時に
    使うと、読み出しと書き込みが重なった時点で
    ``sqlite3.InterfaceError: bad parameter or other API misuse`` になる
    （実機で `/thumbnails` の読み出しとバックグラウンド同期の書き込みが重なって発生）。
    WALモードは接続を分けて使う前提の仕組みなので、スレッドごとに分けるのが正しい。
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._local = threading.local()
        self._all_connections: list[sqlite3.Connection] = []
        self._connections_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._ready = False

    def _new_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        with self._connections_lock:
            self._all_connections.append(connection)
        return connection

    @property
    def connection(self) -> sqlite3.Connection:
        """呼び出したスレッド専用の接続。"""
        if not self._ready:
            raise RuntimeError("connect() を先に呼ぶこと")
        connection: sqlite3.Connection | None = getattr(self._local, "connection", None)
        if connection is None:
            connection = self._new_connection()
            self._local.connection = connection
        return connection

    def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._new_connection()
        connection.executescript(SCHEMA)
        connection.commit()
        self._local.connection = connection
        self._ready = True

    def close(self) -> None:
        """すべてのスレッドの接続を閉じる。"""
        with self._connections_lock:
            connections, self._all_connections = self._all_connections, []
        for connection in connections:
            try:
                connection.close()
            except sqlite3.Error:
                # 別のスレッドが使っていた接続は、そのスレッド側で閉じられる。
                pass
        self._local = threading.local()
        self._ready = False

    def __enter__(self) -> Database:
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------ 書き込み

    def replace_assets(self, records: Iterable[AssetRecord]) -> None:
        """アセットをまとめて入れ替える。既存の行はカテゴリごと置き換える。"""
        rows = list(records)
        if not rows:
            return
        with self._write_lock, self.connection:
            for record in rows:
                meta = record.meta
                self.connection.execute(
                    """
                    INSERT INTO assets (id, name, type, rel_dir, search_text,
                                        average_color, meta_json, resolutions, fingerprint)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        type = excluded.type,
                        rel_dir = excluded.rel_dir,
                        search_text = excluded.search_text,
                        average_color = excluded.average_color,
                        meta_json = excluded.meta_json,
                        resolutions = excluded.resolutions,
                        fingerprint = excluded.fingerprint
                    """,
                    (
                        meta.id,
                        meta.name,
                        meta.type,
                        record.rel_dir,
                        meta.search_text,
                        meta.average_color,
                        json.dumps(meta.meta, ensure_ascii=False, sort_keys=True),
                        ", ".join(record.resolutions),
                        record.fingerprint,
                    ),
                )
                self.connection.execute(
                    "DELETE FROM asset_categories WHERE asset_id = ?", (meta.id,)
                )
                self.connection.executemany(
                    "INSERT INTO asset_categories (asset_id, category_path) VALUES (?, ?)",
                    [(meta.id, path) for path in meta.category_paths],
                )

    def delete_assets(self, asset_ids: Sequence[str]) -> None:
        if not asset_ids:
            return
        with self._write_lock, self.connection:
            self.connection.executemany(
                "DELETE FROM assets WHERE id = ?", [(asset_id,) for asset_id in asset_ids]
            )

    def put_thumbnail(self, asset_id: str, image: bytes) -> None:
        with self._write_lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO thumbnails (asset_id, image) VALUES (?, ?)
                ON CONFLICT(asset_id) DO UPDATE SET image = excluded.image
                """,
                (asset_id, image),
            )

    def set_meta(self, key: str, value: str) -> None:
        with self._write_lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO app_meta (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    # -------------------------------------------------------------------- 読み出し

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        row = self.connection.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row is not None else default

    def thumbnail(self, asset_id: str) -> bytes | None:
        row = self.connection.execute(
            "SELECT image FROM thumbnails WHERE asset_id = ?", (asset_id,)
        ).fetchone()
        return bytes(row["image"]) if row is not None else None

    def fingerprints(self) -> dict[str, str]:
        rows = self.connection.execute("SELECT id, fingerprint FROM assets")
        return {row["id"]: row["fingerprint"] for row in rows}

    def asset(self, asset_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT id, name, type, rel_dir, average_color, meta_json, resolutions, fingerprint
            FROM assets WHERE id = ?
            """,
            (asset_id,),
        ).fetchone()
        if row is None:
            return None
        asset = _row_to_asset(row)
        asset["categories"] = [
            category["category_path"]
            for category in self.connection.execute(
                """
                SELECT category_path FROM asset_categories
                WHERE asset_id = ? ORDER BY category_path
                """,
                (asset_id,),
            )
        ]
        return asset

    def search(
        self,
        query: str | None = None,
        asset_type: str | None = None,
        category: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """一覧と検索。`{id}.json` と実ファイルは読まず、DBだけで答える。"""
        where, parameters = self._conditions(query, asset_type, category)
        sql = f"SELECT {', '.join(_LIST_COLUMNS)} FROM assets{where} ORDER BY name, id"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            parameters = [*parameters, limit, offset]
        elif offset:
            sql += " LIMIT -1 OFFSET ?"
            parameters = [*parameters, offset]
        return [_row_to_asset(row) for row in self.connection.execute(sql, parameters)]

    def count(
        self,
        query: str | None = None,
        asset_type: str | None = None,
        category: str | None = None,
    ) -> int:
        where, parameters = self._conditions(query, asset_type, category)
        return self.connection.execute(
            f"SELECT COUNT(*) FROM assets{where}", parameters
        ).fetchone()[0]

    def categories(self) -> list[dict[str, Any]]:
        """カテゴリツリーと件数。親階層も行として入っているので `GROUP BY` だけで済む。"""
        rows = self.connection.execute(
            """
            SELECT category_path AS path, COUNT(*) AS count
            FROM asset_categories
            GROUP BY category_path
            ORDER BY category_path
            """
        )
        return [{"path": row["path"], "count": row["count"]} for row in rows]

    # ---------------------------------------------------------------------- 内部

    def _conditions(
        self, query: str | None, asset_type: str | None, category: str | None
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        for word in (query or "").split():
            clauses.append(f"search_text LIKE ? ESCAPE '{_LIKE_ESCAPE}'")
            parameters.append(f"%{_escape_like(word.lower())}%")
        if asset_type:
            clauses.append("type = ?")
            parameters.append(asset_type)
        if category:
            clauses.append(
                "EXISTS (SELECT 1 FROM asset_categories"
                " WHERE asset_id = assets.id AND category_path = ?)"
            )
            parameters.append(category)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return where, parameters
