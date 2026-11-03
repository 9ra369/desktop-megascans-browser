import type { Connection } from '../shared/types'

/** Pythonサーバーが標準出力の1行に付ける目印。backendの `server.py` と同じ。 */
export const READY_PREFIX = 'MEGASCANS_BROWSER_READY '

/** 起動の行からポートとトークンを取り出す。目印がなければ `null`。 */
export function parseReadyLine(line: string): Connection | null {
  const trimmed = line.trim()
  if (!trimmed.startsWith(READY_PREFIX)) {
    return null
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(trimmed.slice(READY_PREFIX.length))
  } catch {
    return null
  }
  if (typeof parsed !== 'object' || parsed === null) {
    return null
  }
  const { port, token } = parsed as Record<string, unknown>
  if (typeof port !== 'number' || !Number.isInteger(port) || port <= 0) {
    return null
  }
  if (typeof token !== 'string' || token.length === 0) {
    return null
  }
  return { port, token }
}
