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

- [x] `core/db.py`：`assets` / `asset_categories` / `thumbnails` / `app_meta`、WALモード
- [x] 文字検索（`LIKE`）、カテゴリ絞り込み、カテゴリツリーと件数
- [x] `core/records.py`：core内で受け渡す `AssetRecord`
- [x] テスト

## 3. core：Downloadedの走査、差分判定、同期

- [x] `core/scan.py`：`Downloaded/{3d,3dplant,surface}/{folder}/` の2階層走査
- [x] `core/thumbnails.py`：`{id}_Preview.png` からサムネイル生成（Pillow）
- [x] `core/sync.py`：差分判定、同期の実行、進捗、同時実行は1つだけ
- [x] テスト

## 4. api：FastAPIのエンドポイントと認証

- [x] トークン認証、CORS、`127.0.0.1` のみ待ち受け
- [x] `/health` `/settings` `/assets` `/assets/{id}` `/categories` `/thumbnails/{id}` `/sync` `/sync/status`
- [x] 起動時にポートとトークンを標準出力へ出す
- [x] テスト

## 5. app：Electronの起動処理とPythonの起動・終了管理

- [x] メインプロセス：Pythonの起動・終了、ウィンドウ、Explorerを開く、Downloaded選択ダイアログ
- [x] preload：`contextBridge` で許可した操作だけ公開
- [x] Explorerを開くときのDownloaded配下チェック
- [x] テスト（起動の行の解析、パス判定、実際にbackendを起動する結合テスト）

## 6. app：React画面

- [x] グリッド、検索、カテゴリ、詳細、初回設定
- [x] テスト（APIクライアント、カテゴリツリー、同期ラベル、各コンポーネント）

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
- 検索語は空白で区切り、すべてを含む行だけを返す（AND）。`%` と `_` は `ESCAPE` で
  エスケープし、検索語として扱う。
- `resolutions` は `", "` 区切りの文字列として1列に入れた（設計のスキーマが `TEXT`）。
- 接続は `check_same_thread=False` で共有し、書き込みは `threading.Lock` で直列化した。
  同期がバックグラウンドスレッドで走る前提のため。
- Vite + `tsc` の2本立てにした。レンダラーはVite、メインとpreloadは `tsc` で
  CommonJSへ出す。`electron-vite` のような追加の枠組みは入れていない。
- テストランナーは `vitest`（設計のスタック表にはないが、テストを書くために必要）。
  Reactのコンポーネントは `@testing-library/react` で確認する。
- Pythonは `backend/.venv` のPythonを直に起動する。`uv run` を挟むとPythonが孫
  プロセスになり、Electronの終了時に取り残された（実測で確認）。`.venv` がなければ
  `uv run` に落とす。
- Windowsでは `.venv/Scripts/python.exe` 自体が本体のインタプリタを子として起動する
  ため、終了は `taskkill /T /F` でプロセスツリーごと止める。
- `/health` だけ認証なし。メインプロセスが接続を確かめる前にトークンを使えないため。
- トークンは `Authorization: Bearer` のほか、クエリの `token` でも受け取る。`<img>` は
  ヘッダーを付けられないという設計の記述に合わせた。比較は `secrets.compare_digest`。
- `uvicorn` の `fd=` 渡しはWindowsで動かないため、先に `bind` したソケットを
  `uvicorn.Server.run(sockets=[...])` へ渡す。ポートを起動前に確定させるために
  ソケットを先に作る形は変えていない。
- 起動の行は `MEGASCANS_BROWSER_READY {"port":..,"token":..}` の1行。メインプロセスは
  この目印を探す。
- `PUT /settings` は、フォルダが存在し `3d` / `3dplant` / `surface` のいずれかを含むことだけ
  確認する。
- `/assets` の `type` は `3d` / `3dplant` / `surface` に限る（`atlas` などは422）。
- サムネイルの長辺は320px。グリッド1枚ぶんで、元より大きくはしない。
- 同期ログは走査時のスキップ・規則外ファイルと、manifestの解析失敗をまとめて
  `SyncResult.log` に入れ、上限500件にした。
- `{id}.json` の解析に失敗したアセットはDBに入れず、他のアセットの同期は続ける。
- 解像度の規則外として記録するのは、Billboardでなく解像度が読めず、拡張子が
  `.abc/.fbx/.json/.mtl/.obj/.ztl` でもなく、`_Preview.png` でもないファイルだけ。
  メッシュやプレビューは解像度を持たないのが普通なので、ログを埋めないようにした。
- カタログのファイル一覧のキーはタイプごとに異なる（surface=`maps`、3d=`components`+`meshes`、
  3dplant=`maps`+`billboards`+`models`）。この組で設計の449ファイルに一致することをテストで固定した。

## 未解決

- 実機の `Downloaded` のパスが不明なため、実装順7（実際のDownloadedでの初回同期）は人間の対応待ち。代わりに一時フォルダへ実物相当の構成を作って同期を検証する。
