export type Status = 'NEEDS-ACTION' | 'IN-PROCESS' | 'COMPLETED' | 'CANCELLED'
export type PriorityBand = 'none' | 'high' | 'medium' | 'low'

export interface TimeAlarm { at?: string | null; offset?: string | null; related?: 'START' | 'END' | null }

export interface LocationAlarm {
  title: string
  address: string
  lat: number | null
  lon: number | null
  radius: number | null
  proximity: 'ARRIVE' | 'DEPART'
}

export interface Task {
  uid: string
  title: string
  notes: string
  status: Status
  priority: number
  priority_band: PriorityBand
  due: string | null
  start: string | null
  completed_at: string | null
  percent: number
  tags: string[]
  location: string
  url: string
  parent_uid: string | null
  starred: boolean
  recur_after: string | null
  rrule: string | null
  completions: string[]
  alarms: TimeAlarm[]
  location_alarm: LocationAlarm | null
  created: string | null
  last_modified: string | null
  virtual_tags: string[]
}

export type TaskPatch = Partial<Pick<Task,
  'title' | 'notes' | 'status' | 'priority' | 'due' | 'start' | 'tags' | 'location' | 'url' |
  'parent_uid' | 'starred' | 'recur_after' | 'rrule' | 'alarms' | 'location_alarm'>>

export interface Place { name: string; address: string; lat: number; lon: number; radius: number }

export interface AppConfig {
  timezone: string
  due_this_week_days: number
  tags: string[]
  places: Place[]
  priorities: Record<PriorityBand, number>
  virtual_tags: string[]
}
