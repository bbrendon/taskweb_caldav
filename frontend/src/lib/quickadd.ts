import { addDays, dayLabel, today } from './dates'
import type { Place, TaskPatch } from './types'

/**
 * Quick-add parser. Recognized anywhere in the text:
 *   #tag                       tag
 *   !high !med !low (!h !m !l) priority
 *   *                          starred
 *   @Place                     preset place (adds an arrive alert)
 *   today tomorrow mon..sun    due day ("next fri" works too)
 *   in 3d / in 2w / in 1m      due day
 *   oct 14 / 10/14 / 2026-10-14
 *   9am 9:30pm 21:00           due time
 *   every 30d [after]          repeat N days/weeks/months/years after done
 * Everything else is the title.
 */

export interface Chip { kind: string; label: string }
export interface Parsed { title: string; patch: TaskPatch; chips: Chip[] }

const WEEKDAYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
const UNIT: Record<string, 'D' | 'W' | 'M' | 'Y'> = {
  d: 'D', day: 'D', days: 'D', w: 'W', wk: 'W', week: 'W', weeks: 'W',
  m: 'M', mo: 'M', month: 'M', months: 'M', y: 'Y', yr: 'Y', year: 'Y', years: 'Y',
}
const UNIT_NAME = { D: 'day', W: 'week', M: 'month', Y: 'year' }

/** Read '30d', '30 days' or 'week' starting at toks[j]; `used` = tokens consumed. */
function readAmount(toks: string[], j: number): { n: number; unit: 'D' | 'W' | 'M' | 'Y'; used: number } | null {
  const a = toks[j]?.toLowerCase()
  if (!a) return null
  const joined = /^(\d+)([a-z]+)$/.exec(a)
  if (joined && UNIT[joined[2]]) return { n: Number(joined[1]), unit: UNIT[joined[2]], used: 1 }
  const b = toks[j + 1]?.toLowerCase()
  if (/^\d+$/.test(a) && b && UNIT[b]) return { n: Number(a), unit: UNIT[b], used: 2 }
  if (UNIT[a] && a.length > 1) return { n: 1, unit: UNIT[a], used: 1 }
  return null
}

function shiftMonths(day: string, n: number): string {
  const [y, m, d] = day.split('-').map(Number)
  const target = new Date(Date.UTC(y, m - 1 + n, 1))
  const last = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate()
  target.setUTCDate(Math.min(d, last))
  return target.toISOString().slice(0, 10)
}

function nextMonthDay(month: number, dayNum: number, now: string): string | null {
  let year = Number(now.slice(0, 4))
  const fmt = (y: number) => `${y}-${String(month + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`
  if (month < 0 || month > 11 || dayNum < 1 || dayNum > 31) return null
  if (fmt(year) < now) year += 1
  return fmt(year)
}

/** Offset of a wall-clock time in tz, as '+HH:MM' (handles DST). */
function offsetFor(day: string, hhmm: string, tz: string): string {
  const guess = new Date(`${day}T${hhmm}:00Z`)
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: tz, timeZoneName: 'longOffset' })
    .formatToParts(guess).find((p) => p.type === 'timeZoneName')?.value ?? 'GMT'
  const m = /GMT([+-]\d{2}):?(\d{2})?/.exec(parts)
  return m ? `${m[1]}:${m[2] ?? '00'}` : '+00:00'
}

export function localDateTime(day: string, hhmm: string, tz: string): string {
  return `${day}T${hhmm}:00${offsetFor(day, hhmm, tz)}`
}

