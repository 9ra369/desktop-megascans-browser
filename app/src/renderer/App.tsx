import { useCallback, useEffect, useRef, useState } from 'react'

import { ASSET_TYPES, type AssetDetail, type AssetListItem, type CategoryItem, type SyncStatus } from '../shared/types'
import { ApiClient } from './api'
import { AssetGrid } from './components/AssetGrid'
import { CategoryPanel } from './components/CategoryPanel'
import { DetailPanel } from './components/DetailPanel'
import { SetupScreen } from './components/SetupScreen'
import { syncLabel } from './syncLabel'

/** 検索の打鍵をまとめる待ち時間。 */
const SEARCH_DEBOUNCE_MS = 200
/** `/sync/status` を見にいく間隔。 */
const SYNC_POLL_MS = 700
/** 一覧の取得件数。 */
const PAGE_SIZE = 500

type Phase = 'connecting' | 'setup' | 'ready' | 'failed'

export function App(): React.JSX.Element {
  const [client, setClient] = useState<ApiClient | null>(null)
  const [phase, setPhase] = useState<Phase>('connecting')
  const [fatal, setFatal] = useState<string | null>(null)

  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  const [assetType, setAssetType] = useState('')
  const [category, setCategory] = useState<string | null>(null)

  const [assets, setAssets] = useState<readonly AssetListItem[]>([])
  const [total, setTotal] = useState(0)
  const [categories, setCategories] = useState<readonly CategoryItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<AssetDetail | null>(null)
  const [sync, setSync] = useState<SyncStatus | null>(null)
  const [listError, setListError] = useState<string | null>(null)

  const syncedOnce = useRef(false)

  // 起動：接続情報を受け取り、Downloadedの場所が未設定なら初回設定を出す。
  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const connection = await window.desktop.getConnection()
        const api = new ApiClient(connection)
        const settings = await api.getSettings()
        if (cancelled) {
          return
        }
        setClient(api)
        setPhase(settings.configured ? 'ready' : 'setup')
      } catch (error) {
        if (!cancelled) {
          setFatal(error instanceof Error ? error.message : String(error))
          setPhase('failed')
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [query])

  const reload = useCallback(async (): Promise<void> => {
    if (client === null) {
      return
    }
    try {
      const [list, tree] = await Promise.all([
        client.listAssets({
          q: debounced,
          type: assetType,
          category: category ?? '',
          limit: PAGE_SIZE,
        }),
        client.listCategories(),
      ])
      setAssets(list.items)
      setTotal(list.total)
      setCategories(tree.items)
      setListError(null)
    } catch (error) {
      setListError(error instanceof Error ? error.message : String(error))
    }
  }, [client, debounced, assetType, category])

  // DBの一覧を先に表示する。
  useEffect(() => {
    if (phase === 'ready') {
      void reload()
    }
  }, [phase, reload])

  const startSync = useCallback(async (): Promise<void> => {
    if (client === null) {
      return
    }
    try {
      await client.startSync()
      setSync(await client.getSyncStatus())
    } catch (error) {
      setListError(error instanceof Error ? error.message : String(error))
    }
  }, [client])

  // 表示したあとに裏で同期を始める。
  useEffect(() => {
    if (phase === 'ready' && client !== null && !syncedOnce.current) {
      syncedOnce.current = true
      void startSync()
    }
  }, [phase, client, startSync])

  // 同期中は状態をポーリングし、終わったら一覧を取り直す。
  useEffect(() => {
    if (client === null || sync === null || !sync.running) {
      return
    }
    const timer = setInterval(() => {
      void (async () => {
        const next = await client.getSyncStatus()
        setSync(next)
        if (!next.running) {
          await reload()
        }
      })()
    }, SYNC_POLL_MS)
    return () => clearInterval(timer)
  }, [client, sync, reload])

  // 選んだアセットの詳細を取る。
  useEffect(() => {
    if (client === null || selectedId === null) {
      setDetail(null)
      return
    }
    let cancelled = false
    void client
      .getAsset(selectedId)
      .then((asset) => {
        if (!cancelled) {
          setDetail(asset)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDetail(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [client, selectedId])

  const openFolder = useCallback((relDir: string): void => {
    void window.desktop.openAssetFolder(relDir)
  }, [])

  if (phase === 'connecting') {
    return (
      <div className="center">
        <p className="muted">Pythonサーバーに接続中…</p>
      </div>
    )
  }

  if (phase === 'failed') {
    return (
      <div className="center">
        <div className="setup">
          <h1>起動できませんでした</h1>
          <p className="error">{fatal}</p>
        </div>
      </div>
    )
  }

  if (phase === 'setup' || client === null) {
    return (
      <SetupScreen
        initialPath={null}
        onSave={async (downloadedPath) => {
          if (client === null) {
            return
          }
          await client.setDownloadedPath(downloadedPath)
          setPhase('ready')
        }}
      />
    )
  }

  return (
    <div className="app">
      <header className="toolbar">
        <h1 className="toolbar__title">Megascans Browser</h1>
        <input
          className="toolbar__search"
          type="search"
          placeholder="名前、タグ、カテゴリで検索"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label="検索"
        />
        <select
          value={assetType}
          onChange={(event) => setAssetType(event.target.value)}
          aria-label="タイプ"
        >
          <option value="">すべてのタイプ</option>
          {ASSET_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
        <button type="button" onClick={() => void startSync()} disabled={sync?.running === true}>
          再スキャン
        </button>
        <span className="toolbar__status">{syncLabel(sync, total)}</span>
      </header>

      <div className={`app__body${detail === null ? '' : ' app__body--with-detail'}`}>
        <CategoryPanel
          items={categories}
          total={total}
          selected={category}
          onSelect={setCategory}
        />
        <main style={{ minHeight: 0, display: 'grid', gridTemplateRows: 'auto 1fr' }}>
          {listError === null ? null : <p className="error" style={{ margin: '8px 14px' }}>{listError}</p>}
          {sync?.state === 'error' && sync.error !== null ? (
            <p className="error" style={{ margin: '8px 14px' }}>
              同期に失敗しました: {sync.error}
            </p>
          ) : null}
          <AssetGrid
            items={assets}
            selectedId={selectedId}
            thumbnailUrl={(id) => client.thumbnailUrl(id)}
            onSelect={setSelectedId}
            onOpenFolder={openFolder}
          />
        </main>
        {detail === null ? null : (
          <DetailPanel
            asset={detail}
            thumbnailUrl={(id) => client.thumbnailUrl(id)}
            onOpenFolder={openFolder}
            onClose={() => setSelectedId(null)}
          />
        )}
      </div>
    </div>
  )
}
