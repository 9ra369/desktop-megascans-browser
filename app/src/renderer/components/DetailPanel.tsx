import type { AssetDetail } from '../../shared/types'
import { Thumbnail } from './Thumbnail'

interface Props {
  asset: AssetDetail
  thumbnailUrl: (id: string) => string
  onOpenFolder: (relDir: string) => void
  onClose: () => void
}

function metaText(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(metaText).join(', ')
  }
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value)
  }
  return String(value)
}

export function DetailPanel({
  asset,
  thumbnailUrl,
  onOpenFolder,
  onClose,
}: Props): React.JSX.Element {
  return (
    <aside className="detail" aria-label="詳細">
      <h2 className="detail__name">{asset.name}</h2>
      <p className="muted">
        {asset.type} · {asset.id}
      </p>
      <Thumbnail
        assetId={asset.id}
        averageColor={asset.average_color}
        thumbnailUrl={thumbnailUrl}
        className="detail__image"
      />

      <dl>
        <dt>解像度</dt>
        <dd>{asset.resolutions.length > 0 ? asset.resolutions.join(', ') : '—'}</dd>
        <dt>カテゴリ</dt>
        <dd>{asset.categories.join(' / ') || '—'}</dd>
        <dt>フォルダ</dt>
        <dd>{asset.rel_dir}</dd>
        {Object.entries(asset.meta).map(([key, value]) => (
          <div key={key} style={{ display: 'contents' }}>
            <dt>{key}</dt>
            <dd>{metaText(value)}</dd>
          </div>
        ))}
      </dl>

      <div style={{ display: 'flex', gap: 8 }}>
        <button type="button" onClick={() => onOpenFolder(asset.rel_dir)}>
          フォルダを開く
        </button>
        <button type="button" onClick={onClose}>
          閉じる
        </button>
      </div>
    </aside>
  )
}
