import sqlite3
from pathlib import Path

import pytest

from megascans_browser.core.db import Database
from megascans_browser.core.manifest import AssetMeta
from megascans_browser.core.records import AssetRecord


def record(
    asset_id: str,
    name: str,
    asset_type: str,
    category_paths: list[str],
    search_text: str = "",
    resolutions: list[str] | None = None,
    fingerprint: str = "f",
) -> AssetRecord:
    return AssetRecord(
        meta=AssetMeta(
            id=asset_id,
            name=name,
            type=asset_type,
            category_paths=category_paths,
            search_text=search_text or f"{name.lower()} {asset_id}",
            average_color="#112233",
            meta={"scanArea": "2x2 m"},
        ),
        rel_dir=f"{asset_type}/{name}_{asset_id}",
        resolutions=resolutions if resolutions is not None else ["2K", "4K"],
        fingerprint=fingerprint,
    )


SAMPLE = [
    record("wlrvaf3", "Concrete Pavement", "surface", ["surface", "surface/concrete"]),
    record("aaa", "Mossy Rock", "3d", ["3d", "3d/nature", "3d/nature/rock"], "mossy rock moss"),
    record("bbb", "Dragon Tree", "3dplant", ["3dplant", "3dplant/houseplant"], "dragon tree"),
]


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.db")
    database.connect()
    yield database
    database.close()


@pytest.fixture
def filled(db: Database) -> Database:
    db.replace_assets(SAMPLE)
    return db


def test_connect_creates_the_four_tables(db: Database) -> None:
    names = {
        row["name"]
        for row in db.connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }

    assert {"assets", "asset_categories", "thumbnails", "app_meta"} <= names


def test_connect_uses_wal(db: Database) -> None:
    mode = db.connection.execute("PRAGMA journal_mode").fetchone()[0]

    assert mode.lower() == "wal"


def test_connect_enables_foreign_keys(db: Database) -> None:
    assert db.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_rows_come_back_as_mappings(db: Database) -> None:
    assert isinstance(db.connection.execute("SELECT 1 AS one").fetchone(), sqlite3.Row)


def test_replace_assets_stores_every_column(filled: Database) -> None:
    asset = filled.asset("wlrvaf3")

    assert asset is not None
    assert asset["name"] == "Concrete Pavement"
    assert asset["type"] == "surface"
    assert asset["rel_dir"] == "surface/Concrete Pavement_wlrvaf3"
    assert asset["average_color"] == "#112233"
    assert asset["resolutions"] == ["2K", "4K"]
    assert asset["meta"] == {"scanArea": "2x2 m"}
    assert asset["categories"] == ["surface", "surface/concrete"]


def test_asset_returns_none_for_an_unknown_id(filled: Database) -> None:
    assert filled.asset("missing") is None


def test_replace_assets_stores_the_category_rows(filled: Database) -> None:
    rows = filled.connection.execute(
        "SELECT asset_id, category_path FROM asset_categories ORDER BY asset_id, category_path"
    ).fetchall()

    assert [tuple(row) for row in rows] == [
        ("aaa", "3d"),
        ("aaa", "3d/nature"),
        ("aaa", "3d/nature/rock"),
        ("bbb", "3dplant"),
        ("bbb", "3dplant/houseplant"),
        ("wlrvaf3", "surface"),
        ("wlrvaf3", "surface/concrete"),
    ]


def test_replace_assets_replaces_an_existing_asset(filled: Database) -> None:
    filled.replace_assets([record("aaa", "Renamed Rock", "3d", ["3d", "3d/industrial"])])

    asset = filled.asset("aaa")
    assert asset is not None
    assert asset["name"] == "Renamed Rock"
    assert asset["categories"] == ["3d", "3d/industrial"]
    assert filled.count() == 3


def test_search_without_a_query_returns_every_asset_by_name(filled: Database) -> None:
    assert [row["id"] for row in filled.search()] == ["wlrvaf3", "bbb", "aaa"]


def test_search_matches_the_search_text(filled: Database) -> None:
    assert [row["id"] for row in filled.search(query="moss")] == ["aaa"]


def test_search_is_case_insensitive(filled: Database) -> None:
    assert [row["id"] for row in filled.search(query="MOSS")] == ["aaa"]


def test_search_treats_every_word_as_required(filled: Database) -> None:
    assert [row["id"] for row in filled.search(query="dragon tree")] == ["bbb"]
    assert filled.search(query="dragon rock") == []


def test_search_escapes_like_wildcards(filled: Database) -> None:
    assert filled.search(query="%") == []
    assert filled.search(query="_") == []


def test_search_filters_by_type(filled: Database) -> None:
    assert [row["id"] for row in filled.search(asset_type="3dplant")] == ["bbb"]


