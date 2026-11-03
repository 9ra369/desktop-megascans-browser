import type { CategoryItem } from '../../shared/types'
import { type CategoryNode, buildCategoryTree } from '../categoryTree'

interface Props {
  items: readonly CategoryItem[]
  total: number
  selected: string | null
  onSelect: (path: string | null) => void
}

function Row({
  node,
  selected,
  onSelect,
}: {
  node: CategoryNode
  selected: string | null
  onSelect: (path: string | null) => void
}): React.JSX.Element {
  const active = selected === node.path
  return (
    <>
      <button
        type="button"
        className={`categories__item${active ? ' categories__item--active' : ''}`}
        style={{ paddingLeft: `${String(8 + node.depth * 14)}px` }}
        onClick={() => onSelect(active ? null : node.path)}
        aria-pressed={active}
      >
        <span className="categories__name">{node.name}</span>
        <span className="categories__count">{node.count}</span>
      </button>
      {node.children.map((child) => (
        <Row key={child.path} node={child} selected={selected} onSelect={onSelect} />
      ))}
    </>
  )
}

export function CategoryPanel({ items, total, selected, onSelect }: Props): React.JSX.Element {
  const tree = buildCategoryTree(items)
  return (
    <nav className="categories" aria-label="カテゴリ">
      <button
        type="button"
        className={`categories__item${selected === null ? ' categories__item--active' : ''}`}
        onClick={() => onSelect(null)}
        aria-pressed={selected === null}
      >
        <span className="categories__name">すべて</span>
        <span className="categories__count">{total}</span>
      </button>
      {tree.map((node) => (
        <Row key={node.path} node={node} selected={selected} onSelect={onSelect} />
      ))}
    </nav>
  )
}
