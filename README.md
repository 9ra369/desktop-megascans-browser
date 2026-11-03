# Megascans Browser

Bridgeでダウンロード済みのMegascansアセットを検索・閲覧するデスクトップアプリです。

## 状態

設計完了、実装前です。設計は [docs/design.md](docs/design.md) を参照してください。

## 技術スタック

- 画面：Electron + React + TypeScript
- 処理：Python + FastAPI
- DB：SQLite

## セットアップ

Pythonバックエンドは `backend/` で次を実行します。

```powershell
uv sync
uv run pytest
```
