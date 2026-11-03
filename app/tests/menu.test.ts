import type { MenuItemConstructorOptions } from 'electron'
import { describe, expect, it } from 'vitest'

import { buildMenuTemplate } from '../src/main/menu'

const template = buildMenuTemplate()

function submenuOf(label: string): MenuItemConstructorOptions[] {
  const entry = template.find((item) => item.label === label)
  expect(entry, `${label} メニューがない`).toBeDefined()
  return (entry?.submenu ?? []) as MenuItemConstructorOptions[]
}

function rolesOf(label: string): (string | undefined)[] {
  return submenuOf(label)
    .filter((item) => item.type !== 'separator')
    .map((item) => item.role)
}

describe('buildMenuTemplate', () => {
  it('has Edit with Undo and Redo only', () => {
    expect(rolesOf('Edit')).toEqual(['undo', 'redo'])
  })

  it('leaves cut, copy, paste and select all out of Edit', () => {
    const roles = rolesOf('Edit')

    for (const role of ['cut', 'copy', 'paste', 'pasteAndMatchStyle', 'delete', 'selectAll']) {
      expect(roles).not.toContain(role)
    }
  })

  it('labels every item in English', () => {
    const labels = template.flatMap((item) => [
      item.label,
      ...((item.submenu ?? []) as MenuItemConstructorOptions[]).map((child) => child.label),
    ])

    for (const label of labels) {
      if (label !== undefined) {
        // 日本語（ひらがな・カタカナ・漢字）を含まないこと。
        expect(label).not.toMatch(/[぀-ヿ一-龯]/)
      }
    }
  })

  it('gives every non-separator item a role and a label', () => {
    for (const menu of template) {
      for (const item of (menu.submenu ?? []) as MenuItemConstructorOptions[]) {
        if (item.type === 'separator') {
          continue
        }
        expect(item.role).toBeDefined()
        expect(item.label).toBeDefined()
      }
    }
  })

  it('has the expected top level menus', () => {
    expect(template.map((item) => item.label)).toEqual(['File', 'Edit', 'View', 'Window'])
  })
})
