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
    <aside className="detail" aria-label="Details">
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
        <dt>Resolutions</dt>
        <dd>{asset.resolutions.length > 0 ? asset.resolutions.join(', ') : '—'}</dd>
        <dt>Categories</dt>
        <dd>{asset.categories.join(' / ') || '—'}</dd>
        <dt>Folder</dt>
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
          Open folder
        </button>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </div>
    </aside>
  )
}
