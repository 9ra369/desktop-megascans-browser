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

- [x] 実機の `Downloaded` で初回同期を実行し、ログを確認した
      （`C:\Users\kuram\Megascans_Library\Downloaded`、ダウンロード済み4件、783MB）
- [x] アプリ（`electron .`）から起動して、同期・サムネイル・終了まで確認した

### 実機の構成（走査して分かったこと）

| 項目 | 実機の内容 |
|---|---|
| Downloaded直下 | `3d`、`3dplant`、`atlas`、`brush`、`DHI`、`surface`、`assetsData.json` |
| ダウンロード済み | 4件（3d 1、3dplant 1、surface 2）、実ファイル166件 |
| フォルダ名 | `concrete_rough_wlrvaf3`、`industrial_storage_xiwcfassc` など `{カテゴリ}_{サブカテゴリ}_{id}` |
| `{id}.json` | 4件すべてにある |
| `{id}_Preview.png` | 4件すべてにある |
| テクスチャの置き場 | surface/3dは直下、3dplantは `Textures/Atlas/`・`Textures/Billboard/` |
| メッシュ | 3dは `{id}_High.fbx`・`{id}_LOD0..4.fbx`、3dplantは `Var1/`〜`Var8/` の `VarN_LODn.fbx` |
| **`Thumbs/{1k,2k,4k}/`** | **設計で想定していなかったフォルダ。Bridgeの画面用の縮小画像が入る** |
| **`previews/`** | **設計で想定していなかったフォルダ。`*_Popup_3840_sp.jpg` などのプレビュー画像** |
| 実際の解像度 | 4件すべて4Kのみ |
| `atlas` / `brush` | 空 |
| `DHI` | `assetsData.json` のみ（走査しない） |

### 実機で見つかって直した問題

| 問題 | 内容 | 対応 |
|---|---|---|
| **解像度の誤表示** | `Thumbs/{1k,2k,4k}/` を数えてしまい、4Kだけを持つ4件すべてが `1K, 2K, 4K` と表示されていた | `Thumbs/` と `previews/` を解像度の集計から除外（Billboardと同じ理由） |
| **同期ログのノイズ** | `previews/` のプレビュー画像が毎回「解像度の規則に合わない」として記録されていた | 補助フォルダは規則外として数えない。実機のログは0件になった |
| **SQLiteの並行アクセスで500** | アプリ起動時に `/thumbnails` の読み出しと同期の書き込みが重なり `sqlite3.InterfaceError: bad parameter or other API misuse` | 接続をスレッドごとに分けた（WALは接続を分ける前提）。書き込みロックだけでは読み書きの衝突を防げていなかった |

3つめは、既存の「同期中も検索できる」テストが進捗コールバックで同期を止めていて
実際には同時アクセスが起きておらず、検出できていなかった。読み書きを150回ずつ重ねる
回帰テスト（`tests/test_db_concurrency.py`）を追加した。

テストのフォルダ構成（`tests/downloaded.py`）も実機で確認した形に差し替えた。

### 修正後の初回同期

```text
=== 走査 ===
見つかったアセット: 4
  xiwcfassc    3d       files=29   3d/industrial_storage_xiwcfassc        解像度 = ['4K']
  wfypejzha    3dplant  files=83   3dplant/3dplant_houseplant_wfypejzha   解像度 = ['4K']
  vlprbbt      surface  files=27   surface/concrete_rough_vlprbbt         解像度 = ['4K']
  wlrvaf3      surface  files=27   surface/concrete_rough_wlrvaf3         解像度 = ['4K']
スキップ 0 件
規則外 0 件

=== 初回同期 ===
added=4 updated=0 removed=0 unchanged=0 failed=0
ログ 0 件
サムネイル 4 / 4 件

=== 2回目の同期 ===
added=0 updated=0 unchanged=4

=== カテゴリ ===
  3d 1 / 3d/industrial 1 / 3d/industrial/storage 1
  3dplant 1 / 3dplant/houseplant 1 / 3dplant/houseplant/flowerless 1
  surface 2 / surface/concrete 2 / surface/concrete/rough 2

=== 検索 ===
  concrete -> [vlprbbt, wlrvaf3]   dracaena -> [wfypejzha]   tarp -> [xiwcfassc]
```

アプリから起動した場合も同じ4件・サムネイル4件になり、ASGIのエラーは0件、
ウィンドウを閉じるとElectronとPythonの両方が0プロセスになることを確認した。

## 最終検証

