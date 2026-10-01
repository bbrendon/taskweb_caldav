import { addDays, dayOf, daysBetween, today } from './dates'
import type { Task } from './types'

/**
 * Views = a filter + sort + visible columns. Smart lists are built-in views;
 * saved searches are user views with the same shape, stored in server settings.
 */

export type ConditionField =
  | 'text' | 'tag' | 'smart' | 'priority' | 'place' | 'due' | 'starred' | 'repeat' | 'status'

export interface Condition {
  field: ConditionField
  op: string
  value?: string | number | null
}

export interface Filter {
  match: 'all' | 'any'
  conditions: Condition[]
  showCompleted: boolean
  showDeferred: boolean
}

export type SortKey = 'due' | 'priority' | 'title' | 'created' | 'modified' | 'completed'
export interface Sort { key: SortKey; dir: 'asc' | 'desc' }

export interface View {
  id: string
  name: string
  filter: Filter
  sort: Sort[]
  columns?: string[]
  builtin?: boolean
}

const base = (conditions: Condition[] = [], extra: Partial<Filter> = {}): Filter => ({
  match: 'all', conditions, showCompleted: false, showDeferred: false, ...extra,
})
const smart = (tag: string): Condition => ({ field: 'smart', op: 'has', value: tag })
const DUE_SORT: Sort[] = [{ key: 'due', dir: 'asc' }, { key: 'priority', dir: 'asc' }]

const SMART_LIST_DEFS: Omit<View, 'builtin'>[] = [
  { id: 'pending', name: 'Pending', filter: base(), sort: DUE_SORT },
  { id: 'today', name: 'Due today', filter: base([smart('DUE_TODAY'), smart('OVERDUE')], { match: 'any' }), sort: DUE_SORT },
  { id: 'week', name: 'Due this week', filter: base([smart('DUE_WEEK'), smart('OVERDUE')], { match: 'any' }), sort: DUE_SORT },
  { id: 'overdue', name: 'Overdue', filter: base([smart('OVERDUE')]), sort: DUE_SORT },
  { id: 'starred', name: 'Starred', filter: base([smart('STARRED')]), sort: DUE_SORT },
  { id: 'high', name: 'High priority', filter: base([smart('HIGH')]), sort: DUE_SORT },
  { id: 'recurring', name: 'Repeating', filter: base([smart('RECURRING')]), sort: DUE_SORT },
  { id: 'single', name: 'One-time', filter: base([smart('SINGLE')]), sort: DUE_SORT },
  { id: 'subtasks', name: 'Has subtasks', filter: base([smart('HAS_SUBTASKS')]), sort: DUE_SORT },
  { id: 'deferred', name: 'Deferred', filter: base([smart('DEFERRED')], { showDeferred: true }), sort: DUE_SORT },
  { id: 'completed', name: 'Completed', filter: base([{ field: 'status', op: 'is', value: 'done' }], { showCompleted: true, showDeferred: true }), sort: [{ key: 'completed', dir: 'desc' } as Sort] },
  { id: 'all', name: 'All', filter: base([], { showCompleted: true, showDeferred: true }), sort: DUE_SORT },
]
export const SMART_LISTS: View[] = SMART_LIST_DEFS.map((v) => ({ ...v, builtin: true }))

export const tagView = (tag: string): View => ({
  id: `tag:${tag}`, name: tag, builtin: true, sort: DUE_SORT,
  filter: base([{ field: 'tag', op: 'has', value: tag }]),
})

export const placeView = (place: string): View => ({
  id: `place:${place}`, name: place, builtin: true, sort: DUE_SORT,
  filter: base([{ field: 'place', op: 'is', value: place }]),
})

const isDone = (t: Task) => t.status === 'COMPLETED' || t.status === 'CANCELLED'

export const placeOf = (t: Task) => t.location_alarm?.title || t.location || ''