export function parseQuickAdd(input: string, tz: string, places: Place[]): Parsed {
  const now = today(tz)
  const patch: TaskPatch = {}
  const chips: Chip[] = []
  const tags: string[] = []
  let due: string | null = null
  let time: string | null = null
  const words: string[] = []
  const toks = input.trim().split(/\s+/).filter(Boolean)

  for (let i = 0; i < toks.length; i++) {
    const tok = toks[i]
    const lo = tok.toLowerCase()
    const next = toks[i + 1]?.toLowerCase()

    if (/^#[\p{L}\p{N}_-]+$/u.test(tok)) { tags.push(tok.slice(1)); continue }
    if (/^!(h|hi|high|1)$/.test(lo)) { patch.priority = 1; continue }
    if (/^!(m|med|medium|5)$/.test(lo)) { patch.priority = 5; continue }
    if (/^!(l|lo|low|9)$/.test(lo)) { patch.priority = 9; continue }
    if (tok === '*') { patch.starred = true; continue }
    if (tok.startsWith('@') && tok.length > 1) {
      const place = places.find((p) => p.name.toLowerCase() === lo.slice(1))
      if (place) {
        patch.location = place.name
        patch.location_alarm = {
          title: place.name, address: place.address, lat: place.lat, lon: place.lon,
          radius: place.radius, proximity: 'ARRIVE',
        }
        chips.push({ kind: 'place', label: `Arriving at ${place.name}` })
        continue
      }
    }
    if (lo === 'today' || lo === 'tod') { due = now; continue }
    if (lo === 'tomorrow' || lo === 'tmr' || lo === 'tom') { due = addDays(now, 1); continue }
    const wd = WEEKDAYS.findIndex((w) => w.startsWith(lo) && lo.length >= 3)
    if (wd >= 0) {
      if (words.at(-1)?.toLowerCase() === 'next') words.pop()
      const cur = new Date(now + 'T12:00:00Z').getUTCDay()
      due = addDays(now, (wd - cur + 7) % 7 || 7)
      continue
    }
    if (lo === 'in') {
      const amt = readAmount(toks, i + 1)
      if (amt) {
        due = amt.unit === 'D' ? addDays(now, amt.n)
          : amt.unit === 'W' ? addDays(now, amt.n * 7)
          : shiftMonths(now, amt.unit === 'M' ? amt.n : amt.n * 12)
        i += amt.used
        continue
      }
    }
    if (lo === 'every') {
      const amt = readAmount(toks, i + 1)
      if (amt) {
        patch.recur_after = `P${amt.n}${amt.unit}`
        i += amt.used
        if (toks[i + 1]?.toLowerCase() === 'after') i += 1
        chips.push({ kind: 'repeat', label: `${amt.n} ${UNIT_NAME[amt.unit]}${amt.n === 1 ? '' : 's'} after done` })
        continue
      }
    }
    if (/^\d{4}-\d{2}-\d{2}$/.test(tok)) { due = tok; continue }
    const slash = /^(\d{1,2})\/(\d{1,2})$/.exec(tok)
    if (slash) {
      const d = nextMonthDay(Number(slash[1]) - 1, Number(slash[2]), now)
      if (d) { due = d; continue }
    }
    const mon = MONTHS.indexOf(lo.slice(0, 3))
    if (mon >= 0 && /^[a-z]+$/.test(lo) && next && /^\d{1,2}(st|nd|rd|th)?$/.test(next)) {
      const d = nextMonthDay(mon, parseInt(next, 10), now)
      if (d) { due = d; i += 1; continue }
    }
    const t = /^(\d{1,2})(?::(\d{2}))?(am|pm)?$/.exec(lo)
    if (t && (t[2] || t[3])) {
      let h = Number(t[1])
      if (t[3] === 'pm' && h < 12) h += 12
      if (t[3] === 'am' && h === 12) h = 0
      if (h < 24 && Number(t[2] ?? 0) < 60) {
        time = `${String(h).padStart(2, '0')}:${t[2] ?? '00'}`
        continue
      }
    }
    words.push(tok)
  }

  if (time && !due) due = now
  if (due) {
    patch.due = time ? localDateTime(due, time, tz) : due
    const [h, m] = (time ?? '').split(':').map(Number)
    const clock = time ? ` ${h % 12 || 12}${m ? ':' + String(m).padStart(2, '0') : ''}${h < 12 ? 'am' : 'pm'}` : ''
    chips.unshift({ kind: 'due', label: `Due ${dayLabel(due, tz)}${clock}` })
  }
  if (tags.length) {
    patch.tags = tags
    chips.push(...tags.map((t) => ({ kind: 'tag', label: `#${t}` })))
  }
  if (patch.priority) {
    chips.push({ kind: 'priority', label: { 1: 'High', 5: 'Medium', 9: 'Low' }[patch.priority as 1 | 5 | 9] + ' priority' })
  }
  if (patch.starred) chips.push({ kind: 'star', label: 'Starred' })
  const title = words.join(' ')
  patch.title = title
  return { title, patch, chips }
}
