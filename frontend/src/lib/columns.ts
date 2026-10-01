import type { SortKey } from './filters'

/** Task list columns. `width` is a CSS grid track; title always flexes. */
export interface ColumnDef {
  id: string
  label: string
  width: string
  sortKey?: SortKey
  align?: 'start' | 'end'
}

export const COLUMNS: ColumnDef[] = [
  { id: 'title', label: 'Task', width: 'minmax(220px, 1fr)', sortKey: 'title' },
  { id: 'due', label: 'Due', width: '128px', sortKey: 'due' },
  { id: 'start', label: 'Starts', width: '104px' },
  { id: 'priority', label: 'Priority', width: '84px', sortKey: 'priority' },
  { id: 'tags', label: 'Tags', width: 'minmax(96px, 180px)' },
  { id: 'place', label: 'Place', width: '104px' },
  { id: 'repeat', label: 'Repeats', width: '168px' },
  { id: 'subtasks', label: 'Subtasks', width: '80px', align: 'end' },
  { id: 'notes', label: 'Notes', width: 'minmax(120px, 240px)' },
  { id: 'created', label: 'Created', width: '104px', sortKey: 'created' },
  { id: 'modified', label: 'Modified', width: '104px', sortKey: 'modified' },
  { id: 'completed', label: 'Completed', width: '104px', sortKey: 'completed' },
]

export const DEFAULT_COLUMNS = ['title', 'due', 'tags', 'repeat', 'priority']

export const columnById = (id: string) => COLUMNS.find((c) => c.id === id)
