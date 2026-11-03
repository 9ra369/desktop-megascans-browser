"""FastAPIのエンドポイントと認証。

HTTPの受付と認証だけを担当し、検索・同期・サムネイルは ``core`` に任せる。
長い処理はリクエスト処理では走らせない。
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..core.db import Database
from ..core.naming import ASSET_TYPES
from ..core.sync import SyncService
from .settings import DOWNLOADED_PATH_KEY, ServerSettings

AssetType = Literal["3d", "3dplant", "surface"]


class SettingsBody(BaseModel):
    downloaded_path: str


class SettingsResponse(BaseModel):
    downloaded_path: str | None
    configured: bool


class AssetListItem(BaseModel):
    id: str
    name: str
    type: str
    rel_dir: str
    average_color: str
    resolutions: list[str]


class AssetListResponse(BaseModel):
    items: list[AssetListItem]
    total: int
    limit: int
    offset: int


class AssetDetail(AssetListItem):
    abs_dir: str | None
    categories: list[str]
    meta: dict[str, Any]
    has_thumbnail: bool


class CategoryItem(BaseModel):
    path: str
    name: str
    parent: str | None
    depth: int
    count: int


class CategoryListResponse(BaseModel):
    items: list[CategoryItem]


class SyncStatusResponse(BaseModel):
    state: str
    running: bool
    done: int
    total: int
    error: str | None
    added: int
    updated: int
    removed: int
    unchanged: int
    failed: int
    log: list[str]


class SyncStartedResponse(BaseModel):
    started: bool


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() == "bearer" and value:
        return value
    return request.query_params.get("token")


def _looks_like_downloaded(path: Path) -> bool:
    return path.is_dir() and any((path / name).is_dir() for name in ASSET_TYPES)


def _category_item(path: str, count: int) -> CategoryItem:
    parent, _, name = path.rpartition("/")
    return CategoryItem(
        path=path,
        name=name or path,
        parent=parent or None,
        depth=path.count("/"),
        count=count,
    )


def create_app(db: Database, settings: ServerSettings | None = None) -> FastAPI:
    """DBと設定からFastAPIアプリを組み立てる。"""
    settings = settings or ServerSettings()
    sync = SyncService(db)

    app = FastAPI(title="Megascans Browser", version="0.1.0", docs_url=None, redoc_url=None)
    app.state.db = db
    app.state.sync = sync
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "PUT", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def require_token(request: Request) -> None:
        token = _bearer_token(request)
        if token is None or not secrets.compare_digest(token, settings.token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="トークンが正しくない"
            )

    authorized = [Depends(require_token)]

    def downloaded_root() -> Path | None:
        stored = db.get_meta(DOWNLOADED_PATH_KEY)
        return Path(stored) if stored else None

    # ------------------------------------------------------------------ /health

    @app.get("/health")
    def health() -> dict[str, str]:
        """起動確認。メインプロセスがここで接続を確かめるので認証はいらない。"""
        return {"status": "ok", "version": app.version}

    # ---------------------------------------------------------------- /settings

    @app.get("/settings", dependencies=authorized)
    def get_settings() -> SettingsResponse:
        stored = db.get_meta(DOWNLOADED_PATH_KEY)
        return SettingsResponse(downloaded_path=stored, configured=stored is not None)

    @app.put("/settings", dependencies=authorized)
    def put_settings(body: SettingsBody) -> SettingsResponse:
        path = Path(body.downloaded_path)
        if not path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="フォルダが見つからない"
            )
        if not _looks_like_downloaded(path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="3d / 3dplant / surface のいずれも見つからない",
            )
        db.set_meta(DOWNLOADED_PATH_KEY, str(path))
        return SettingsResponse(downloaded_path=str(path), configured=True)

    # ------------------------------------------------------------------ /assets

    @app.get("/assets", dependencies=authorized)
    def list_assets(
        q: Annotated[str | None, Query(max_length=200)] = None,
        type: AssetType | None = None,
        category: Annotated[str | None, Query(max_length=200)] = None,
        limit: Annotated[int, Query(ge=1, le=2000)] = 200,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> AssetListResponse:
        """一覧と検索。DBだけで答える。"""
        rows = db.search(query=q, asset_type=type, category=category, limit=limit, offset=offset)
        return AssetListResponse(
            items=[AssetListItem(**row) for row in rows],
            total=db.count(query=q, asset_type=type, category=category),
            limit=limit,
            offset=offset,
        )

    @app.get("/assets/{asset_id}", dependencies=authorized)
    def get_asset(asset_id: str) -> AssetDetail:
        asset = db.asset(asset_id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="アセットがない")
        root = downloaded_root()
        asset.pop("fingerprint", None)
        return AssetDetail(
            **asset,
            abs_dir=str(root / asset["rel_dir"]) if root is not None else None,
            has_thumbnail=db.thumbnail(asset_id) is not None,
        )

    # -------------------------------------------------------------- /categories

    @app.get("/categories", dependencies=authorized)
    def list_categories() -> CategoryListResponse:
        return CategoryListResponse(
            items=[_category_item(row["path"], row["count"]) for row in db.categories()]
        )

    # -------------------------------------------------------------- /thumbnails

    @app.get("/thumbnails/{asset_id}", dependencies=authorized)
    def get_thumbnail(asset_id: str) -> Response:
        """``<img>`` から読むので、トークンはクエリでも受け取る。"""
        image = db.thumbnail(asset_id)
        if image is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="サムネイルがない")
        return Response(
            content=image,
            media_type="image/png",
            headers={"Cache-Control": "no-cache"},
        )

    # -------------------------------------------------------------------- /sync

    @app.post("/sync", status_code=status.HTTP_202_ACCEPTED, dependencies=authorized)
    def start_sync() -> SyncStartedResponse:
        """同期を始めるだけ。走査と解析はバックグラウンドスレッドで行う。"""
        root = downloaded_root()
        if root is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Downloadedの場所が未設定"
            )
        if not sync.start(root):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="同期中")
        return SyncStartedResponse(started=True)

    @app.get("/sync/status", dependencies=authorized)
    def sync_status() -> SyncStatusResponse:
        return SyncStatusResponse(**sync.status())

    return app
