import type { CategoryItem } from '../shared/types'

export interface CategoryNode extends CategoryItem {
  children: CategoryNode[]
}

/**
 * 平坦なカテゴリの一覧を木にする。
 *
 * APIは親階層も行として返すので、`parent` をたどるだけで組める。
 */
export function buildCategoryTree(items: readonly CategoryItem[]): CategoryNode[] {
  const nodes = new Map<string, CategoryNode>()
  for (const item of items) {
    nodes.set(item.path, { ...item, children: [] })
  }

  const roots: CategoryNode[] = []
  for (const node of nodes.values()) {
    const parent = node.parent === null ? undefined : nodes.get(node.parent)
    if (parent === undefined) {
      roots.push(node)
    } else {
      parent.children.push(node)
    }
  }

  const sort = (list: CategoryNode[]): void => {
    list.sort((a, b) => a.path.localeCompare(b.path))
    for (const node of list) {
      sort(node.children)
    }
  }
  sort(roots)
  return roots
}
