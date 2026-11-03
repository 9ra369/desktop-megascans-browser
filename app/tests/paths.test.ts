import { existsSync } from 'node:fs'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

import { resolveAppPaths } from '../src/main/paths'

/** ビルド後のメインプロセスが置かれる場所。 */
const builtMainDir = path.resolve(__dirname, '..', 'dist', 'main', 'main')

describe('resolveAppPaths', () => {
  const paths = resolveAppPaths(builtMainDir)

  it('finds the app folder', () => {
    expect(paths.appDir).toBe(path.resolve(__dirname, '..'))
  })

  it('finds the project root', () => {
    expect(paths.projectRoot).toBe(path.resolve(__dirname, '..', '..'))
  })

  it('points at the real backend folder', () => {
    expect(paths.backendDir).toBe(path.resolve(__dirname, '..', '..', 'backend'))
    expect(existsSync(path.join(paths.backendDir, 'pyproject.toml'))).toBe(true)
  })

  it('points at the built renderer entry', () => {
    expect(paths.rendererEntry).toBe(
      path.resolve(__dirname, '..', 'dist', 'renderer', 'index.html'),
    )
  })

  it('points at the built preload script', () => {
    expect(paths.preloadScript).toBe(
      path.resolve(__dirname, '..', 'dist', 'main', 'preload', 'index.js'),
    )
  })
})
