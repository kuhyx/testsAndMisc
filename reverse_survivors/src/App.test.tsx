import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { makeEnemy } from './core/sim'
import type { RafHarness } from './test/harness'
import { installRaf, makeCtxStub } from './test/harness'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

const pump = (raf: RafHarness, ts: number): void => {
  act(() => {
    raf.pump(ts)
  })
}

describe('App', () => {
  it('runs the loop and accrues souls even without a canvas context', () => {
    const raf = installRaf()
    render(<App />)
    expect(screen.getByText('30 / 400')).toBeInTheDocument()
    pump(raf, 0)
    for (let i = 1; i <= 20; i += 1) {
      pump(raf, i * 1000)
    }
    expect(screen.getByText('42 / 400')).toBeInTheDocument()
    expect(screen.getByText(/0:02 \/ 5:00/)).toBeInTheDocument()
  })

  it('spends souls on a spawn and draws the horde', () => {
    const raf = installRaf()
    const stub = makeCtxStub()
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext')
      .mockImplementation(() => stub as unknown as CanvasRenderingContext2D)
    render(<App seed={5} />)
    fireEvent.click(screen.getByRole('button', { name: /rusher/i }))
    pump(raf, 0)
    expect(screen.getByText('20 / 400')).toBeInTheDocument()
    const arcsWithHorde = stub.arc.mock.calls.length
    expect(arcsWithHorde).toBeGreaterThan(4)
  })

  it('shows the director victory overlay and restarts fresh', () => {
    const raf = installRaf()
    render(
      <App
        seed={9}
        boot={(state) => {
          state.survivor.hp = 5
          makeEnemy(state, 'rusher', { x: state.survivor.pos.x, y: state.survivor.pos.y })
        }}
      />,
    )
    pump(raf, 0)
    expect(screen.getByText('The intruder falls')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /open the gates/i }))
    expect(screen.queryByText('The intruder falls')).not.toBeInTheDocument()
    expect(screen.getByText('30 / 400')).toBeInTheDocument()
  })

  it('dispatches a director power from the bar', () => {
    const raf = installRaf()
    render(<App seed={9} boot={(state) => { state.director.energy = 400 }} />)
    pump(raf, 0)
    fireEvent.click(screen.getByRole('button', { name: /frenzy/i }))
    pump(raf, 16)
    expect(screen.getByText(/frenzied/i)).toBeInTheDocument()
  })

  it('shows the dawn overlay when the survivor outlasts the horde', () => {
    const raf = installRaf()
    render(<App boot={(state) => { state.duration = 0.05 }} />)
    pump(raf, 0)
    pump(raf, 100)
    expect(screen.getByText('Dawn breaks')).toBeInTheDocument()
  })
})
