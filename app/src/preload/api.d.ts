import type { DesktopApi } from '../shared/types'

declare global {
  interface Window {
    /** preloadが `contextBridge` で公開する操作。 */
    desktop: DesktopApi
  }
}

export {}