- [x] `uv run pytest`：222 passed
- [x] `uv run ruff check .`：All checks passed!
- [x] `uv run ruff format --check .`：30 files already formatted
- [x] `npm test`（app）：58 passed
- [x] `npm run typecheck`（app）：エラーなし（renderer / main / tests の3プロジェクト）
- [x] `npm run build`（app）：renderer と main のビルド成功
- [x] 実際にElectronを起動して一連の動作を確認（下の「起動の確認」）
- [x] サブエージェントで差分を設計書と照合

### 起動の確認

`app/` で `npx electron .` を実行して確認した。

| 確認したこと | 結果 |
|---|---|
| ElectronがPythonサーバーを起動する | `.venv` のPythonが `--user-data <userData>` で起動 |
| `127.0.0.1` の空きポートで待ち受ける | ポート49444 |
| `/health` | `{"status":"ok","version":"0.1.0"}` |
| トークンなしのAPI | `/assets` が401 |
| ウィンドウを閉じるとPythonも止まる | Electron 0プロセス、backend 0プロセス（取り残しなし） |

## サブエージェントによる設計との照合（対応済み）

差分を `docs/design.md` と照合して指摘された項目への対応。

### 修正した要件違反

| 指摘 | 対応 |
|---|---|
| CORSが本番の画面を許可していない。本番のレンダラーは `file://` から読まれ `Origin: null` を送るため、全API呼び出しがブロックされる（実際に再現） | `ALLOWED_ORIGINS` に `"null"` を追加。preflightが200を返すことをテストで固定 |
| 起動失敗時にPythonが残る。`will-quit` が `connection === null` で即returnし、`bootstrap` の失敗時に `stop()` を呼んでいなかった | `bootstrap` の失敗時に `server.stop()` を呼び、`will-quit` の判定を `stopping` フラグに変更 |
| `meta_json` に `useBillboardMaterial`（Billboardの有無）と `dimensions`（バリエーション別の寸法）が入っていた | 両方を除外（自分でも同じ問題を見つけて修正済み） |

### 取り除いたスコープ外の追加

| 指摘 | 対応 |
|---|---|
| `AssetDetail.abs_dir`：APIが絶対パスを返していた。設計はExplorer連携を `rel_dir` + IPC と定め、メインプロセスが自分で絶対パスを解決する | 削除 |
| `AssetDetail.has_thumbnail`：設計にない項目。真偽値のためにBLOBを丸ごと読んでいた | 削除。サムネイルの有無は `<img>` の `onError` で判断する（グリッドと同じ `Thumbnail` に共通化） |
| クエリのトークンを全エンドポイントで受理。設計はサムネイルURLに限っている | `/thumbnails/{id}` だけに限定。他は401 |
| `search()` が `fingerprint` を返していた。設計では差分検知専用 | 一覧の列から削除 |
| CSPのメタタグ。設計に記述がなく、`script-src 'self'` と `connect-src` がReact RefreshのインラインスクリプトとHMRのWebSocketを止めるため `npm run dev` が動かない | 削除。`npm run dev` が動くことを確認 |

### 足したテスト

- 本番オリジン（`Origin: null`）のCORS preflight、他オリジンの拒否
- クエリのトークンが `/thumbnails` 以外で拒否されること
- `abs_dir` と `fingerprint` がAPIから出ないこと
- DBに持たないメタデータ（`points`、`splitSubmeshes`、`useBillboardMaterial`、`dimensions`、色空間、マップ種類）
- 同じアセットを別の絶対パスに置いてもフィンガープリントが一致すること
- `assetsData.json` と `atlas`/`brush`/`DHI` を読まないこと（読めない状態にして確認）
- 同期後にDownloadedを丸ごと消しても検索・一覧・詳細・カテゴリ・サムネイルが答えること
- 走行中の `POST /sync` が409を返すこと（モックなし）
- 同期中に `/assets` と `/categories` が答えること
- サムネイルの読み込み失敗でプレースホルダーに切り替わること（グリッドと詳細の両方）
- 詳細パネルが渡された `meta` のキー以外を描かないこと（空振りしていたテストを置き換え）

### 残した指摘と理由

- **`/assets` の `limit` / `offset`**：設計のAPI表にはないが、無ければ応答が無制限になる。APIの上限2000件で打ち切る。
- **メインプロセスの単一インスタンスロック、`setWindowOpenHandler`、`will-navigate` ガード、`sandbox: true`**：設計の役割分担には書かれていないが、2つ起動すると1つのSQLiteを2プロセスで書くことになり、残りは設計のセキュリティ節（`contextIsolation` 有効・Node.js統合無効）と同じ向き。
- **`userData` へのログファイル**：Downloaded配下ではなく、設計の「初回同期のログで確認する」に必要。
- **追加インデックス3件**：ER図は列の定義で、インデックスは含まない。列は追加していない。
- **`vitest` / `@testing-library` / `jsdom`**：テストを書くために必要。
- **メインプロセス（`index.ts`）のテストがない**：Electronのランタイムが必要なため単体テストにしていない。代わりに実際に `electron .` を起動して、Pythonの起動・`/health`・401・終了時の停止を確認した（上の「起動の確認」）。
- **`searchStr` との一致（設計の37/37）**：`assetsData.json` を使わない方針で、フィクスチャ3件に `searchStr` が無いため検証できない。語の含有を個別に確認している。

