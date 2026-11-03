import { describe, expect, it } from 'vitest'

import { syncLabel } from '../src/renderer/syncLabel'
import type { SyncStatus } from '../src/shared/types'

function status(overrides: Partial<SyncStatus> = {}): SyncStatus {
  return {
    state: 'idle',
    running: false,
    done: 0,
    total: 0,
    error: null,
    added: 0,
    updated: 0,
    removed: 0,
    unchanged: 0,
    failed: 0,
    log: [],
    ...overrides,
  }
}

describe('syncLabel', () => {
  it('shows the count before the first sync', () => {
    expect(syncLabel(null, 37)).toBe('37 assets')
    expect(syncLabel(status(), 37)).toBe('37 assets')
  })

  it('uses the singular for one asset', () => {
    expect(syncLabel(null, 1)).toBe('1 asset')
    expect(syncLabel(null, 0)).toBe('0 assets')
  })

  it('shows the progress while syncing', () => {
    expect(syncLabel(status({ state: 'running', running: true, done: 4, total: 9 }), 0)).toBe(
      'Syncing 4 / 9',
    )
  })

  it('shows a plain message when the total is not known yet', () => {
    expect(syncLabel(status({ state: 'running', running: true }), 0)).toBe('Syncing…')
  })

  it('reports no change when nothing moved', () => {
    expect(syncLabel(status({ state: 'done', unchanged: 37 }), 37)).toBe('37 assets · no changes')
  })

  it('reports what changed', () => {
    const label = syncLabel(
      status({ state: 'done', added: 2, updated: 1, removed: 3, failed: 1 }),
      37,
    )

    expect(label).toBe('37 assets · +2 / 1 updated / 3 removed / 1 failed')
  })

  it('reports a failure', () => {
    expect(syncLabel(status({ state: 'error', error: 'boom' }), 0)).toBe('Sync failed')
  })
})
