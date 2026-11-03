import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AssetGrid } from '../src/renderer/components/AssetGrid'
import { CategoryPanel } from '../src/renderer/components/CategoryPanel'
import { DetailPanel } from '../src/renderer/components/DetailPanel'
import type { AssetDetail, AssetListItem, CategoryItem } from '../src/shared/types'

afterEach(cleanup)

const thumbnailUrl = (id: string): string => `http://127.0.0.1:1/thumbnails/${id}?token=t`

function asset(overrides: Partial<AssetListItem> = {}): AssetListItem {
  return {
    id: 'wlrvaf3',
    name: 'Concrete Pavement',
    type: 'surface',
    rel_dir: 'surface/Concrete Pavement_wlrvaf3',
    average_color: '#112233',
    resolutions: ['2K', '4K'],
    ...overrides,
  }
}

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

describe('AssetGrid', () => {
  it('shows a card per asset with its type and resolutions', () => {
    render(
      <AssetGrid
        items={[asset()]}
        selectedId={null}
        thumbnailUrl={thumbnailUrl}
        onSelect={vi.fn()}
        onOpenFolder={vi.fn()}
      />,
    )

    expect(screen.getByText('Concrete Pavement')).toBeDefined()
    expect(screen.getByText('surface · 2K, 4K')).toBeDefined()
  })

  it('loads the thumbnail lazily from the api', () => {
    render(
      <AssetGrid
        items={[asset()]}
        selectedId={null}
        thumbnailUrl={thumbnailUrl}
        onSelect={vi.fn()}
        onOpenFolder={vi.fn()}
      />,
    )

    const image = document.querySelector('img')
    expect(image?.getAttribute('loading')).toBe('lazy')
    expect(image?.getAttribute('src')).toContain('/thumbnails/wlrvaf3?token=t')
  })

  it('says so when nothing matches', () => {
    render(
      <AssetGrid
        items={[]}
        selectedId={null}
        thumbnailUrl={thumbnailUrl}
        onSelect={vi.fn()}
        onOpenFolder={vi.fn()}
      />,
    )

    expect(screen.getByText('該当するアセットがありません。')).toBeDefined()
  })

  it('reports a click and a double click', () => {
    const onSelect = vi.fn()
    const onOpenFolder = vi.fn()
    render(
      <AssetGrid
        items={[asset()]}
        selectedId={null}
        thumbnailUrl={thumbnailUrl}
        onSelect={onSelect}
        onOpenFolder={onOpenFolder}
      />,
    )

    const card = screen.getByTitle('Concrete Pavement')
    card.click()
    card.dispatchEvent(new MouseEvent('dblclick', { bubbles: true }))

    expect(onSelect).toHaveBeenCalledWith('wlrvaf3')
    expect(onOpenFolder).toHaveBeenCalledWith('surface/Concrete Pavement_wlrvaf3')
  })
})

describe('CategoryPanel', () => {
  it('shows every level with its count', () => {
    render(
      <CategoryPanel
        items={[category('surface', 8), category('surface/concrete', 3)]}
        total={37}
        selected={null}
        onSelect={vi.fn()}
      />,
    )

    expect(screen.getByText('すべて')).toBeDefined()
    expect(screen.getByText('37')).toBeDefined()
    expect(screen.getByText('surface')).toBeDefined()
    expect(screen.getByText('concrete')).toBeDefined()
  })

  it('selects a category and clears it when clicked again', () => {
    const onSelect = vi.fn()
    render(
      <CategoryPanel
        items={[category('surface')]}
        total={1}
        selected={null}
        onSelect={onSelect}
      />,
    )
    screen.getByText('surface').click()
    expect(onSelect).toHaveBeenCalledWith('surface')

    cleanup()
    render(
      <CategoryPanel
        items={[category('surface')]}
        total={1}
        selected="surface"
        onSelect={onSelect}
      />,
    )
    screen.getByText('surface').click()
    expect(onSelect).toHaveBeenCalledWith(null)
  })
})

describe('DetailPanel', () => {
  const detail: AssetDetail = {
    ...asset(),
    abs_dir: 'D:/Megascans/Downloaded/surface/Concrete Pavement_wlrvaf3',
    categories: ['surface', 'surface/concrete'],
    meta: { scanArea: '2x2 m', tiling_directions: ['x', 'y'] },
    has_thumbnail: true,
  }

  it('shows the resolutions, the categories and the meta', () => {
    render(
      <DetailPanel
        asset={detail}
        thumbnailUrl={thumbnailUrl}
        onOpenFolder={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect(screen.getByText('2K, 4K')).toBeDefined()
    expect(screen.getByText('surface / surface/concrete')).toBeDefined()
    expect(screen.getByText('2x2 m')).toBeDefined()
    expect(screen.getByText('x, y')).toBeDefined()
  })

  it('does not show a billboard row or a lod row', () => {
    render(
      <DetailPanel
        asset={detail}
        thumbnailUrl={thumbnailUrl}
        onOpenFolder={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect(screen.queryByText(/Billboard/i)).toBeNull()
    expect(screen.queryByText(/lodDistance/i)).toBeNull()
  })

  it('opens the folder with the relative path', () => {
    const onOpenFolder = vi.fn()
    render(
      <DetailPanel
        asset={detail}
        thumbnailUrl={thumbnailUrl}
        onOpenFolder={onOpenFolder}
        onClose={vi.fn()}
      />,
    )

    screen.getByText('フォルダを開く').click()

    expect(onOpenFolder).toHaveBeenCalledWith('surface/Concrete Pavement_wlrvaf3')
  })

  it('leaves out the image when there is no thumbnail', () => {
    render(
      <DetailPanel
        asset={{ ...detail, has_thumbnail: false }}
        thumbnailUrl={thumbnailUrl}
        onOpenFolder={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect(document.querySelector('img')).toBeNull()
  })
})
