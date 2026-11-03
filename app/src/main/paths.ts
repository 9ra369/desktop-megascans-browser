import path from 'node:path'

export interface AppPaths {
  /** `app/` フォルダ。 */
  appDir: string
  /** リポジトリのルート。`backend/` の親。 */
  projectRoot: string
  /** backendのフォルダ。 */
  backendDir: string
  /** ビルド済みレンダラーのHTML。 */
  rendererEntry: string
  /** preloadのスクリプト。 */
  preloadScript: string
}

/**
 * メインプロセスの `__dirname` から、必要なパスをまとめて出す。
 *
 * `tsconfig.main.json` の `rootDir` が `src` なので、`src/main/index.ts` は
 * `app/dist/main/main/index.js` に出る。
 */
export function resolveAppPaths(dirname: string): AppPaths {
  const appDir = path.resolve(dirname, '..', '..', '..')
  const projectRoot = path.resolve(appDir, '..')
  return {
    appDir,
    projectRoot,
    backendDir: path.join(projectRoot, 'backend'),
    rendererEntry: path.join(appDir, 'dist', 'renderer', 'index.html'),
    preloadScript: path.join(dirname, '..', 'preload', 'index.js'),
  }
}
