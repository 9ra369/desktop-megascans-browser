"""Downloadedとの同期。

差分のあるアセットだけ ``{id}.json`` を解析し、実ファイルから解像度を集計して
サムネイルを作る。同期は同時に1つだけ実行する。
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from .db import Database
from .manifest import parse_manifest
from .records import AssetRecord
from .scan import ScannedAsset, scan_downloaded
from .thumbnails import make_thumbnail

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]

#: 同期ログに残す件数の上限。
_LOG_LIMIT = 500


class SyncState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class SyncResult:
    added: int = 0
    updated: int = 0
    removed: int = 0
    unchanged: int = 0
    failed: int = 0
    log: list[str] = field(default_factory=list)


def _record_for(asset: ScannedAsset) -> AssetRecord:
    manifest = json.loads(asset.manifest_path.read_text(encoding="utf-8"))
    return AssetRecord(
        meta=parse_manifest(manifest),
        rel_dir=asset.rel_dir,
        resolutions=asset.resolutions,
        fingerprint=asset.fingerprint,
    )


def sync_once(
    db: Database,
    downloaded: Path | str,
    on_progress: ProgressCallback | None = None,
) -> SyncResult:
    """1回ぶんの同期。走査、差分判定、差分だけの解析、DBの更新をまとめて行う。"""
    scan = scan_downloaded(downloaded)
    result = SyncResult(log=[*scan.skipped, *scan.unmatched][:_LOG_LIMIT])

    known = db.fingerprints()
    changed = [asset for asset in scan.assets if known.get(asset.id) != asset.fingerprint]
    result.unchanged = len(scan.assets) - len(changed)

    total = len(changed)
    records: list[AssetRecord] = []
    thumbnails: list[tuple[str, bytes]] = []
    for done, asset in enumerate(changed, start=1):
        try:
            records.append(_record_for(asset))
        except (OSError, ValueError, KeyError) as error:
            result.failed += 1
            result.log.append(f"{asset.id}.json を読めなかった: {asset.rel_dir} ({error})")
            logger.warning("manifestの解析に失敗: %s (%s)", asset.manifest_path, error)
            continue
        if asset.preview_path is not None and (image := make_thumbnail(asset.preview_path)):
            thumbnails.append((asset.id, image))
        if asset.id in known:
            result.updated += 1
        else:
            result.added += 1
        if on_progress is not None:
            on_progress(done, total)

    if on_progress is not None and total == 0:
        on_progress(0, 0)

    db.replace_assets(records)
    for asset_id, image in thumbnails:
        db.put_thumbnail(asset_id, image)

    found = {asset.id for asset in scan.assets}
    gone = [asset_id for asset_id in known if asset_id not in found]
    db.delete_assets(gone)
    result.removed = len(gone)
    return result


class SyncService:
    """同期をバックグラウンドスレッドで走らせ、進捗を保持する。

    リクエスト処理では走らせない。同時に動くのは1つだけ。
    """

    def __init__(self, db: Database) -> None:
        self._db = db
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._state = SyncState.IDLE
        self._done = 0
        self._total = 0
        self._result: SyncResult | None = None
        self._error: str | None = None

    def status(self) -> dict[str, Any]:
        with self._lock:
            result = self._result
            status: dict[str, Any] = {
                "state": self._state,
                "running": self._state is SyncState.RUNNING,
                "done": self._done,
                "total": self._total,
                "error": self._error,
                "added": result.added if result else 0,
                "updated": result.updated if result else 0,
                "removed": result.removed if result else 0,
                "unchanged": result.unchanged if result else 0,
                "failed": result.failed if result else 0,
                "log": list(result.log) if result else [],
            }
        return status

    def start(self, downloaded: Path | str, on_progress: ProgressCallback | None = None) -> bool:
        """同期を開始する。すでに走っていれば ``False`` を返す。"""
        with self._lock:
            if self._state is SyncState.RUNNING:
                return False
            self._state = SyncState.RUNNING
            self._done = 0
            self._total = 0
            self._result = None
            self._error = None
            thread = threading.Thread(
                target=self._run,
                args=(Path(downloaded), on_progress),
                name="megascans-sync",
                daemon=True,
            )
            self._thread = thread
        thread.start()
        return True

    def wait(self, timeout: float | None = None) -> None:
        with self._lock:
            thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def _progress(self, done: int, total: int) -> None:
        with self._lock:
            self._done = done
            self._total = total

    def _run(self, downloaded: Path, on_progress: ProgressCallback | None) -> None:
        def report(done: int, total: int) -> None:
            self._progress(done, total)
            if on_progress is not None:
                on_progress(done, total)

        try:
            result = sync_once(self._db, downloaded, on_progress=report)
        except Exception as error:  # noqa: BLE001 - 状態として持ち帰る
            logger.exception("同期に失敗した: %s", downloaded)
            with self._lock:
                self._state = SyncState.ERROR
                self._error = str(error)
            return
        with self._lock:
            self._state = SyncState.DONE
            self._result = result
            self._error = None
