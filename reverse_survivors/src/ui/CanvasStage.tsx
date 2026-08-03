import type { ReactElement } from 'react'
import type { Ctx2D } from '../render/draw'
import { ARENA } from '../core/types'

interface Props {
  onCtx: (ctx: Ctx2D | null) => void
}

export const CanvasStage = ({ onCtx }: Props): ReactElement => (
  <canvas
    className="stage"
    width={ARENA.w}
    height={ARENA.h}
    ref={(el) => {
      onCtx(el === null ? null : el.getContext('2d'))
    }}
  />
)
