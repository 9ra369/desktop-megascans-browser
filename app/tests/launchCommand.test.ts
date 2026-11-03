import path from 'node:path'

import { describe, expect, it } from 'vitest'

import { launchCommand } from '../src/main/pythonServer'

const backendDir = path.resolve(__dirname, '..', '..', 'backend')

describe('launchCommand', () => {
  it('uses the given executable as is', () => {
    const { command, args } = launchCommand({
      userData: 'C:/userData',
      backendDir,
      executable: 'C:/bin/server.exe',
    })

    expect(command).toBe('C:/bin/server.exe')
    expect(args).toEqual(['--user-data', 'C:/userData'])
  })

  it('launches the venv python directly so python is not a grandchild', () => {
    const { command, args } = launchCommand({ userData: 'C:/userData', backendDir })

    expect(command).toContain('.venv')
    expect(command).not.toContain('uv')
    expect(args).toEqual([
      '-m',
      'megascans_browser.api.server',
      '--user-data',
      'C:/userData',
    ])
  })

  it('falls back to uv run when there is no venv', () => {
    const { command, args } = launchCommand({
      userData: 'C:/userData',
      backendDir: path.join(backendDir, 'no-such-dir'),
    })

    expect(command).toMatch(/^uv/)
    expect(args[0]).toBe('run')
    expect(args).toContain('megascans_browser.api.server')
  })
})
