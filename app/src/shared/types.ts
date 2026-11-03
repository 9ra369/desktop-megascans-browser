/** メインプロセス、preload、レンダラーで共有する型。 */

export type AssetType = '3d' | '3dplant' | 'surface'

export const ASSET_TYPES: readonly AssetType[] = ['3d', '3dplant', 'surface']

/** Pythonサーバーへの接続情報。起動ごとに変わる。 */
export interface Connection {
  port: number
  token: string
}

export interface AssetListItem {
  id: string
  name: string
  type: string
  rel_dir: string
  average_color: string
  resolutions: string[]
}

export interface AssetListResponse {
  items: AssetListItem[]
  total: number
  limit: number
  offset: number
}

export interface AssetDetail extends AssetListItem {
  categories: string[]
  meta: Record<string, unknown>
}

export interface CategoryItem {
  path: string
  name: string
  parent: string | null
  depth: number
  count: number
}

export interface CategoryListResponse {
  items: CategoryItem[]
}

export interface AppSettings {
  downloaded_path: string | null
  configured: boolean
}

export type SyncState = 'idle' | 'running' | 'done' | 'error'

export interface SyncStatus {
  state: SyncState
  running: boolean
  done: number
  total: number
  error: string | null
  added: number
  updated: number
  removed: number
  unchanged: number
  failed: number
  log: string[]
}

/** preloadが画面へ公開する操作。 */
export interface DesktopApi {
  /** Pythonサーバーの接続情報を返す。 */
  getConnection(): Promise<Connection>
  /** Downloadedを選ぶダイアログを出す。取り消したら `null`。 */
  chooseDownloadedFolder(): Promise<string | null>
  /** Downloaded配下のフォルダをFile Explorerで開く。 */
  openAssetFolder(relDir: string): Promise<boolean>
}
