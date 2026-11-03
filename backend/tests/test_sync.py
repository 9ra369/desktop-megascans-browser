import os
import threading
from pathlib import Path

import pytest

from downloaded import make_asset, make_downloaded, write_file
from megascans_browser.core.db import Database
from megascans_browser.core.sync import SyncService, SyncState, sync_once


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.db")
    database.connect()
    yield database
    database.close()


@pytest.fixture
def downloaded(tmp_path: Path) -> Path:
    return make_downloaded(tmp_path)


# ------------------------------------------------------------------- sync_once


def test_sync_once_inserts_every_asset(db: Database, downloaded: Path) -> None:
    result = sync_once(db, downloaded)

    assert db.count() == 3
    assert result.added == 3
    assert result.updated == 0
    assert result.removed == 0


def test_sync_once_stores_the_metadata_from_the_manifest(db: Database, downloaded: Path) -> None:
    sync_once(db, downloaded)

    asset = db.asset("wlrvaf3")
    assert asset is not None
    assert asset["name"] == "Concrete Pavement"
    assert asset["type"] == "surface"
    assert asset["rel_dir"] == "surface/Concrete Pavement_wlrvaf3"
    assert asset["categories"] == ["surface", "surface/concrete", "surface/concrete/rough"]
    assert asset["meta"]["scanArea"] == "2x2 m"


def test_sync_once_stores_the_resolutions_from_the_real_files(
    db: Database, downloaded: Path
) -> None:
    sync_once(db, downloaded)

    asset = db.asset("wfypejzha")
    assert asset is not None
    assert asset["resolutions"] == ["2K", "4K"]


def test_sync_once_stores_a_thumbnail(db: Database, downloaded: Path) -> None:
    sync_once(db, downloaded)

    assert db.thumbnail("wlrvaf3")


def test_sync_once_is_a_no_op_when_nothing_changed(db: Database, downloaded: Path) -> None:
    sync_once(db, downloaded)

    result = sync_once(db, downloaded)

    assert (result.added, result.updated, result.removed) == (0, 0, 0)
    assert result.unchanged == 3


def test_sync_once_does_not_read_the_manifest_of_an_unchanged_asset(
    db: Database, downloaded: Path
) -> None:
    sync_once(db, downloaded)

    # サイズと更新日時を変えずに中身を壊す。フィンガープリントは同じままなので、
    # JSONを読み直していれば解析に失敗する。
    manifest = downloaded / "surface" / "Concrete Pavement_wlrvaf3" / "wlrvaf3.json"
    stat = manifest.stat()
    manifest.write_bytes(b"!" * stat.st_size)
    os.utime(manifest, ns=(stat.st_atime_ns, stat.st_mtime_ns))

    result = sync_once(db, downloaded)

    assert result.unchanged == 3
    assert result.failed == 0


def test_sync_once_updates_a_changed_asset(db: Database, downloaded: Path) -> None:
    sync_once(db, downloaded)
    write_file(downloaded / "surface" / "Concrete Pavement_wlrvaf3" / "wlrvaf3_8K_Albedo.jpg")

    result = sync_once(db, downloaded)

    assert (result.added, result.updated) == (0, 1)
    asset = db.asset("wlrvaf3")
    assert asset is not None
    assert asset["resolutions"] == ["2K", "4K", "8K"]


def test_sync_once_removes_an_asset_that_is_gone(db: Database, downloaded: Path) -> None:
    import shutil

    sync_once(db, downloaded)
    shutil.rmtree(downloaded / "surface" / "Concrete Pavement_wlrvaf3")

    result = sync_once(db, downloaded)

    assert result.removed == 1
    assert db.asset("wlrvaf3") is None
    assert db.count() == 2


def test_sync_once_reports_a_folder_without_a_manifest(db: Database, tmp_path: Path) -> None:
    downloaded = make_downloaded(tmp_path, asset_ids=[])
    make_asset(downloaded, "wlrvaf3", manifest=False)

    result = sync_once(db, downloaded)

    assert db.count() == 0
    assert any("wlrvaf3" in message for message in result.log)


