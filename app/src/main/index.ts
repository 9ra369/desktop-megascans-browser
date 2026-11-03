import { BrowserWindow, app, dialog, ipcMain, shell } from 'electron'

import type { AppSettings, Connection } from '../shared/types'
import { resolveInsideDownloaded } from './downloadedPath'
import { resolveAppPaths } from './paths'
import { PythonServer, baseUrl } from './pythonServer'

const DEV_SERVER_URL = 'http://127.0.0.1:5173'
const isDev = process.env.NODE_ENV === 'development'

const paths = resolveAppPaths(__dirname)
const server = new PythonServer({
  userData: app.getPath('userData'),
  backendDir: paths.backendDir,
  executable: process.env.MEGASCANS_BROWSER_SERVER,
})

let connection: Connection | null = null
let window: BrowserWindow | null = null

/** Explorerを開く前に、DBが持っているDownloadedの場所をAPIから取る。 */
async function downloadedPath(): Promise<string | null> {
  if (connection === null) {
    return null
  }
  const response = await fetch(`${baseUrl(connection)}/settings`, {
    headers: { Authorization: `Bearer ${connection.token}` },
  })
  if (!response.ok) {
    return null
  }
  return ((await response.json()) as AppSettings).downloaded_path
}

function createWindow(): BrowserWindow {
  const created = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#14161a',
    show: false,
    title: 'Megascans Browser',
    webPreferences: {
      preload: paths.preloadScript,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
    },
  })

  created.once('ready-to-show', () => created.show())

  // 外部リンクは既定のブラウザへ。アプリ内では開かない。
  created.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) {
      void shell.openExternal(url)
    }
    return { action: 'deny' }
  })
  created.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith(DEV_SERVER_URL) && !url.startsWith('file://')) {
      event.preventDefault()
    }
  })

  if (isDev) {
    void created.loadURL(DEV_SERVER_URL)
  } else {
    void created.loadFile(paths.rendererEntry)
  }
  return created
}

function registerIpc(): void {
  ipcMain.handle('desktop:getConnection', (): Connection => {
    if (connection === null) {
      throw new Error('Pythonサーバーが起動していない')
    }
    return connection
  })

  ipcMain.handle('desktop:chooseDownloadedFolder', async (): Promise<string | null> => {
    const result = await dialog.showOpenDialog({
      title: 'Megascans の Downloaded フォルダを選ぶ',
      properties: ['openDirectory'],
    })
    return result.canceled ? null : (result.filePaths[0] ?? null)
  })

  ipcMain.handle('desktop:openAssetFolder', async (_event, relDir: unknown): Promise<boolean> => {
    if (typeof relDir !== 'string') {
      return false
    }
    const target = resolveInsideDownloaded(await downloadedPath(), relDir)
    if (target === null) {
      return false
    }
    // 空文字が返れば成功。Downloaded配下であることは上で確認済み。
    return (await shell.openPath(target)) === ''
  })
}

async function bootstrap(): Promise<void> {
  registerIpc()
  try {
    connection = await server.start()
  } catch (error) {
    dialog.showErrorBox('起動に失敗しました', String(error))
    app.quit()
    return
  }
  window = createWindow()
}

if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  app.on('second-instance', () => {
    window?.focus()
  })

  void app.whenReady().then(bootstrap)

  app.on('window-all-closed', () => {
    app.quit()
  })

  // Electronの終了時にPythonも止める。
  app.on('will-quit', (event) => {
    if (connection === null) {
      return
    }
    event.preventDefault()
    connection = null
    void server.stop().then(() => app.quit())
  })
}
