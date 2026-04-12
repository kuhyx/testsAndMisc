import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { App } from './App'

// Mock the hooks
vi.mock('./useBattery')
vi.mock('./useBeforeUnload')

import { useBattery } from './useBattery'
import { useBeforeUnload } from './useBeforeUnload'

const mockUseBattery = vi.mocked(useBattery)
const mockUseBeforeUnload = vi.mocked(useBeforeUnload)

describe('App', () => {
  afterEach(() => {
    cleanup()
    vi.resetAllMocks()
  })

  it('shows unsupported message when not supported', () => {
    mockUseBattery.mockReturnValue({
      supported: false,
      loading: false,
      error: null,
      charging: false,
      chargingTime: Infinity,
      dischargingTime: Infinity,
      level: 1,
    })

    render(<App />)
    expect(screen.getByText('Battery Status')).toBeInTheDocument()
    expect(screen.getByText(/not supported/)).toBeInTheDocument()
    expect(mockUseBeforeUnload).toHaveBeenCalledWith(true, expect.any(String))
  })

  it('shows loading state', () => {
    mockUseBattery.mockReturnValue({
      supported: true,
      loading: true,
      error: null,
      charging: false,
      chargingTime: Infinity,
      dischargingTime: Infinity,
      level: 1,
    })

    render(<App />)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('shows error message', () => {
    mockUseBattery.mockReturnValue({
      supported: true,
      loading: false,
      error: 'Something went wrong',
      charging: false,
      chargingTime: Infinity,
      dischargingTime: Infinity,
      level: 1,
    })

    render(<App />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('shows battery info when charging', () => {
    mockUseBattery.mockReturnValue({
      supported: true,
      loading: false,
      error: null,
      charging: true,
      chargingTime: 7200,
      dischargingTime: Infinity,
      level: 0.65,
    })

    render(<App />)
    expect(screen.getByText('Yes')).toBeInTheDocument()
    expect(screen.getByText('65%')).toBeInTheDocument()
    expect(screen.getByText('Time to full:')).toBeInTheDocument()
    expect(screen.getByText('2h 0m')).toBeInTheDocument()
    // Time to empty should not be shown when charging
    expect(screen.queryByText('Time to empty:')).not.toBeInTheDocument()
  })

  it('shows battery info when discharging', () => {
    mockUseBattery.mockReturnValue({
      supported: true,
      loading: false,
      error: null,
      charging: false,
      chargingTime: Infinity,
      dischargingTime: 5400,
      level: 0.42,
    })

    render(<App />)
    expect(screen.getByText('No')).toBeInTheDocument()
    expect(screen.getByText('42%')).toBeInTheDocument()
    expect(screen.getByText('Time to empty:')).toBeInTheDocument()
    expect(screen.getByText('1h 30m')).toBeInTheDocument()
    expect(screen.queryByText('Time to full:')).not.toBeInTheDocument()
  })

  it('handles short times (minutes only)', () => {
    mockUseBattery.mockReturnValue({
      supported: true,
      loading: false,
      error: null,
      charging: false,
      chargingTime: Infinity,
      dischargingTime: 300,
      level: 0.1,
    })

    render(<App />)
    expect(screen.getByText('5m')).toBeInTheDocument()
  })

  it('handles infinite discharging time as N/A', () => {
    mockUseBattery.mockReturnValue({
      supported: true,
      loading: false,
      error: null,
      charging: false,
      chargingTime: Infinity,
      dischargingTime: Infinity,
      level: 0.5,
    })

    render(<App />)
    // Infinity is a number so it would try to show, but formatTime returns N/A
    expect(screen.getByText('N/A')).toBeInTheDocument()
  })

  it('handles negative time as N/A', () => {
    mockUseBattery.mockReturnValue({
      supported: true,
      loading: false,
      error: null,
      charging: true,
      chargingTime: -1,
      dischargingTime: Infinity,
      level: 0.5,
    })

    render(<App />)
    expect(screen.getByText('N/A')).toBeInTheDocument()
  })
})
