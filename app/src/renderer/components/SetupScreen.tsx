import { useState } from 'react'

interface Props {
  /** 入力済みのパス。初回は空。 */
  initialPath: string | null
  onSave: (downloadedPath: string) => Promise<void>
}

/** 初回設定。Downloadedの場所を選んで保存する。 */
export function SetupScreen({ initialPath, onSave }: Props): React.JSX.Element {
  const [path, setPath] = useState(initialPath ?? '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const choose = async (): Promise<void> => {
    const chosen = await window.desktop.chooseDownloadedFolder()
    if (chosen !== null) {
      setPath(chosen)
      setError(null)
    }
  }

  const save = async (): Promise<void> => {
    setSaving(true)
    setError(null)
    try {
      await onSave(path)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="center">
      <div className="setup">
        <h1>Megascans Browser</h1>
        <p className="muted">
          Choose the <code>Downloaded</code> folder from Bridge — the one that contains{' '}
          <code>3d</code>, <code>3dplant</code> and <code>surface</code>.
        </p>
        <div className="setup__path">{path === '' ? <span className="muted">Not selected</span> : path}</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" onClick={() => void choose()}>
            Choose folder
          </button>
          <button type="button" onClick={() => void save()} disabled={path === '' || saving}>
            {saving ? 'Saving…' : 'Save and start'}
          </button>
        </div>
        {error === null ? null : <p className="error">{error}</p>}
      </div>
    </div>
  )
}
