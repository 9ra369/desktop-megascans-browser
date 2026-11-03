import type {
  AppSettings,
  AssetDetail,
  AssetListResponse,
  CategoryListResponse,
  Connection,
  SyncStatus,
} from '../shared/types'

export interface AssetQuery {
  q?: string
  type?: string
  category?: string
  limit?: number
  offset?: number
}

/** Pythonサーバーを呼ぶ薄い層。トークンはここだけで扱う。 */
export class ApiClient {
  private readonly base: string

  constructor(private readonly connection: Connection) {
    this.base = `http://127.0.0.1:${String(connection.port)}`
  }

  private async request<T>(pathname: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.base}${pathname}`, {
      ...init,
      headers: {
        ...init?.headers,
        Authorization: `Bearer ${this.connection.token}`,
      },
    })
    if (!response.ok) {
      throw new Error(await errorMessage(response))
    }
    return (await response.json()) as T
  }

  getSettings(): Promise<AppSettings> {
    return this.request<AppSettings>('/settings')
  }

  setDownloadedPath(downloadedPath: string): Promise<AppSettings> {
    return this.request<AppSettings>('/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ downloaded_path: downloadedPath }),
    })
  }

  listAssets(query: AssetQuery = {}): Promise<AssetListResponse> {
    return this.request<AssetListResponse>(`/assets${toSearch(query)}`)
  }

  getAsset(id: string): Promise<AssetDetail> {
    return this.request<AssetDetail>(`/assets/${encodeURIComponent(id)}`)
  }

  listCategories(): Promise<CategoryListResponse> {
    return this.request<CategoryListResponse>('/categories')
  }

  startSync(): Promise<{ started: boolean }> {
    return this.request<{ started: boolean }>('/sync', { method: 'POST' })
  }

  getSyncStatus(): Promise<SyncStatus> {
    return this.request<SyncStatus>('/sync/status')
  }

  /** `<img>` から読む用のURL。ヘッダーを付けられないのでトークンをクエリに付ける。 */
  thumbnailUrl(id: string): string {
    return `${this.base}/thumbnails/${encodeURIComponent(id)}?token=${encodeURIComponent(this.connection.token)}`
  }
}

export function toSearch(query: AssetQuery): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== '' && value !== null) {
      params.set(key, String(value))
    }
  }
  const search = params.toString()
  return search === '' ? '' : `?${search}`
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') {
      return body.detail
    }
  } catch {
    // JSONでなければステータスだけを返す。
  }
  return `${String(response.status)} ${response.statusText}`
}
