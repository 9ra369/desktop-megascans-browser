import { useState } from 'react'

interface Props {
  assetId: string
  /** プレースホルダーの地色に使う平均色。 */
  averageColor: string
  thumbnailUrl: (id: string) => string
  className?: string
}

/**
 * サムネイル。無ければプレースホルダーを出す。
 *
 * サムネイルの有無はAPIに問い合わせず、`<img>` の読み込み失敗で判断する。
 */
export function Thumbnail({
  assetId,
  averageColor,
  thumbnailUrl,
  className = 'card__image',
}: Props): React.JSX.Element {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <div
        className="card__placeholder"
        style={{ background: averageColor || 'var(--panel-2)' }}
        aria-hidden="true"
      >
        no preview
      </div>
    )
  }
  return (
    <img
      className={className}
      src={thumbnailUrl(assetId)}
      alt=""
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  )
}
