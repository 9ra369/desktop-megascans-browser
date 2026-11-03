import { type ChildProcess, execFile, spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import readline from 'node:readline'

import type { Connection } from '../shared/types'
import { parseReadyLine } from './readyLine'

/** 起動の行を待つ上限。 */
const READY_TIMEOUT_MS = 60_000
/** `/health` を確かめる上限。 */
const HEALTH_TIMEOUT_MS = 15_000
/** 終了を待ってから強制終了するまで。 */
const STOP_TIMEOUT_MS = 5_000

export interface PythonServerOptions {
  /** `userData` のパス。DBとログをこの下に置く。 */
  userData: string
  /** backendのフォルダ。開発時は `uv run` をここで実行する。 */
  backendDir: string
  /** 本番で使う単体の実行ファイル。なければ `uv run` を使う。 */
  executable?: string | undefined
}

const SERVER_MODULE = 'megascans_browser.api.server'

/** `uv sync` が作る仮想環境のPython。 */
function venvPython(backendDir: string): string {
  return process.platform === 'win32'
    ? path.join(backendDir, '.venv', 'Scripts', 'python.exe')
    : path.join(backendDir, '.venv', 'bin', 'python')
}

/**
 * 起動するコマンドを決める。
 *
 * 仮想環境のPythonを直に起動する。`uv run` を挟むとPythonが孫プロセスになり、
 * Electronの終了時に取り残されるため。
 */
export function launchCommand(options: PythonServerOptions): {
  command: string
  args: string[]
} {
  const args = ['--user-data', options.userData]
  if (options.executable) {
    return { command: options.executable, args }
  }
  const python = venvPython(options.backendDir)
  if (existsSync(python)) {
    return { command: python, args: ['-m', SERVER_MODULE, ...args] }
  }
  return {
    command: process.platform === 'win32' ? 'uv.exe' : 'uv',
    args: ['run', '--project', options.backendDir, 'python', '-m', SERVER_MODULE, ...args],
  }
}

/**
 * 子プロセスとその子孫をまとめて止める。
 *
 * Windowsでは `.venv/Scripts/python.exe` が本体のインタプリタを子として起動する
 * ため、直の子だけを止めるとサーバーが残る。
 */
function killTree(child: ChildProcess): Promise<void> {
  if (process.platform === 'win32' && child.pid !== undefined) {
    return new Promise((resolve) => {
      // taskkill はツリーを止めてから返るので、これを待てば孫も終わっている。
      // すでに終了していればエラーになるので、結果は見ない。
      execFile('taskkill', ['/pid', String(child.pid), '/T', '/F'], () => resolve())
    })
  }
  child.kill()
  return Promise.resolve()
}

/**
 * Pythonサーバーの起動と終了を受け持つ。
 *
 * ポートとトークンは標準出力の1行から受け取り、`/health` で起動を確認する。
 */
export class PythonServer {
  private child: ChildProcess | null = null
  private connection: Connection | null = null

  constructor(private readonly options: PythonServerOptions) {}

  /** 起動して接続情報を返す。すでに起動していればそれを返す。 */
  async start(): Promise<Connection> {
    if (this.connection !== null) {
      return this.connection
    }
    const { command, args } = launchCommand(this.options)
    const child = spawn(command, args, {
      cwd: path.resolve(this.options.backendDir),
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    })
    this.child = child

    child.stderr?.setEncoding('utf-8')
    child.stderr?.on('data', (chunk: string) => {
      process.stderr.write(`[python] ${chunk}`)
    })

    const connection = await this.waitForReady(child)
    await this.waitForHealth(connection)
    this.connection = connection
    return connection
  }

  private waitForReady(child: ChildProcess): Promise<Connection> {
    return new Promise((resolve, reject) => {
      if (child.stdout === null) {
        reject(new Error('Pythonの標準出力を読めない'))
        return
      }
      const lines = readline.createInterface({ input: child.stdout })
      const timer = setTimeout(() => {
        finish(new Error('Pythonサーバーの起動が時間内に終わらなかった'))
      }, READY_TIMEOUT_MS)

      const finish = (error: Error | null, connection?: Connection): void => {
        clearTimeout(timer)
        lines.removeAllListeners()
        child.removeListener('exit', onExit)
        child.removeListener('error', onError)
        if (error !== null) {
          reject(error)
        } else if (connection !== undefined) {
          resolve(connection)
        }
      }
      const onExit = (code: number | null): void => {
        finish(new Error(`Pythonサーバーが起動前に終了した (code ${String(code)})`))
      }
      const onError = (error: Error): void => {
        finish(new Error(`Pythonサーバーを起動できなかった: ${error.message}`))
      }

      lines.on('line', (line) => {
        const parsed = parseReadyLine(line)
        if (parsed !== null) {
          finish(null, parsed)
        } else {
          process.stdout.write(`[python] ${line}\n`)
        }
      })
      child.once('exit', onExit)
      child.once('error', onError)
    })
  }

  private async waitForHealth(connection: Connection): Promise<void> {
    const deadline = Date.now() + HEALTH_TIMEOUT_MS
    let lastError: unknown = null
    while (Date.now() < deadline) {
      try {
        const response = await fetch(`${baseUrl(connection)}/health`)
        if (response.ok) {
          return
        }
        lastError = new Error(`/health が ${String(response.status)} を返した`)
      } catch (error) {
        lastError = error
      }
      await new Promise((resolve) => setTimeout(resolve, 200))
    }
    throw new Error(`Pythonサーバーの起動を確認できなかった: ${String(lastError)}`)
  }

  /** Electronの終了時に呼ぶ。 */
  async stop(): Promise<void> {
    const child = this.child
    this.child = null
    this.connection = null
    if (child === null || child.exitCode !== null) {
      return
    }
    const exited = new Promise<void>((resolve) => {
      const timer = setTimeout(() => {
        child.kill('SIGKILL')
        resolve()
      }, STOP_TIMEOUT_MS)
      child.once('exit', () => {
        clearTimeout(timer)
        resolve()
      })
    })
    // ツリーの終了と直の子の終了の両方を待つ。直の子が先に消えても、DBの
    // ファイルを握っている孫が残っていることがある。
    await killTree(child)
    await exited
  }
}

export function baseUrl(connection: Connection): string {
  return `http://127.0.0.1:${String(connection.port)}`
}
