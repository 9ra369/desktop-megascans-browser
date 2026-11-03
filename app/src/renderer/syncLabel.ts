import type { SyncStatus } from '../shared/types'

/** 上の帯に出す同期の状態。 */
export function syncLabel(status: SyncStatus | null, total: number): string {
  if (status === null) {
    return `${String(total)} 件`
  }
  if (status.running) {
    return status.total > 0
      ? `同期中 ${String(status.done)} / ${String(status.total)}`
      : '同期中…'
  }
  if (status.state === 'error') {
    return '同期に失敗'
  }
  if (status.state === 'done') {
    const changes = [
      status.added > 0 ? `+${String(status.added)}` : null,
      status.updated > 0 ? `更新 ${String(status.updated)}` : null,
      status.removed > 0 ? `削除 ${String(status.removed)}` : null,
      status.failed > 0 ? `失敗 ${String(status.failed)}` : null,
    ].filter((part): part is string => part !== null)
    return changes.length === 0
      ? `${String(total)} 件 · 変更なし`
      : `${String(total)} 件 · ${changes.join(' / ')}`
  }
  return `${String(total)} 件`
}
