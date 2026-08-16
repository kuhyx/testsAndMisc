import { describe, expect, it } from 'vitest'
import { TASK_TYPES } from './taskTypes'

describe('TASK_TYPES', () => {
  it('is non-empty', () => {
    expect(TASK_TYPES.length).toBeGreaterThan(0)
  })

  it('has unique ids', () => {
    const ids = TASK_TYPES.map((t) => t.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('gives every entry a non-empty id and label', () => {
    for (const taskType of TASK_TYPES) {
      expect(taskType.id.length).toBeGreaterThan(0)
      expect(taskType.label.length).toBeGreaterThan(0)
    }
  })
})
