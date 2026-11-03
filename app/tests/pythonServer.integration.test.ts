import { existsSync, mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'

import { afterEach, describe, expect, it } from 'vitest'

import { PythonServer, baseUrl } from '../src/main/pythonServer'

const backendDir = path.resolve(__dirname, '..', '..', 'backend')

describe('PythonServer', () => {
  let server: PythonServer | null = null
  let userData: string | null = null

  /** 使い捨ての `userData` を作り、後片付けの対象にする。 */
  function makeUserData(): string {
    userData = mkdtempSync(path.join(tmpdir(), 'megascans-browser-'))
    return userData
  }

  afterEach(async () => {
    await server?.stop()
    server = null
    if (userData !== null) {
      // Windowsはプロセス終了直後もDBのハンドルを握っていることがあるので少し待つ。
      rmSync(userData, { recursive: true, force: true, maxRetries: 20, retryDelay: 100 })
      userData = null
    }
  })

  it('starts the backend, confirms health and stops it', async () => {
    server = new PythonServer({ userData: makeUserData(), backendDir })

    const connection = await server.start()

    expect(connection.port).toBeGreaterThan(0)
    expect(connection.token.length).toBeGreaterThan(16)

    const health = await fetch(`${baseUrl(connection)}/health`)
    expect(health.ok).toBe(true)
    expect(((await health.json()) as { status: string }).status).toBe('ok')

    const unauthorized = await fetch(`${baseUrl(connection)}/assets`)
    expect(unauthorized.status).toBe(401)

    const assets = await fetch(`${baseUrl(connection)}/assets`, {
      headers: { Authorization: `Bearer ${connection.token}` },
    })
    expect(assets.ok).toBe(true)
    expect(((await assets.json()) as { total: number }).total).toBe(0)

    await server.stop()
    await expect(fetch(`${baseUrl(connection)}/health`)).rejects.toThrow()
  }, 120_000)

  it('returns the same connection when started twice', async () => {
    server = new PythonServer({ userData: makeUserData(), backendDir })

    const first = await server.start()
    const second = await server.start()

    expect(second).toEqual(first)
  }, 120_000)

  it('fails when the backend cannot be launched', async () => {
    server = new PythonServer({
      userData: makeUserData(),
      backendDir,
      executable: path.join(backendDir, 'no-such-server.exe'),
    })

    await expect(server.start()).rejects.toThrow()
  }, 120_000)

  it('holds no file handle once it has stopped', async () => {
    // stop() から戻った時点で孫プロセスまで終わっていないと、DBのファイルを
    // 握ったままになり、Windowsではフォルダを消せない。
    const dir = makeUserData()
    server = new PythonServer({ userData: dir, backendDir })
    await server.start()

    await server.stop()
    rmSync(dir, { recursive: true, force: true })

    expect(existsSync(dir)).toBe(false)
    userData = null
  }, 120_000)

  it('stopping a server that never started is harmless', async () => {
    server = new PythonServer({ userData: makeUserData(), backendDir })

    await expect(server.stop()).resolves.toBeUndefined()
  })
})
