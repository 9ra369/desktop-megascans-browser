# Megascans Browser

Bridgeでダウンロード済みのMegascansアセットを検索・閲覧するデスクトップアプリです。

## 状態

実装済みです。設計は [docs/design.md](docs/design.md)、進捗は [PROGRESS.md](PROGRESS.md) を参照してください。

実機の `Downloaded` での初回同期は未実施です（PROGRESS.md の「未解決」を参照）。

## 技術スタック

- 画面：Electron + React + TypeScript
- 処理：Python + FastAPI
- DB：SQLite

## セットアップ

Pythonバックエンドは `backend/` で次を実行します。

```powershell
uv sync
uv run pytest
uv run ruff check .
```

Electron側は `app/` で次を実行します。

```powershell
npm install
npm test
npm run typecheck
```

## 起動

`backend/` で `uv sync` を済ませてから、`app/` で次を実行します。

```powershell
npm start
```

ElectronがPythonサーバーを起動し、初回は `Downloaded` フォルダを選ぶ画面が出ます。
`3d`、`3dplant`、`surface` が入っているフォルダを選んでください。
