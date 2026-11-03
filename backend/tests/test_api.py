from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from downloaded import make_downloaded
from megascans_browser.api.app import create_app
from megascans_browser.api.settings import ServerSettings
from megascans_browser.core.db import Database
from megascans_browser.core.sync import sync_once

TOKEN = "test-token"


@pytest.fixture
def downloaded(tmp_path: Path) -> Path:
    return make_downloaded(tmp_path)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "test.db")
    database.connect()
    yield database
    database.close()


@pytest.fixture
def client(db: Database) -> Iterator[TestClient]:
    app = create_app(db, ServerSettings(token=TOKEN))
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {TOKEN}"
        yield test_client


@pytest.fixture
def filled(client: TestClient, db: Database, downloaded: Path) -> TestClient:
    db.set_meta("downloaded_path", str(downloaded))
    sync_once(db, downloaded)
    return client


# ------------------------------------------------------------------------ 認証


def test_health_needs_no_token(client: TestClient) -> None:
    response = client.get("/health", headers={"Authorization": ""})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_a_request_without_a_token_is_rejected(client: TestClient) -> None:
    response = client.get("/assets", headers={"Authorization": ""})

    assert response.status_code == 401


def test_a_request_with_the_wrong_token_is_rejected(client: TestClient) -> None:
    response = client.get("/assets", headers={"Authorization": "Bearer nope"})

    assert response.status_code == 401


def test_the_token_can_come_from_the_query(client: TestClient) -> None:
    response = client.get("/assets", params={"token": TOKEN}, headers={"Authorization": ""})

    assert response.status_code == 200


def test_the_wrong_token_in_the_query_is_rejected(client: TestClient) -> None:
    response = client.get("/assets", params={"token": "nope"}, headers={"Authorization": ""})

    assert response.status_code == 401


# --------------------------------------------------------------------- settings


def test_settings_is_empty_before_the_first_setup(client: TestClient) -> None:
    body = client.get("/settings").json()

    assert body["downloaded_path"] is None
    assert body["configured"] is False


def test_put_settings_stores_the_downloaded_path(client: TestClient, downloaded: Path) -> None:
    response = client.put("/settings", json={"downloaded_path": str(downloaded)})

    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert client.get("/settings").json()["downloaded_path"] == str(downloaded)


def test_put_settings_rejects_a_path_that_is_not_a_folder(
    client: TestClient, tmp_path: Path
) -> None:
    response = client.put("/settings", json={"downloaded_path": str(tmp_path / "missing")})

    assert response.status_code == 400


def test_put_settings_rejects_a_folder_without_any_asset_type(
    client: TestClient, tmp_path: Path
) -> None:
    empty = tmp_path / "NotDownloaded"
    empty.mkdir()

    response = client.put("/settings", json={"downloaded_path": str(empty)})

    assert response.status_code == 400


# ----------------------------------------------------------------------- assets


def test_assets_is_empty_before_the_first_sync(client: TestClient) -> None:
    body = client.get("/assets").json()

    assert body["total"] == 0
    assert body["items"] == []


def test_assets_lists_every_synced_asset(filled: TestClient) -> None:
    body = filled.get("/assets").json()

    assert body["total"] == 3
    assert {item["id"] for item in body["items"]} == {"wlrvaf3", "xiwcfassc", "wfypejzha"}


def test_an_asset_in_the_list_carries_what_the_grid_needs(filled: TestClient) -> None:
    item = next(item for item in filled.get("/assets").json()["items"] if item["id"] == "wlrvaf3")

    assert item["name"] == "Concrete Pavement"
    assert item["type"] == "surface"
    assert item["resolutions"] == ["2K", "4K"]
    assert item["average_color"] == "#000000"


def test_assets_filters_by_query(filled: TestClient) -> None:
    body = filled.get("/assets", params={"q": "pavement"}).json()

    assert [item["id"] for item in body["items"]] == ["wlrvaf3"]
    assert body["total"] == 1


def test_assets_filters_by_type(filled: TestClient) -> None:
    body = filled.get("/assets", params={"type": "3dplant"}).json()

    assert [item["id"] for item in body["items"]] == ["wfypejzha"]


