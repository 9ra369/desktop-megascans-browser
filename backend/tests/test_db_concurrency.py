"""同期の書き込みと検索の読み出しが本当に並行して動くことを確認する。

設計: 「同期中も検索できるよう、SQLiteはWALモードで使う」。
実機で `/thumbnails` の読み出しが同期の書き込みと重なり、
``sqlite3.InterfaceError: bad parameter or other API misuse`` が出たための回帰テスト。
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from megascans_browser.core.db import Database
from megascans_browser.core.manifest import AssetMeta
from megascans_browser.core.records import AssetRecord

#: 読み書きを重ねる回数。1つの接続を共有していれば、この回数で必ず壊れる。
ROUNDS = 150


def record(asset_id: str, name: str = "Asset") -> AssetRecord:
    return AssetRecord(
        meta=AssetMeta(
            id=asset_id,
            name=f"{name} {asset_id}",
            type="surface",
            category_paths=["surface", "surface/concrete"],
            search_text=f"{asset_id} concrete",
            average_color="#112233",
            meta={"scanArea": "2x2 m"},
        ),
        rel_dir=f"surface/concrete_rough_{asset_id}",
        resolutions=["4K"],
        fingerprint=f"fp-{asset_id}-{name}",
    )


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "test.db")
    database.connect()
    yield database
    database.close()


def run_concurrently(*workers: object) -> None:
    errors: list[BaseException] = []

    def guard(worker: object) -> None:
        try:
            worker()  # type: ignore[operator]
        except BaseException as error:  # noqa: BLE001 - 本体で上げ直す
            errors.append(error)

    threads = [
        threading.Thread(target=guard, args=(worker,), name=f"worker-{index}")
        for index, worker in enumerate(workers)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    for thread in threads:
        assert not thread.is_alive(), "スレッドが終わらなかった"
    if errors:
        raise errors[0]


def test_thumbnails_can_be_read_while_assets_are_written(db: Database) -> None:
    db.replace_assets([record("aaa")])
    db.put_thumbnail("aaa", b"png")

    def writer() -> None:
        for round_number in range(ROUNDS):
            db.replace_assets([record("aaa", name=f"round{round_number}")])
            db.put_thumbnail("aaa", bytes([round_number % 256]))

    def reader() -> None:
        for _ in range(ROUNDS):
            assert db.thumbnail("aaa") is not None

    run_concurrently(writer, reader)


def test_search_works_while_assets_are_written(db: Database) -> None:
    db.replace_assets([record("aaa"), record("bbb")])

    def writer() -> None:
        for round_number in range(ROUNDS):
            db.replace_assets([record("ccc", name=f"round{round_number}")])

    def reader() -> None:
        for _ in range(ROUNDS):
            assert db.search(query="concrete")
            db.count()
            db.categories()
            db.asset("aaa")

    run_concurrently(writer, reader)


def test_two_readers_and_a_writer(db: Database) -> None:
    db.replace_assets([record("aaa")])

    def writer() -> None:
        for round_number in range(ROUNDS):
            db.replace_assets([record(f"id{round_number % 5}")])
            db.set_meta("downloaded_path", f"C:/x/{round_number}")

    def reader() -> None:
        for _ in range(ROUNDS):
            db.search()
            db.fingerprints()
            db.get_meta("downloaded_path")

    run_concurrently(writer, reader, reader)