## 判断の記録

- リモートが空だったため、統合する履歴はなし。ローカルの `main` をそのまま push する。
- `is_billboard` は大文字小文字を区別しない。設計の表記は `Billboard` だが、実ファイルの
  表記揺れで解像度を誤表示する方が害が大きいため。
- `search_text` はフィールド名を語に含めない。`semanticTags` と `environment` は値だけを辿り、
  値が入れ子の辞書（`locations` など）のときはキーを中身として扱う。`assetCategories` は
  キーが中身なのでキーを辿る。語は小文字・重複なし・ソート済みで空白区切りにした。
- `meta_json` から `lodDistance`、`points`、`splitSubmeshes`、`useBillboardMaterial`、
  `dimensions` を落とした。設計が「ポリゴン数、色空間、バリエーション、マップ種類、
  LODはDBに持たない」「詳細パネルにはBillboardの有無とLODは表示しない」としているため。
  `dimensions` はバリエーション別の寸法。結果として3dplantの `meta_json` は空になる。
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
  ため、終了は `taskkill /T /F` でプロセスツリーごと止める。`stop()` は直の子の終了だけ
  でなく `taskkill` の完了も待つ。直の子が先に消えても、DBのファイルを握った孫が
  残っていることがあり、テストで実際に再現した。
- グリッドは一度に最大2000件（APIの上限）を取得する。設計にページングの指定がないため
  追加していない。これを超える件数のライブラリでは、件数表示は正しいが一覧は2000件まで。
- `/health` だけ認証なし。メインプロセスが接続を確かめる前にトークンを使えないため。
- トークンは `Authorization: Bearer` で受け取る。`/thumbnails/{id}` だけはクエリの
  `token` も受け取る（`<img>` はヘッダーを付けられないという設計の記述に合わせた）。
  比較は `secrets.compare_digest`。
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
- 解像度の規則外として記録するのは、Bridgeの補助フォルダ（`Thumbs/`、`previews/`）の
  外にあり、Billboardでなく解像度が読めず、拡張子が `.abc/.fbx/.json/.mtl/.obj/.ztl`
  でもなく、`_Preview.png` でもないファイルだけ。メッシュやプレビューは解像度を
  持たないのが普通なので、ログを埋めないようにした。
- `Thumbs/{1k,2k,4k}/` と `previews/` は解像度の集計に数えない。設計には書かれていない
  フォルダだが、実機で確認したところBridgeが画面用の縮小画像を置く場所で、実際に
  ダウンロードした解像度とは関係なかった。数えると4Kだけのアセットが1K/2K/4Kを持って
  いるように見える。除外の理由は設計がBillboardを除外するのと同じ（誤表示を防ぐ）。
  フィンガープリントには含めたままにした（フォルダ内の実ファイルではあるため）。
- SQLiteの接続はスレッドごとに持つ。1本を共有して書き込みだけロックする作りでは、
  読み出しと書き込みが重なった時点で `sqlite3.InterfaceError` になった（実機で発生）。
  WALは接続を分けて使う前提の仕組みなので、分けるのが設計の意図に沿う。
- カタログのファイル一覧のキーはタイプごとに異なる（surface=`maps`、3d=`components`+`meshes`、
  3dplant=`maps`+`billboards`+`models`）。この組で設計の449ファイルに一致することをテストで固定した。

## 未解決

なし。実装順1〜7はすべて完了し、実機のDownloadedでの初回同期も実行済み。

認証情報が必要な項目はなし。`origin` へのpushはすべて成功している。

### 残っている既知の制約

- グリッドは一度に最大2000件（APIの上限）まで。設計にページングの指定がないため追加して
  いない。実機は4件なので影響なし。
- 画面の見た目は、この環境からElectronのウィンドウのスクリーンショットを撮れないため
  目視では未確認。コンポーネントのテストと、アプリ起動時に `/thumbnails` が実際に
  呼ばれていたこと（最初の実行でこのエンドポイントのエラーが出たのが、グリッドが
  描画されてサムネイルを取りにいっていた証拠）で代替している。
