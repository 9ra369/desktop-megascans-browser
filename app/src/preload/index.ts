import { contextBridge, ipcRenderer } from 'electron'

import type { Connection, DesktopApi } from '../shared/types'

/** 許可した操作だけを画面へ公開する。Node.jsのAPIは渡さない。 */
const api: DesktopApi = {
  getConnection: () => ipcRenderer.invoke('desktop:getConnection') as Promise<Connection>,
  chooseDownloadedFolder: () =>
    ipcRenderer.invoke('desktop:chooseDownloadedFolder') as Promise<string | null>,
  openAssetFolder: (relDir: string) =>
    ipcRenderer.invoke('desktop:openAssetFolder', relDir) as Promise<boolean>,
}

contextBridge.exposeInMainWorld('desktop', api)