def test_assets_filters_by_category(filled: TestClient) -> None:
    body = filled.get("/assets", params={"category": "surface/concrete/rough"}).json()

    assert [item["id"] for item in body["items"]] == ["wlrvaf3"]


def test_assets_paginates(filled: TestClient) -> None:
    body = filled.get("/assets", params={"limit": 2, "offset": 0}).json()

    assert len(body["items"]) == 2
    assert body["total"] == 3


def test_assets_rejects_an_unknown_type(filled: TestClient) -> None:
    assert filled.get("/assets", params={"type": "brush"}).status_code == 422


# ------------------------------------------------------------------- asset 詳細


def test_asset_detail_carries_the_metadata(filled: TestClient) -> None:
    body = filled.get("/assets/wlrvaf3").json()

    assert body["name"] == "Concrete Pavement"
    assert body["rel_dir"] == "surface/Concrete Pavement_wlrvaf3"
    assert body["resolutions"] == ["2K", "4K"]
    assert body["categories"] == ["surface", "surface/concrete", "surface/concrete/rough"]
    assert body["meta"]["scanArea"] == "2x2 m"


def test_asset_detail_carries_the_absolute_folder(filled: TestClient, downloaded: Path) -> None:
    body = filled.get("/assets/wlrvaf3").json()

    assert Path(body["abs_dir"]) == downloaded / "surface" / "Concrete Pavement_wlrvaf3"


def test_asset_detail_is_404_for_an_unknown_id(filled: TestClient) -> None:
    assert filled.get("/assets/nope").status_code == 404


# ------------------------------------------------------------------- categories


def test_categories_returns_the_tree_with_counts(filled: TestClient) -> None:
    items = filled.get("/categories").json()["items"]
    by_path = {item["path"]: item for item in items}

    assert by_path["surface"]["count"] == 1
    assert by_path["surface"]["name"] == "surface"
    assert by_path["surface/concrete"]["name"] == "concrete"
    assert by_path["surface/concrete"]["depth"] == 1


def test_categories_is_empty_before_the_first_sync(client: TestClient) -> None:
    assert client.get("/categories").json()["items"] == []


# ------------------------------------------------------------------- thumbnails


def test_thumbnail_returns_a_png(filled: TestClient) -> None:
    response = filled.get("/thumbnails/wlrvaf3")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_thumbnail_accepts_the_token_in_the_query(filled: TestClient) -> None:
    response = filled.get(
        "/thumbnails/wlrvaf3", params={"token": TOKEN}, headers={"Authorization": ""}
    )

    assert response.status_code == 200


def test_thumbnail_is_404_when_missing(filled: TestClient) -> None:
    assert filled.get("/thumbnails/nope").status_code == 404


# ------------------------------------------------------------------------- sync


def test_sync_is_idle_before_it_runs(client: TestClient) -> None:
    body = client.get("/sync/status").json()

    assert body["state"] == "idle"
    assert body["running"] is False


def test_post_sync_runs_a_sync(filled: TestClient) -> None:
    assert filled.post("/sync").status_code == 202

    for _ in range(600):
        body = filled.get("/sync/status").json()
        if not body["running"]:
            break
    assert body["state"] == "done"
    assert filled.get("/assets").json()["total"] == 3


def test_post_sync_fails_without_a_downloaded_path(client: TestClient) -> None:
    assert client.post("/sync").status_code == 409


def test_post_sync_while_one_runs_returns_409(filled: TestClient) -> None:
    import unittest.mock

    with unittest.mock.patch.object(type(filled.app.state.sync), "start", return_value=False):
        assert filled.post("/sync").status_code == 409


# -------------------------------------------------------------------- CORS など


def test_cors_allows_only_the_app_origin(client: TestClient) -> None:
    allowed = client.get(
        "/health", headers={"Origin": "http://localhost:5173", "Authorization": ""}
    )
    other = client.get("/health", headers={"Origin": "https://example.com", "Authorization": ""})

    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in other.headers


def test_server_settings_generate_a_token() -> None:
    assert len(ServerSettings().token) >= 32
    assert ServerSettings().token != ServerSettings().token


def test_server_settings_listen_on_loopback_only() -> None:
    assert ServerSettings().host == "127.0.0.1"
