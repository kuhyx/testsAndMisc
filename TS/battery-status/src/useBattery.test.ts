import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, act, cleanup } from '@testing-library/react'
import { useBattery } from './useBattery'

type BatteryManagerLike = {
  charging: boolean
  chargingTime: number
  dischargingTime: number
  level: number
  addEventListener?: (type: string, listener: () => void) => void
  removeEventListener?: (type: string, listener: () => void) => void
  onchargingchange?: (() => void) | null
  onlevelchange?: (() => void) | null
  onchargingtimechange?: (() => void) | null
  ondischargingtimechange?: (() => void) | null
}

function createMockBattery(overrides: Partial<BatteryManagerLike> = {}): BatteryManagerLike {
  return {
    charging: true,
    chargingTime: 3600,
    dischargingTime: Infinity,
    level: 0.75,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    ...overrides,
  }
}

describe('useBattery', () => {
  const originalGetBattery = navigator.getBattery

  afterEach(() => {
    cleanup()
    Object.defineProperty(navigator, 'getBattery', {
      value: originalGetBattery,
      configurable: true,
      writable: true,
    })
  })

  it('returns supported=false when getBattery is not available', async () => {
    Object.defineProperty(navigator, 'getBattery', {
      value: undefined,
      configurable: true,
      writable: true,
    })

    const { result } = renderHook(() => useBattery())
    // Wait for the async init to complete
    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    expect(result.current.supported).toBe(false)
  })

  it('returns battery state when getBattery resolves', async () => {
    const mockBattery = createMockBattery()
    Object.defineProperty(navigator, 'getBattery', {
      value: () => Promise.resolve(mockBattery),
      configurable: true,
      writable: true,
    })

    const { result } = renderHook(() => useBattery())
    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.supported).toBe(true)
    expect(result.current.charging).toBe(true)
    expect(result.current.level).toBe(0.75)
    expect(result.current.chargingTime).toBe(3600)
    expect(result.current.error).toBeNull()
  })

  it('subscribes to battery events and cleans up on unmount', async () => {
    const mockBattery = createMockBattery()
    Object.defineProperty(navigator, 'getBattery', {
      value: () => Promise.resolve(mockBattery),
      configurable: true,
      writable: true,
    })

    const { result, unmount } = renderHook(() => useBattery())
    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(mockBattery.addEventListener).toHaveBeenCalledWith('chargingchange', expect.any(Function))
    expect(mockBattery.addEventListener).toHaveBeenCalledWith('levelchange', expect.any(Function))
    expect(mockBattery.addEventListener).toHaveBeenCalledWith('chargingtimechange', expect.any(Function))
    expect(mockBattery.addEventListener).toHaveBeenCalledWith('dischargingtimechange', expect.any(Function))

    unmount()

    expect(mockBattery.removeEventListener).toHaveBeenCalledWith('chargingchange', expect.any(Function))
    expect(mockBattery.removeEventListener).toHaveBeenCalledWith('levelchange', expect.any(Function))
  })

  it('uses fallback on* properties when addEventListener is missing', async () => {
    const mockBattery = createMockBattery({
      addEventListener: undefined,
      removeEventListener: undefined,
      onlevelchange: null,
      onchargingchange: null,
      onchargingtimechange: null,
      ondischargingtimechange: null,
    })

    Object.defineProperty(navigator, 'getBattery', {
      value: () => Promise.resolve(mockBattery),
      configurable: true,
      writable: true,
    })

    const { result, unmount } = renderHook(() => useBattery())
    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(mockBattery.onchargingchange).toBeTypeOf('function')
    expect(mockBattery.onlevelchange).toBeTypeOf('function')
    expect(mockBattery.onchargingtimechange).toBeTypeOf('function')
    expect(mockBattery.ondischargingtimechange).toBeTypeOf('function')

    // Simulate change via fallback property
    mockBattery.level = 0.5
    act(() => {
      mockBattery.onlevelchange!()
    })
    expect(result.current.level).toBe(0.5)

    // Unmount clears the callbacks
    unmount()
    expect(mockBattery.onchargingchange).toBeNull()
    expect(mockBattery.onlevelchange).toBeNull()
  })

  it('updates state when battery events fire', async () => {
    const listeners = new Map<string, () => void>()
    const mockBattery = createMockBattery({
      addEventListener: vi.fn((type: string, listener: () => void) => {
        listeners.set(type, listener)
      }),
      removeEventListener: vi.fn(),
    })

    Object.defineProperty(navigator, 'getBattery', {
      value: () => Promise.resolve(mockBattery),
      configurable: true,
      writable: true,
    })

    const { result } = renderHook(() => useBattery())
    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Simulate a level change
    mockBattery.level = 0.5
    mockBattery.charging = false
    act(() => {
      listeners.get('levelchange')!()
    })

    expect(result.current.level).toBe(0.5)
    expect(result.current.charging).toBe(false)
  })

  it('handles getBattery rejection with error message', async () => {
    Object.defineProperty(navigator, 'getBattery', {
      value: () => Promise.reject(new Error('Permission denied')),
      configurable: true,
      writable: true,
    })

    const { result } = renderHook(() => useBattery())
    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Permission denied')
  })

  it('handles getBattery rejection with non-Error thrown', async () => {
    Object.defineProperty(navigator, 'getBattery', {
      value: () => Promise.reject('string error'),
      configurable: true,
      writable: true,
    })

    const { result } = renderHook(() => useBattery())
    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to read battery status')
  })

  it('handles getBattery resolving to null', async () => {
    Object.defineProperty(navigator, 'getBattery', {
      value: () => Promise.resolve(null),
      configurable: true,
      writable: true,
    })

    const { result } = renderHook(() => useBattery())
    // The hook would return early since battery is null, staying in loading state
    // Wait a tick to let the async init() run
    await new Promise(r => setTimeout(r, 50))
    // Since early return doesn't call setLoading(false), it stays loading
    expect(result.current.loading).toBe(true)
  })
})
