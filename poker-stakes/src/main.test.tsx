import { act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { vi } from 'vitest'

beforeEach(() => {
  vi.resetModules()
  document.body.innerHTML = ''
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('main', () => {
  it('refuses to boot without a #root element', async () => {
    await expect(import('./main')).rejects.toThrow('root element not found')
  })

  it('mounts the app into #root', async () => {
    document.body.innerHTML = '<div id="root"></div>'
    await act(async () => {
      await import('./main')
    })
    // Asserts the mount happened, not the whole app's copy — App has its own tests for that.
    expect(document.querySelector('#root')?.textContent).toContain('Poker Stakes')
  })
})
