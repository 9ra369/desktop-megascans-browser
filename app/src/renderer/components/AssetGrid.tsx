import { useState } from 'react'

import type { AssetListItem } from '../../shared/types'

interface Props {
  items: readonly AssetListItem[]
  selectedId: string | null
  thumbnailUrl: (id: string) => string
  onSelect: (id: string) => void
  onOpenFolder: (relDir: string) => void
}

function Thumbnail({
  asset,
  thumbnailUrl,
}: {
  asset: AssetListItem
  thumbnailUrl: (id: string) => string
}): React.JSX.Element {
  const [failed, setFailed] = useState(false)

  if (failed) {
    // サムネイルがなければプレースホルダー。平均色を敷いて見分けやすくする。
    return (
      <div
        className="card__placeholder"
        style={{ background: asset.average_color || 'var(--panel-2)' }}
        aria-hidden="true"
      >
        no preview
      </div>
    )
  }
  return (
    <img
      className="card__image"
      src={thumbnailUrl(asset.id)}
      alt=""
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  )
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
          <Thumbnail asset={asset} thumbnailUrl={thumbnailUrl} />
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
