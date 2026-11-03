import { describe, expect, it } from 'vitest'

import { resolveInsideDownloaded } from '../src/main/downloadedPath'

const DOWNLOADED = 'D:/Megascans/Downloaded'

describe('resolveInsideDownloaded', () => {
  it('resolves a relative folder below Downloaded', () => {
    const resolved = resolveInsideDownloaded(DOWNLOADED, 'surface/Concrete Pavement_wlrvaf3')

    expect(resolved).not.toBeNull()
    expect(resolved?.replace(/\\/g, '/')).toBe('D:/Megascans/Downloaded/surface/Concrete Pavement_wlrvaf3')
  })

  it('accepts a nested folder', () => {
    expect(resolveInsideDownloaded(DOWNLOADED, '3dplant/Dragon Tree_wfypejzha/Var1')).not.toBeNull()
  })

  it('rejects an escape with ..', () => {
    expect(resolveInsideDownloaded(DOWNLOADED, '../Secrets')).toBeNull()
    expect(resolveInsideDownloaded(DOWNLOADED, 'surface/../../Secrets')).toBeNull()
  })

  it('rejects an absolute path', () => {
    expect(resolveInsideDownloaded(DOWNLOADED, 'C:/Windows')).toBeNull()
    expect(resolveInsideDownloaded(DOWNLOADED, '/etc')).toBeNull()
  })

  it('rejects Downloaded itself', () => {
    expect(resolveInsideDownloaded(DOWNLOADED, '')).toBeNull()
    expect(resolveInsideDownloaded(DOWNLOADED, '.')).toBeNull()
  })

  it('rejects a sibling folder whose name starts the same', () => {
    expect(resolveInsideDownloaded('D:/Megascans/Downloaded', '../DownloadedOther/x')).toBeNull()
  })

  it('rejects a path with a null byte', () => {
    expect(resolveInsideDownloaded(DOWNLOADED, 'surface/x\u0000.json')).toBeNull()
  })

  it('rejects a backslash separated escape', () => {
    expect(resolveInsideDownloaded(DOWNLOADED, '..\\Secrets')).toBeNull()
  })

  it('returns null when Downloaded is not configured', () => {
    expect(resolveInsideDownloaded(null, 'surface/x')).toBeNull()
    expect(resolveInsideDownloaded('', 'surface/x')).toBeNull()
  })
})