def test_sync_once_reports_a_broken_manifest(db: Database, tmp_path: Path) -> None:
    downloaded = make_downloaded(tmp_path, asset_ids=[])
    folder = make_asset(downloaded, "wlrvaf3")
    (folder / "wlrvaf3.json").write_text("{ broken", encoding="utf-8")

    result = sync_once(db, downloaded)

    assert result.failed == 1
    assert db.count() == 0
    assert any("wlrvaf3" in message for message in result.log)


def test_sync_once_keeps_the_other_assets_when_one_manifest_is_broken(
    db: Database, downloaded: Path
) -> None:
    (downloaded / "surface" / "Concrete Pavement_wlrvaf3" / "wlrvaf3.json").write_text(
        "{ broken", encoding="utf-8"
    )

    result = sync_once(db, downloaded)

    assert result.added == 2
    assert result.failed == 1
    assert db.count() == 2


def test_sync_once_works_without_a_preview(db: Database, tmp_path: Path) -> None:
    downloaded = make_downloaded(tmp_path, asset_ids=[])
    make_asset(downloaded, "wlrvaf3", preview=False)

    sync_once(db, downloaded)

    assert db.count() == 1
    assert db.thumbnail("wlrvaf3") is None


def test_sync_once_reports_progress(db: Database, downloaded: Path) -> None:
    seen: list[tuple[int, int]] = []

    sync_once(db, downloaded, on_progress=lambda done, total: seen.append((done, total)))

    assert seen
    assert seen[-1] == (3, 3)


def test_sync_once_does_not_write_into_downloaded(db: Database, downloaded: Path) -> None:
    before = {path: path.stat().st_mtime_ns for path in downloaded.rglob("*") if path.is_file()}

    sync_once(db, downloaded)

    after = {path: path.stat().st_mtime_ns for path in downloaded.rglob("*") if path.is_file()}
    assert before == after


# ---------------------------------------------------------------- SyncService


@pytest.fixture
def service(db: Database) -> SyncService:
    return SyncService(db)


def test_the_service_starts_idle(service: SyncService) -> None:
    status = service.status()

    assert status["state"] == SyncState.IDLE
    assert status["running"] is False


def test_the_service_runs_a_sync_in_the_background(service: SyncService, downloaded: Path) -> None:
    assert service.start(downloaded) is True
    service.wait(timeout=30)

    status = service.status()
    assert status["state"] == SyncState.DONE
    assert status["running"] is False
    assert status["added"] == 3
    assert status["done"] == status["total"] == 3


def test_the_service_runs_only_one_sync_at_a_time(service: SyncService, downloaded: Path) -> None:
    release = threading.Event()
    started = threading.Event()

    def slow(done: int, total: int) -> None:
        started.set()
        release.wait(timeout=30)

    assert service.start(downloaded, on_progress=slow) is True
    assert started.wait(timeout=30)
    assert service.start(downloaded) is False
    release.set()
    service.wait(timeout=30)

    assert service.status()["state"] == SyncState.DONE


def test_the_service_records_a_failure(service: SyncService, tmp_path: Path) -> None:
    assert service.start(tmp_path / "missing") is True
    service.wait(timeout=30)

    status = service.status()
    assert status["state"] == SyncState.ERROR
    assert status["error"]


def test_the_service_can_run_again_after_a_failure(
    service: SyncService, tmp_path: Path, downloaded: Path
) -> None:
    service.start(tmp_path / "missing")
    service.wait(timeout=30)

    assert service.start(downloaded) is True
    service.wait(timeout=30)
    assert service.status()["state"] == SyncState.DONE


def test_the_service_keeps_the_log(service: SyncService, tmp_path: Path) -> None:
    downloaded = make_downloaded(tmp_path, asset_ids=[])
    make_asset(downloaded, "wlrvaf3", manifest=False)

    service.start(downloaded)
    service.wait(timeout=30)

    assert any("wlrvaf3" in message for message in service.status()["log"])


def test_the_database_can_be_read_while_a_sync_runs(
    service: SyncService, db: Database, downloaded: Path
) -> None:
    release = threading.Event()
    started = threading.Event()

    def slow(done: int, total: int) -> None:
        started.set()
        release.wait(timeout=30)

    service.start(downloaded, on_progress=slow)
    assert started.wait(timeout=30)
    try:
        assert db.search() is not None
    finally:
        release.set()
        service.wait(timeout=30)
