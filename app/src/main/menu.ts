import type { MenuItemConstructorOptions } from 'electron'

/**
 * アプリのメニュー。
 *
 * Electronの既定メニューは使わない。Editは Undo と Redo だけにする（この画面で
 * 文字を打つのは検索欄だけで、Cut / Copy / Paste / Select All は不要）。
 * ラベルは `role` の既定に任せず明示する。環境の言語に関わらず英語で出すため。
 */
export function buildMenuTemplate(): MenuItemConstructorOptions[] {
  return [
    {
      label: 'File',
      submenu: [{ role: 'quit', label: 'Quit' }],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo', label: 'Undo' },
        { role: 'redo', label: 'Redo' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload', label: 'Reload' },
        { role: 'toggleDevTools', label: 'Toggle Developer Tools' },
        { type: 'separator' },
        { role: 'resetZoom', label: 'Actual Size' },
        { role: 'zoomIn', label: 'Zoom In' },
        { role: 'zoomOut', label: 'Zoom Out' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: 'Toggle Full Screen' },
      ],
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize', label: 'Minimize' },
        { role: 'close', label: 'Close' },
      ],
    },
  ]
}
