import { TASK_TYPES } from '../stakes/taskTypes'

/** Falls back to the raw id so a debt recorded under a since-removed task type still renders. */
export const taskLabel = (taskTypeId: string): string =>
  TASK_TYPES.find((t) => t.id === taskTypeId)?.label ?? taskTypeId