function matchCondition(t: Task, c: Condition, tz: string): boolean {
  const v = c.value
  const lower = typeof v === 'string' ? v.toLowerCase() : ''
  switch (c.field) {
    case 'text': {
      const hay = [t.title, t.notes, t.location, ...t.tags].join('\n').toLowerCase()
      return c.op === 'lacks' ? !hay.includes(lower) : hay.includes(lower)
    }
    case 'tag': {
      const has = t.tags.some((x) => x.toLowerCase() === lower)
      return c.op === 'lacks' ? !has : has
    }
    case 'smart': {
      const has = t.virtual_tags.includes(String(v))
      return c.op === 'lacks' ? !has : has
    }
    case 'priority':
      return c.op === 'isnt' ? t.priority_band !== v : t.priority_band === v
    case 'place': {
      const p = placeOf(t).toLowerCase()
      if (c.op === 'any') return !!p
      if (c.op === 'none') return !p
      return c.op === 'isnt' ? p !== lower : p === lower
    }
    case 'starred':
      return c.op === 'is' ? t.starred : !t.starred
    case 'repeat': {
      if (c.op === 'after') return !!t.recur_after
      if (c.op === 'fixed') return !!t.rrule
      if (c.op === 'none') return !t.recur_after && !t.rrule
      return !!(t.recur_after || t.rrule)
    }
    case 'status':
      return v === 'done' ? isDone(t) : !isDone(t)
    case 'due': {
      if (c.op === 'none') return !t.due
      if (c.op === 'any') return !!t.due
      if (!t.due) return false
      const day = dayOf(t.due, tz)
      const now = today(tz)
      const n = Number(v ?? 0)
      if (c.op === 'within') return day >= now && day <= addDays(now, n)
      if (c.op === 'before') return daysBetween(now, day) < n
      if (c.op === 'after') return daysBetween(now, day) > n
      return false
    }
  }
  return true
}

function needsValue(c: Condition): boolean {
  if (c.field === 'text' || c.field === 'tag') return true
  if (c.field === 'place') return c.op === 'is' || c.op === 'isnt'
  return false
}

export function matches(t: Task, f: Filter, tz: string, search = ''): boolean {
  if (!f.showCompleted && isDone(t)) return false
  if (!f.showDeferred && t.virtual_tags.includes('DEFERRED')) return false
  if (search && !matchSearch(t, search)) return false
  // Ignore conditions still being filled in (e.g. "Tag is [choose a tag]").
  const conditions = f.conditions.filter((c) => !needsValue(c) || (c.value !== '' && c.value !== null && c.value !== undefined))
  if (!conditions.length) return true
  const results = conditions.map((c) => matchCondition(t, c, tz))
  return f.match === 'all' ? results.every(Boolean) : results.some(Boolean)
}

/** Quick search: free text plus #tag, !high|!med|!low, @place, * (starred). */
export function matchSearch(t: Task, query: string): boolean {
  for (const raw of query.trim().split(/\s+/)) {
    const tok = raw.toLowerCase()
    if (!tok) continue
    if (tok.startsWith('#') && tok.length > 1) {
      if (!t.tags.some((x) => x.toLowerCase().startsWith(tok.slice(1)))) return false
    } else if (tok.startsWith('!') && tok.length > 1) {
      const band = { h: 'high', m: 'medium', l: 'low' }[tok[1]]
      if (band && t.priority_band !== band) return false
    } else if (tok.startsWith('@') && tok.length > 1) {
      if (!placeOf(t).toLowerCase().startsWith(tok.slice(1))) return false
    } else if (tok === '*') {
      if (!t.starred) return false
    } else {
      const hay = [t.title, t.notes, t.location, ...t.tags].join('\n').toLowerCase()
      if (!hay.includes(tok)) return false
    }
  }
  return true
}

const PRIORITY_RANK: Record<string, number> = { high: 0, medium: 1, low: 2, none: 3 }

function compare(a: Task, b: Task, s: Sort): number {
  const dir = s.dir === 'asc' ? 1 : -1
  const nullsLast = (x: string | null, y: string | null) =>
    x === y ? 0 : x === null ? 1 : y === null ? -1 : (x < y ? -1 : 1) * dir
  switch (s.key) {
    case 'due': {
      // All-day values sort at the start of their day.
      const k = (t: Task) => (t.due ? Date.parse(t.due.length === 10 ? t.due + 'T00:00' : t.due) : null)
      const x = k(a), y = k(b)
      return x === y ? 0 : x === null ? 1 : y === null ? -1 : (x - y) * dir
    }
    case 'priority':
      return (PRIORITY_RANK[a.priority_band] - PRIORITY_RANK[b.priority_band]) * dir
    case 'title':
      return a.title.localeCompare(b.title, undefined, { sensitivity: 'base' }) * dir
    case 'created':
      return nullsLast(a.created, b.created)
    case 'modified':
      return nullsLast(a.last_modified, b.last_modified)
    case 'completed':
      return nullsLast(a.completed_at, b.completed_at)
  }
}

export function sortTasks(tasks: Task[], sort: Sort[]): Task[] {
  return [...tasks].sort((a, b) => {
    for (const s of sort) {
      const c = compare(a, b, s)
      if (c) return c
    }
    return a.title.localeCompare(b.title)
  })
}

