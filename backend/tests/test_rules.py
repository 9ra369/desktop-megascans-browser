"""CLAUDE.md と設計で明文化されている禁止事項をテストで固定する。"""

from __future__ import annotations

import shutil
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from downloaded import make_downloaded
from megascans_browser.api.app import create_app
from megascans_browser.api.settings import DOWNLOADED_PATH_KEY, ServerSettings
from megascans_browser.core.db import Database
from megascans_browser.core.scan import scan_downloaded
from megascans_browser.core.sync import sync_once

TOKEN = "test-token"


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "test.db")
    database.connect()
    yield database
    database.close()


@pytest.fixture
def downloaded(tmp_path: Path) -> Path:
    return make_downloaded(tmp_path / "library")


@pytest.fixture
def client(db: Database) -> Iterator[TestClient]:
    app = create_app(db, ServerSettings(token=TOKEN))
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {TOKEN}"
        yield test_client


def test_the_fingerprint_is_the_same_below_a_different_absolute_path(tmp_path: Path) -> None:
    """設計: フィンガープリントの元から絶対パスを除外する。"""
    first = make_downloaded(tmp_path / "one")
    second = tmp_path / "two" / "Downloaded"
    second.parent.mkdir(parents=True)
    shutil.copytree(first, second)

    by_id_first = {asset.id: asset for asset in scan_downloaded(first).assets}
    by_id_second = {asset.id: asset for asset in scan_downloaded(second).assets}

    assert by_id_first.keys() == by_id_second.keys()
    for asset_id, asset in by_id_first.items():
        assert asset.rel_dir == by_id_second[asset_id].rel_dir
        assert asset.fingerprint == by_id_second[asset_id].fingerprint


def test_scan_reads_neither_assets_data_nor_the_excluded_roots(downloaded: Path) -> None:
    """設計: `assetsData.json` は使わない。`atlas`、`brush`、`DHI` は走査しない。"""
    # 読もうとすれば失敗するように、フォルダへ置き換える。
    (downloaded / "assetsData.json").unlink()
    (downloaded / "assetsData.json").mkdir()
    for name in ("atlas", "brush", "DHI"):
        shutil.rmtree(downloaded / name)
        (downloaded / name).write_text("ファイルなのでiterdirできない", encoding="utf-8")

    result = scan_downloaded(downloaded)

    assert sorted(asset.id for asset in result.assets) == [
        "wfypejzha",
        "wlrvaf3",
        "xiwcfassc",
    ]


def test_search_and_list_do_not_touch_the_disk(
    client: TestClient, db: Database, downloaded: Path
) -> None:
    """CLAUDE.md: 検索と一覧表示では `{id}.json` と実ファイルを読まない。"""
    db.set_meta(DOWNLOADED_PATH_KEY, str(downloaded))
    sync_once(db, downloaded)

    # Downloadedを丸ごと消す。ディスクを読んでいれば答えられない。
    shutil.rmtree(downloaded)

    assert client.get("/assets").json()["total"] == 3
    assert client.get("/assets", params={"q": "pavement"}).json()["total"] == 1
    assert client.get("/assets/wlrvaf3").json()["name"] == "Concrete Pavement"
    assert client.get("/categories").json()["items"]
    assert client.get("/thumbnails/wlrvaf3").status_code == 200


def test_a_second_sync_is_rejected_while_one_runs(
    client: TestClient, db: Database, downloaded: Path
) -> None:
    """設計: 同期は同時に1つだけ実行する。"""
    db.set_meta(DOWNLOADED_PATH_KEY, str(downloaded))
    release = threading.Event()
    started = threading.Event()
    service = client.app.state.sync
    original = service.start

    def blocking_start(root: Path, on_progress: object = None) -> bool:
        def hold(done: int, total: int) -> None:
            started.set()
            release.wait(timeout=30)

        return original(root, on_progress=hold)

    service.start = blocking_start  # type: ignore[method-assign]
    try:
        assert client.post("/sync").status_code == 202
        assert started.wait(timeout=30)
        service.start = original  # type: ignore[method-assign]

        assert client.post("/sync").status_code == 409
        assert client.get("/sync/status").json()["running"] is True
    finally:
        release.set()
        service.wait(timeout=30)


def test_the_database_can_be_searched_while_a_sync_runs(
    client: TestClient, db: Database, downloaded: Path
) -> None:
    """設計: 同期中も検索できるよう、SQLiteはWALモードで使う。"""
    db.set_meta(DOWNLOADED_PATH_KEY, str(downloaded))
    release = threading.Event()
    started = threading.Event()
    service = client.app.state.sync

    def hold(done: int, total: int) -> None:
        started.set()
        release.wait(timeout=30)

    assert service.start(downloaded, on_progress=hold) is True
    try:
        assert started.wait(timeout=30)
        assert client.get("/assets").status_code == 200
        assert client.get("/categories").status_code == 200
    finally:
        release.set()
        service.wait(timeout=30)
