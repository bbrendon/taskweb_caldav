import type { Task } from './types'

/** Calendar math on 'YYYY-MM-DD' strings in the user's configured time zone. */

const dayFmtCache = new Map<string, Intl.DateTimeFormat>()
function dayFmt(tz: string) {
  let f = dayFmtCache.get(tz)
  if (!f) {
    f = new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' })
    dayFmtCache.set(tz, f)
  }
  return f
}

export const isDateOnly = (v: string) => v.length === 10

/** Local calendar day of a date or datetime value. */
export function dayOf(value: string, tz: string): string {
  return isDateOnly(value) ? value : dayFmt(tz).format(new Date(value))
}

export function today(tz: string): string {
  return dayFmt(tz).format(new Date())
}

export function addDays(day: string, n: number): string {
  const d = new Date(day + 'T12:00:00Z')
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

export function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(to + 'T12:00:00Z') - Date.parse(from + 'T12:00:00Z')) / 86_400_000)
}

/** Local wall-clock time 'HH:MM' of a datetime value. */
export function timeOf(value: string, tz: string): string | null {
  if (isDateOnly(value)) return null
  return new Intl.DateTimeFormat('en-GB', { timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false })
    .format(new Date(value))
}

function prettyTime(hhmm: string): string {
  const [h, m] = hhmm.split(':').map(Number)
  const suffix = h < 12 ? 'am' : 'pm'
  const h12 = h % 12 || 12
  return m ? `${h12}:${String(m).padStart(2, '0')}${suffix}` : `${h12}${suffix}`
}

export type Urgency = 'late' | 'today' | 'week' | 'far' | 'none'

export function urgency(task: Task, tz: string, weekDays = 7): Urgency {
  if (!task.due || task.status === 'COMPLETED' || task.status === 'CANCELLED') return 'none'
  if (task.virtual_tags.includes('OVERDUE')) return 'late'
  const days = daysBetween(today(tz), dayOf(task.due, tz))
  if (days <= 0) return 'today'
  if (days < weekDays) return 'week'
  return 'far'
}

const WEEKDAY = new Intl.DateTimeFormat('en-US', { weekday: 'short', timeZone: 'UTC' })
const MONTHDAY = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
const MONTHDAYYEAR = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })

/** Short label for a calendar day relative to today: Today, Tomorrow, Fri, Oct 14, Oct 14, 2027. */
export function dayLabel(day: string, tz: string): string {
  const t = today(tz)
  const n = daysBetween(t, day)
  const d = new Date(day + 'T12:00:00Z')
  if (n === 0) return 'Today'
  if (n === 1) return 'Tomorrow'
  if (n === -1) return 'Yesterday'
  if (n > 1 && n < 7) return WEEKDAY.format(d)
  return day.slice(0, 4) === t.slice(0, 4) ? MONTHDAY.format(d) : MONTHDAYYEAR.format(d)
}

/** Due label for list rows, e.g. '3 days late', 'Today 9am', 'Fri', 'Oct 14'. */
export function dueLabel(task: Task, tz: string): string {
  if (!task.due) return ''
  const day = dayOf(task.due, tz)
  const time = timeOf(task.due, tz)
  const open = task.status !== 'COMPLETED' && task.status !== 'CANCELLED'
  const late = daysBetween(day, today(tz))
  if (open && late > 0) return late === 1 ? '1 day late' : `${late} days late`
  const label = dayLabel(day, tz)
  return time ? `${label} ${prettyTime(time)}` : label
}

const UNIT_WORD: Record<string, [string, string]> = {
  D: ['day', 'days'], W: ['week', 'weeks'], M: ['month', 'months'], Y: ['year', 'years'],
}

export function parseInterval(s: string | null): { n: number; unit: 'D' | 'W' | 'M' | 'Y' } | null {
  const m = /^P(\d+)([DWMY])$/i.exec(s ?? '')
  return m ? { n: Number(m[1]), unit: m[2].toUpperCase() as 'D' | 'W' | 'M' | 'Y' } : null
}

function ORD(n: number): string {
  if (n % 100 >= 11 && n % 100 <= 13) return `${n}th`
  return n + ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] ?? 'th')
}
const DAYNAMES: Record<string, string> = { MO: 'Mon', TU: 'Tue', WE: 'Wed', TH: 'Thu', FR: 'Fri', SA: 'Sat', SU: 'Sun' }

/** Human description of a repeat: '30 days after done', 'Every 2 months on the 1st'. */
export function repeatLabel(task: Pick<Task, 'recur_after' | 'rrule'>): string {
  const iv = parseInterval(task.recur_after)
  if (iv) return `${iv.n} ${UNIT_WORD[iv.unit][iv.n === 1 ? 0 : 1]} after done`
  if (!task.rrule) return ''
  const p = Object.fromEntries(task.rrule.split(';').map((kv) => kv.split('=')))
  const n = Number(p.INTERVAL ?? 1)
  const unit = { DAILY: 'D', WEEKLY: 'W', MONTHLY: 'M', YEARLY: 'Y' }[p.FREQ as string]
  if (!unit) return 'Custom schedule'
  let s = n === 1 ? `Every ${UNIT_WORD[unit][0]}` : `Every ${n} ${UNIT_WORD[unit][1]}`
  if (p.BYDAY) s += ' on ' + String(p.BYDAY).split(',').map((d) => DAYNAMES[d.slice(-2)] ?? d).join(', ')
  if (p.BYMONTHDAY) s += ' on the ' + String(p.BYMONTHDAY).split(',').map((d) => ORD(Number(d))).join(', ')
  return s
}
