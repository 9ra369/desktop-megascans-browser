import type { AssetListItem } from '../../shared/types'
import { Thumbnail } from './Thumbnail'

interface Props {
  items: readonly AssetListItem[]
  selectedId: string | null
  thumbnailUrl: (id: string) => string
  onSelect: (id: string) => void
  onOpenFolder: (relDir: string) => void
}

export function AssetGrid({
  items,
  selectedId,
  thumbnailUrl,
  onSelect,
  onOpenFolder,
}: Props): React.JSX.Element {
  if (items.length === 0) {
    return (
      <div className="grid">
        <p className="muted">該当するアセットがありません。</p>
      </div>
    )
  }

  return (
    <div className="grid">
      {items.map((asset) => (
        <button
          key={asset.id}
          type="button"
          className={`card${asset.id === selectedId ? ' card--active' : ''}`}
          onClick={() => onSelect(asset.id)}
          onDoubleClick={() => onOpenFolder(asset.rel_dir)}
          title={asset.name}
        >
          <Thumbnail
            assetId={asset.id}
            averageColor={asset.average_color}
            thumbnailUrl={thumbnailUrl}
          />
          <span className="card__body">
            <span className="card__name">{asset.name}</span>
            <br />
            <span className="card__meta">
              {asset.type}
              {asset.resolutions.length > 0 ? ` · ${asset.resolutions.join(', ')}` : ''}
            </span>
          </span>
        </button>
      ))}
    </div>
  )
}
