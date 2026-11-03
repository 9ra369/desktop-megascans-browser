import { describe, expect, it } from 'vitest'

import { READY_PREFIX, parseReadyLine } from '../src/main/readyLine'

describe('parseReadyLine', () => {
  it('reads the port and the token', () => {
    const line = `${READY_PREFIX}{"port":52294,"token":"a-token"}`

    expect(parseReadyLine(line)).toEqual({ port: 52294, token: 'a-token' })
  })

  it('ignores a line without the marker', () => {
    expect(parseReadyLine('INFO: Started server process')).toBeNull()
  })

  it('ignores the marker with broken json', () => {
    expect(parseReadyLine(`${READY_PREFIX}{ broken`)).toBeNull()
  })

  it('ignores the marker without a port', () => {
    expect(parseReadyLine(`${READY_PREFIX}{"token":"a-token"}`)).toBeNull()
  })

  it('ignores the marker without a token', () => {
    expect(parseReadyLine(`${READY_PREFIX}{"port":1}`)).toBeNull()
  })

  it('tolerates surrounding whitespace', () => {
    expect(parseReadyLine(`  ${READY_PREFIX}{"port":1,"token":"t"}  `)).toEqual({
      port: 1,
      token: 't',
    })
  })
})
