import path from 'node:path'

/**
 * Downloadedからの相対パスを絶対パスにする。Downloaded配下でなければ `null`。
 *
 * Explorerを開くのはメインプロセスなので、画面から渡された文字列はここで必ず
 * 確認する。Downloaded自身は開く対象にしない。
 */
export function resolveInsideDownloaded(
  downloaded: string | null | undefined,
  relDir: string,
): string | null {
  if (!downloaded) {
    return null
  }
  if (relDir.includes('\u0000') || downloaded.includes('\u0000')) {
    return null
  }
  if (path.isAbsolute(relDir) || /^[a-zA-Z]:/.test(relDir)) {
    return null
  }

  const root = path.resolve(downloaded)
  const target = path.resolve(root, relDir)
  const relative = path.relative(root, target)
  if (relative === '' || relative.startsWith('..') || path.isAbsolute(relative)) {
    return null
  }
  return target
}
