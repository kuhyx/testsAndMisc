import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { createInitialState } from '../core/sim'
import { snapshotOf } from '../core/snapshot'
import type { HudSnapshot } from '../core/snapshot'
import type { GameState } from '../core/types'
import { Hud } from './Hud'
import { SpawnBar } from './SpawnBar'

const snapWith = (mutate: (s: GameState) => void = () => undefined): HudSnapshot => {
  const s = createInitialState(1)
  mutate(s)
  return snapshotOf(s)
}

describe('Hud', () => {
  it('fills soul phials proportionally', () => {
    const { container } = render(<Hud snap={snapWith((s) => { s.director.energy = 200 })} onRestart={() => undefined} />)
    expect(container.querySelectorAll('.phial')).toHaveLength(10)
    expect(container.querySelectorAll('.phial-full')).toHaveLength(5)
    expect(screen.getByText('200 / 400')).toBeInTheDocument()
  })

  it('reports the intruder and its recent upgrades', () => {
    const snap = snapWith((s) => {
      s.survivor.hp = 50
      s.survivor.kills = 4
      s.upgrades = ['damage', 'multishot']
    })
    const { container } = render(<Hud snap={snap} onRestart={() => undefined} />)
    expect(container.querySelector('.hpbar-fill')).toHaveStyle({ width: '50%' })
    expect(screen.getByText(/4 of yours slain/)).toBeInTheDocument()
    expect(screen.getByText('sharper bolts')).toBeInTheDocument()
    expect(screen.getByText('split volley')).toBeInTheDocument()
  })

  it('shows no overlay while the game runs', () => {
    render(<Hud snap={snapWith()} onRestart={() => undefined} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('celebrates a director victory and restarts on demand', () => {
    const onRestart = vi.fn()
    const snap = snapWith((s) => { s.status = 'directorWon'; s.outcomeTime = 83 })
    render(<Hud snap={snap} onRestart={onRestart} />)
    expect(screen.getByText('The intruder falls')).toBeInTheDocument()
    expect(screen.getByText(/1:23/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /open the gates/i }))
    expect(onRestart).toHaveBeenCalledOnce()
  })

  it('mourns a survivor victory and restarts on demand', () => {
    const onRestart = vi.fn()
    render(<Hud snap={snapWith((s) => { s.status = 'survivorWon' })} onRestart={onRestart} />)
    expect(screen.getByText('Dawn breaks')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /raise a new horde/i }))
    expect(onRestart).toHaveBeenCalledOnce()
  })
})

describe('SpawnBar', () => {
  it('dispatches unit spawns the director can afford', () => {
    const onAction = vi.fn()
    render(<SpawnBar snap={snapWith()} onAction={onAction} />)
    fireEvent.click(screen.getByRole('button', { name: /rusher/i }))
    expect(onAction).toHaveBeenCalledWith({ type: 'spawn', kind: 'rusher' })
    expect(screen.getByRole('button', { name: /tank/i })).toBeDisabled()
  })

  it('dispatches waves when funded and blocks them when broke', () => {
    const onAction = vi.fn()
    const { rerender } = render(<SpawnBar snap={snapWith()} onAction={onAction} />)
    expect(screen.getByRole('button', { name: /wave 1/i })).toBeDisabled()
    rerender(<SpawnBar snap={snapWith((s) => { s.director.energy = 100 })} onAction={onAction} />)
    fireEvent.click(screen.getByRole('button', { name: /wave 1/i }))
    expect(onAction).toHaveBeenCalledWith({ type: 'wave' })
  })

  it('freezes all summoning once the game ends', () => {
    render(<SpawnBar snap={snapWith((s) => { s.status = 'directorWon' })} onAction={() => undefined} />)
    expect(screen.getByRole('button', { name: /rusher/i })).toBeDisabled()
  })

  it('walks a boss through locked, cooling, poor, and ready', () => {
    const onAction = vi.fn()
    const { rerender } = render(<SpawnBar snap={snapWith()} onAction={onAction} />)
    expect(screen.getByText(/seals break in 60s/)).toBeInTheDocument()

    rerender(<SpawnBar snap={snapWith((s) => { s.t = 61; s.director.bossCooldowns.colossus = 5 })} onAction={onAction} />)
    expect(screen.getByText(/recovering 5s/)).toBeInTheDocument()

    rerender(<SpawnBar snap={snapWith((s) => { s.t = 61; s.director.energy = 20 })} onAction={onAction} />)
    expect(screen.getByRole('button', { name: /colossus/i })).toBeDisabled()
    expect(screen.getByText('150 souls')).toBeInTheDocument()

    rerender(<SpawnBar snap={snapWith((s) => { s.t = 61; s.director.energy = 200 })} onAction={onAction} />)
    fireEvent.click(screen.getByRole('button', { name: /colossus/i }))
    expect(onAction).toHaveBeenCalledWith({ type: 'boss', kind: 'colossus' })
  })
})