def test_search_filters_by_category(filled: Database) -> None:
    assert [row["id"] for row in filled.search(category="3d/nature/rock")] == ["aaa"]


def test_search_by_category_is_an_exact_match(filled: Database) -> None:
    assert filled.search(category="3d/nature/ro") == []


def test_search_combines_the_filters(filled: Database) -> None:
    assert filled.search(query="moss", category="3dplant") == []


def test_search_paginates(filled: Database) -> None:
    assert [row["id"] for row in filled.search(limit=1)] == ["wlrvaf3"]
    assert [row["id"] for row in filled.search(limit=1, offset=1)] == ["bbb"]


def test_search_rows_carry_the_list_columns(filled: Database) -> None:
    row = filled.search(query="moss")[0]

    assert row["resolutions"] == ["2K", "4K"]
    assert row["average_color"] == "#112233"
    assert "categories" not in row


def test_count_honours_the_filters(filled: Database) -> None:
    assert filled.count() == 3
    assert filled.count(asset_type="3d") == 1
    assert filled.count(category="3d/nature") == 1
    assert filled.count(query="moss") == 1


def test_categories_returns_every_path_with_its_count(filled: Database) -> None:
    assert filled.categories() == [
        {"path": "3d", "count": 1},
        {"path": "3d/nature", "count": 1},
        {"path": "3d/nature/rock", "count": 1},
        {"path": "3dplant", "count": 1},
        {"path": "3dplant/houseplant", "count": 1},
        {"path": "surface", "count": 1},
        {"path": "surface/concrete", "count": 1},
    ]


def test_categories_counts_every_asset_under_a_path(db: Database) -> None:
    db.replace_assets(
        [
            record("a1", "One", "3d", ["3d", "3d/nature"]),
            record("a2", "Two", "3d", ["3d", "3d/nature", "3d/nature/rock"]),
        ]
    )

    assert db.categories() == [
        {"path": "3d", "count": 2},
        {"path": "3d/nature", "count": 2},
        {"path": "3d/nature/rock", "count": 1},
    ]


def test_fingerprints_maps_every_id(filled: Database) -> None:
    assert filled.fingerprints() == {"wlrvaf3": "f", "aaa": "f", "bbb": "f"}


def test_delete_assets_removes_the_rows_and_the_categories(filled: Database) -> None:
    filled.delete_assets(["aaa"])

    assert filled.asset("aaa") is None
    assert filled.count() == 2
    assert not filled.connection.execute(
        "SELECT 1 FROM asset_categories WHERE asset_id = 'aaa'"
    ).fetchall()


def test_delete_assets_removes_the_thumbnail(filled: Database) -> None:
    filled.put_thumbnail("aaa", b"png")
    filled.delete_assets(["aaa"])

    assert filled.thumbnail("aaa") is None


def test_delete_assets_accepts_an_empty_list(filled: Database) -> None:
    filled.delete_assets([])

    assert filled.count() == 3


def test_thumbnail_round_trip(filled: Database) -> None:
    filled.put_thumbnail("aaa", b"png-bytes")

    assert filled.thumbnail("aaa") == b"png-bytes"


def test_thumbnail_is_none_when_missing(filled: Database) -> None:
    assert filled.thumbnail("aaa") is None


def test_put_thumbnail_replaces_the_previous_one(filled: Database) -> None:
    filled.put_thumbnail("aaa", b"one")
    filled.put_thumbnail("aaa", b"two")

    assert filled.thumbnail("aaa") == b"two"


def test_app_meta_round_trip(db: Database) -> None:
    db.set_meta("downloaded_path", "D:/Megascans/Downloaded")

    assert db.get_meta("downloaded_path") == "D:/Megascans/Downloaded"


def test_app_meta_returns_the_default_when_missing(db: Database) -> None:
    assert db.get_meta("downloaded_path") is None
    assert db.get_meta("downloaded_path", "fallback") == "fallback"


def test_app_meta_survives_replace_assets(filled: Database) -> None:
    filled.set_meta("downloaded_path", "D:/Megascans/Downloaded")
    filled.replace_assets(SAMPLE)

    assert filled.get_meta("downloaded_path") == "D:/Megascans/Downloaded"


def test_reopening_the_database_keeps_the_data(tmp_path: Path) -> None:
    path = tmp_path / "test.db"
    first = Database(path)
    first.connect()
    first.replace_assets(SAMPLE)
    first.set_meta("downloaded_path", "D:/x")
    first.close()

    second = Database(path)
    second.connect()
    try:
        assert second.count() == 3
        assert second.get_meta("downloaded_path") == "D:/x"
    finally:
        second.close()


def test_connect_creates_the_parent_directory(tmp_path: Path) -> None:
    database = Database(tmp_path / "nested" / "dir" / "test.db")
    database.connect()
    try:
        assert database.count() == 0
    finally:
        database.close()
