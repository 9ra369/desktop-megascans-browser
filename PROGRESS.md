# 実装進捗

CLAUDE.md の実装順にそったチェックリスト。設計の正は `docs/design.md`。

## 準備

- [x] `git init -b main`
- [x] `origin` に `https://github.com/9ra369/desktop-megascans-browser.git` を設定
- [x] `git fetch origin`（リモートは空。統合する履歴なし）
- [x] PROGRESS.md 作成
- [x] `uv sync`

## 1. core：ファイル名解析、フィンガープリント、カテゴリと検索文字列の生成

- [x] `core/naming.py`：ファイル名から解像度を取得、Billboard判定、フォルダ名から `{id}` を取得
- [x] `core/fingerprint.py`：相対パス・サイズ・更新日時からハッシュを生成
- [x] `core/manifest.py`：`{id}.json` からメタデータ、カテゴリパス、`search_text` を生成
- [x] テスト：フィクスチャ3件の全449ファイルで解像度の解析結果がJSONの値と一致する

## 2. core：SQLiteスキーマと検索

- [ ] `core/db.py`：`assets` / `asset_categories` / `thumbnails` / `app_meta`、WALモード
- [ ] 文字検索（`LIKE`）、カテゴリ絞り込み、カテゴリツリーと件数
- [ ] テスト

## 3. core：Downloadedの走査、差分判定、同期

- [ ] `core/scan.py`：`Downloaded/{3d,3dplant,surface}/{folder}/` の2階層走査
- [ ] `core/thumbnails.py`：`{id}_Preview.png` からサムネイル生成（Pillow）
- [ ] `core/sync.py`：差分判定、同期の実行、進捗、同時実行は1つだけ
- [ ] テスト

## 4. api：FastAPIのエンドポイントと認証

- [ ] トークン認証、CORS、`127.0.0.1` のみ待ち受け
- [ ] `/health` `/settings` `/assets` `/assets/{id}` `/categories` `/thumbnails/{id}` `/sync` `/sync/status`
- [ ] 起動時にポートとトークンを標準出力へ出す
- [ ] テスト

## 5. app：Electronの起動処理とPythonの起動・終了管理

- [ ] メインプロセス：Pythonの起動・終了、ウィンドウ、Explorerを開く、Downloaded選択ダイアログ
- [ ] preload：`contextBridge` で許可した操作だけ公開
- [ ] Explorerを開くときのDownloaded配下チェック

## 6. app：React画面

- [ ] グリッド、検索、カテゴリ、詳細、初回設定

## 7. 実際のDownloadedで初回同期を実行し、ログを確認する

- [ ] 未着手（実機のDownloadedのパスが必要）

## 最終検証

- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format .`
- [ ] `npm run build`（app）
- [ ] `npx tsc --noEmit`（app）
- [ ] サブエージェントで差分を設計書と照合

## 判断の記録

- リモートが空だったため、統合する履歴はなし。ローカルの `main` をそのまま push する。
- `is_billboard` は大文字小文字を区別しない。設計の表記は `Billboard` だが、実ファイルの
  表記揺れで解像度を誤表示する方が害が大きいため。
- `search_text` はフィールド名を語に含めない。`semanticTags` と `environment` は値だけを辿り、
  値が入れ子の辞書（`locations` など）のときはキーを中身として扱う。`assetCategories` は
  キーが中身なのでキーを辿る。語は小文字・重複なし・ソート済みで空白区切りにした。
- `meta_json` から `lodDistance`、`points`、`splitSubmeshes` を落とした。設計が
  「ポリゴン数、バリエーション、LODはDBに持たない」としているため。
- カタログのファイル一覧のキーはタイプごとに異なる（surface=`maps`、3d=`components`+`meshes`、
  3dplant=`maps`+`billboards`+`models`）。この組で設計の449ファイルに一致することをテストで固定した。

## 未解決

- 実機の `Downloaded` のパスが不明なため、実装順7（実際のDownloadedでの初回同期）は人間の対応待ち。代わりに一時フォルダへ実物相当の構成を作って同期を検証する。
