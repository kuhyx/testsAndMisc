import { act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

beforeEach(() => {
  vi.resetModules()
  document.body.innerHTML = ''
  vi.stubGlobal('requestAnimationFrame', (): number => 0)
  vi.stubGlobal('cancelAnimationFrame', (): void => undefined)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('main', () => {
  it('refuses to boot without a #root element', async () => {
    await expect(import('./main')).rejects.toThrow('missing #root')
  })

  it('mounts the app into #root', async () => {
    document.body.innerHTML = '<div id="root"></div>'
    await act(async () => {
      await import('./main')
    })
    expect(document.querySelector('h1')?.textContent).toBe('Reverse Survivors')
  })
})
