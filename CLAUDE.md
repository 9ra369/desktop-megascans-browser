# Megascans Browser

Bridgeでダウンロード済みのMegascansアセットを検索・閲覧する、Windows向けのデスクトップアプリ。

実装の前に `docs/design.md` を読むこと。設計はこのファイルを正とし、変更が必要なら実装前にユーザーへ確認する。

## 構成

```text
app/                     Electron + React + TypeScript（未作成）
backend/
  src/megascans_browser/
    core/                検索、同期、DB、サムネイル生成
    api/                 FastAPI
  tests/
    fixtures/manifests/  実物の {id}.json（surface / 3d / 3dplant）
docs/design.md           設計書
```

## 実装順

1. `core`：ファイル名解析、フィンガープリント、カテゴリと検索文字列の生成
2. `core`：SQLiteスキーマと検索
3. `core`：Downloadedの走査、差分判定、同期
4. `api`：FastAPIのエンドポイントと認証
5. `app`：Electronの起動処理とPythonの起動・終了管理
6. `app`：React画面（グリッド、検索、カテゴリ、詳細、初回設定）
7. 実際のDownloadedで初回同期を実行し、ログを確認する

## 守ること

- `core` は `fastapi` とElectronに依存させない
- Downloaded配下へ書き込まない
- `assetsData.json` は読まない
- `atlas`、`brush`、`DHI` は走査しない
- 検索と一覧表示では `{id}.json` と実ファイルを読まない
- 解像度は実ファイルの名前から取得し、JSONのファイル一覧を一覧の根拠にしない
- 解像度の集計からBillboardを除外する
- パスはDownloadedからの相対パスで保存し、区切りは `/` に統一する
- サーバーの待ち受けは `127.0.0.1` のみにする
- 長い処理をリクエスト処理やUIスレッドで実行しない

## フィクスチャ

`backend/tests/fixtures/manifests/` のJSONは入手可能なファイルのカタログで、ダウンロード済みの一覧ではない。

| ファイル | タイプ | 掲載ファイル数 |
|---|---|---|
| `wlrvaf3.json` | surface | 72 |
| `xiwcfassc.json` | 3d | 143 |
| `wfypejzha.json` | 3dplant | 234 |

## コマンド

`backend/` で実行する。

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run ruff format .
```

実際のDownloadedの場所は、必要になったらユーザーに確認する。
