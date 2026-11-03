import { describe, expect, it } from 'vitest'

import { ApiClient, toSearch } from '../src/renderer/api'
import { buildCategoryTree } from '../src/renderer/categoryTree'
import type { CategoryItem } from '../src/shared/types'

function category(path: string, count = 1): CategoryItem {
  const parent = path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : null
  return {
    path,
    name: path.slice(path.lastIndexOf('/') + 1),
    parent,
    depth: path.split('/').length - 1,
    count,
  }
}

describe('toSearch', () => {
  it('is empty without a query', () => {
    expect(toSearch({})).toBe('')
  })

  it('skips empty values', () => {
    expect(toSearch({ q: '', type: 'surface' })).toBe('?type=surface')
  })

  it('encodes the values', () => {
    expect(toSearch({ category: '3d/nature/rock' })).toBe('?category=3d%2Fnature%2Frock')
  })

  it('keeps a zero offset out but a positive one in', () => {
    expect(toSearch({ offset: 0 })).toBe('?offset=0')
    expect(toSearch({ limit: 50, offset: 50 })).toBe('?limit=50&offset=50')
  })
})

describe('buildCategoryTree', () => {
  it('nests the children under their parent', () => {
    const tree = buildCategoryTree([
      category('3d'),
      category('3d/nature'),
      category('3d/nature/rock'),
      category('surface'),
    ])

    expect(tree.map((node) => node.path)).toEqual(['3d', 'surface'])
    expect(tree[0]?.children.map((node) => node.path)).toEqual(['3d/nature'])
    expect(tree[0]?.children[0]?.children.map((node) => node.path)).toEqual(['3d/nature/rock'])
  })

  it('keeps the counts', () => {
    const tree = buildCategoryTree([category('3d', 18), category('3d/nature', 7)])

    expect(tree[0]?.count).toBe(18)
    expect(tree[0]?.children[0]?.count).toBe(7)
  })

  it('treats a node whose parent is missing as a root', () => {
    const tree = buildCategoryTree([category('3d/nature/rock')])

    expect(tree.map((node) => node.path)).toEqual(['3d/nature/rock'])
  })

  it('sorts the siblings by path', () => {
    const tree = buildCategoryTree([category('surface'), category('3dplant'), category('3d')])

    expect(tree.map((node) => node.path)).toEqual(['3d', '3dplant', 'surface'])
  })

  it('is empty for no items', () => {
    expect(buildCategoryTree([])).toEqual([])
  })
})

describe('ApiClient', () => {
  const client = new ApiClient({ port: 51234, token: 'a token' })

  it('puts the token in the thumbnail url', () => {
    expect(client.thumbnailUrl('wlrvaf3')).toBe(
      'http://127.0.0.1:51234/thumbnails/wlrvaf3?token=a%20token',
    )
  })

  it('escapes the asset id in the thumbnail url', () => {
    expect(client.thumbnailUrl('a/b')).toContain('/thumbnails/a%2Fb')
  })

  it('talks to loopback only', () => {
    expect(client.thumbnailUrl('x').startsWith('http://127.0.0.1:')).toBe(true)
  })
})
