import { describe, expect, it } from 'vitest'
import { taskLabel } from './taskLabel'

describe('taskLabel', () => {
  it('maps a known task type id to its label', () => {
    expect(taskLabel('pushups')).toBe('Pushups')
  })

  it('falls back to the raw id for an unknown task type', () => {
    expect(taskLabel('unknown-type')).toBe('unknown-type')
  })
})
