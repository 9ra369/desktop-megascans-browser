import type { SyncStatus } from '../shared/types'

function assetCount(total: number): string {
  return `${String(total)} ${total === 1 ? 'asset' : 'assets'}`
}

/** 上の帯に出す同期の状態。 */
export function syncLabel(status: SyncStatus | null, total: number): string {
  if (status === null) {
    return assetCount(total)
  }
  if (status.running) {
    return status.total > 0
      ? `Syncing ${String(status.done)} / ${String(status.total)}`
      : 'Syncing…'
  }
  if (status.state === 'error') {
    return 'Sync failed'
  }
  if (status.state === 'done') {
    const changes = [
      status.added > 0 ? `+${String(status.added)}` : null,
      status.updated > 0 ? `${String(status.updated)} updated` : null,
      status.removed > 0 ? `${String(status.removed)} removed` : null,
      status.failed > 0 ? `${String(status.failed)} failed` : null,
    ].filter((part): part is string => part !== null)
    return changes.length === 0
      ? `${assetCount(total)} · no changes`
      : `${assetCount(total)} · ${changes.join(' / ')}`
  }
  return assetCount(total)
}
