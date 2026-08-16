import type { TaskType } from './types'

export const TASK_TYPES: readonly [TaskType, ...TaskType[]] = [
  { id: 'pushups', label: 'Pushups' },
  { id: 'leetcode', label: 'LeetCode problems' },
  { id: 'anki', label: 'Anki reviews' },
]
