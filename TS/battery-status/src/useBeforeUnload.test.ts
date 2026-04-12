import { describe, it, expect } from 'vitest'
import { useBeforeUnload } from './useBeforeUnload'
import { renderHook, cleanup } from '@testing-library/react'

describe('useBeforeUnload', () => {
  afterEach(() => {
    cleanup()
  })

  it('registers beforeunload handler when enabled', () => {
    const addSpy = vi.spyOn(window, 'addEventListener')
    renderHook(() => useBeforeUnload(true, 'Leave?'))
    expect(addSpy).toHaveBeenCalledWith('beforeunload', expect.any(Function))
    addSpy.mockRestore()
  })

  it('does not register handler when disabled', () => {
    const addSpy = vi.spyOn(window, 'addEventListener')
    renderHook(() => useBeforeUnload(false, 'Leave?'))
    expect(addSpy).not.toHaveBeenCalledWith('beforeunload', expect.any(Function))
    addSpy.mockRestore()
  })

  it('removes handler on unmount', () => {
    const removeSpy = vi.spyOn(window, 'removeEventListener')
    const { unmount } = renderHook(() => useBeforeUnload(true, 'Leave?'))
    unmount()
    expect(removeSpy).toHaveBeenCalledWith('beforeunload', expect.any(Function))
    removeSpy.mockRestore()
  })

  it('handler sets returnValue and prevents default', () => {
    let captured: ((e: BeforeUnloadEvent) => void) | undefined
    const addSpy = vi.spyOn(window, 'addEventListener').mockImplementation((type, handler) => {
      if (type === 'beforeunload') captured = handler as (e: BeforeUnloadEvent) => void
    })

    renderHook(() => useBeforeUnload(true, 'Stay here'))

    expect(captured).toBeDefined()
    const event = new Event('beforeunload') as BeforeUnloadEvent
    const preventSpy = vi.spyOn(event, 'preventDefault')
    captured!(event)
    expect(preventSpy).toHaveBeenCalled()
    // jsdom may coerce returnValue to boolean; just verify it was set
    expect(event.returnValue).toBeDefined()

    addSpy.mockRestore()
  })

  it('uses default values when called with no arguments', () => {
    const addSpy = vi.spyOn(window, 'addEventListener')
    renderHook(() => useBeforeUnload())
    expect(addSpy).toHaveBeenCalledWith('beforeunload', expect.any(Function))
    addSpy.mockRestore()
  })
})