export interface Row { task: Task; depth: number; childCount: number }

/**
 * Matching tasks as an indented tree. A matching child appears under its parent when
 * the parent matches too; otherwise it stands at the top level so it is never hidden.
 */
export function buildRows(all: Task[], view: View, tz: string, search: string, collapsed: Set<string>): Row[] {
  const matched = all.filter((t) => matches(t, view.filter, tz, search))
  const ids = new Set(matched.map((t) => t.uid))
  const kids = new Map<string, Task[]>()
  for (const t of matched) {
    if (t.parent_uid && ids.has(t.parent_uid)) {
      kids.set(t.parent_uid, [...(kids.get(t.parent_uid) ?? []), t])
    }
  }
  const rows: Row[] = []
  const walk = (list: Task[], depth: number) => {
    for (const t of sortTasks(list, view.sort)) {
      const children = kids.get(t.uid) ?? []
      rows.push({ task: t, depth, childCount: children.length })
      if (children.length && !collapsed.has(t.uid)) walk(children, depth + 1)
    }
  }
  walk(matched.filter((t) => !t.parent_uid || !ids.has(t.parent_uid)), 0)
  return rows
}

// ------------------------------------------------------------------ filter builder

export type ValueKind = 'none' | 'text' | 'number' | 'tag' | 'place' | 'priority' | 'smart'

export interface FieldDef {
  field: ConditionField
  label: string
  ops: { op: string; label: string; value: ValueKind }[]
}

/** What the filter builder offers, in plain words. */
export const FIELD_DEFS: FieldDef[] = [
  { field: 'text', label: 'Text', ops: [
    { op: 'contains', label: 'contains', value: 'text' },
    { op: 'lacks', label: 'doesn’t contain', value: 'text' },
  ] },
  { field: 'tag', label: 'Tag', ops: [
    { op: 'has', label: 'is', value: 'tag' },
    { op: 'lacks', label: 'isn’t', value: 'tag' },
  ] },
  { field: 'place', label: 'Place', ops: [
    { op: 'is', label: 'is', value: 'place' },
    { op: 'isnt', label: 'isn’t', value: 'place' },
    { op: 'any', label: 'is set', value: 'none' },
    { op: 'none', label: 'isn’t set', value: 'none' },
  ] },
  { field: 'priority', label: 'Priority', ops: [
    { op: 'is', label: 'is', value: 'priority' },
    { op: 'isnt', label: 'isn’t', value: 'priority' },
  ] },
  { field: 'due', label: 'Due', ops: [
    { op: 'within', label: 'within the next … days', value: 'number' },
    { op: 'before', label: 'sooner than … days from today', value: 'number' },
    { op: 'after', label: 'later than … days from today', value: 'number' },
    { op: 'any', label: 'is set', value: 'none' },
    { op: 'none', label: 'isn’t set', value: 'none' },
  ] },
  { field: 'repeat', label: 'Repeats', ops: [
    { op: 'yes', label: 'in any way', value: 'none' },
    { op: 'after', label: 'after done', value: 'none' },
    { op: 'fixed', label: 'on a schedule', value: 'none' },
    { op: 'none', label: 'never', value: 'none' },
  ] },
  { field: 'starred', label: 'Starred', ops: [
    { op: 'is', label: 'yes', value: 'none' },
    { op: 'isnt', label: 'no', value: 'none' },
  ] },
  { field: 'smart', label: 'Status', ops: [
    { op: 'has', label: 'is', value: 'smart' },
    { op: 'lacks', label: 'isn’t', value: 'smart' },
  ] },
]

/** Virtual tags offered under "Status", with readable names. */
export const SMART_LABELS: Record<string, string> = {
  OVERDUE: 'Overdue', DUE_TODAY: 'Due today', DUE_WEEK: 'Due this week', DEFERRED: 'Deferred',
  HAS_SUBTASKS: 'Has subtasks', CHILD: 'A subtask', TAGGED: 'Tagged', UNTAGGED: 'Untagged',
}

export function defaultCondition(field: ConditionField): Condition {
  const def = FIELD_DEFS.find((d) => d.field === field)!
  const op = def.ops[0]
  const value = op.value === 'number' ? 7 : op.value === 'priority' ? 'high' : op.value === 'smart' ? 'OVERDUE' : ''
  return { field, op: op.op, value }
}

export const cloneFilter = (f: Filter): Filter => ({ ...f, conditions: f.conditions.map((c) => ({ ...c })) })

export const sameFilter = (a: Filter, b: Filter) => JSON.stringify(a) === JSON.stringify(b)
