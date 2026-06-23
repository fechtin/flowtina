// Helpers to translate between a friendly schedule form (Hourly / Daily / Weekly /
// Monthly / Yearly) and the cron expression / interval the backend understands.

export type Frequency = 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly' | 'custom' | 'interval'

export interface ScheduleForm {
  frequency: Frequency
  time: string // "HH:MM"
  dayOfWeek: number // 0 = Sunday .. 6 = Saturday
  dayOfMonth: number // 1 .. 31
  month: number // 1 .. 12
  cron: string // raw cron, used by the "custom" frequency
  intervalSeconds: number // used by the "interval" frequency
}

export function defaultSchedule(): ScheduleForm {
  return {
    frequency: 'daily',
    time: '09:00',
    dayOfWeek: 1,
    dayOfMonth: 1,
    month: 1,
    cron: '',
    intervalSeconds: 3600,
  }
}

function splitTime(time: string): { minute: number; hour: number } {
  const [h, m] = (time || '09:00').split(':')
  const hour = Math.min(23, Math.max(0, Number(h) || 0))
  const minute = Math.min(59, Math.max(0, Number(m) || 0))
  return { minute, hour }
}

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

/** Build a cron expression for cron-based frequencies; returns null for interval. */
export function buildCron(s: ScheduleForm): string | null {
  const { minute, hour } = splitTime(s.time)
  switch (s.frequency) {
    case 'hourly':
      return `${minute} * * * *`
    case 'daily':
      return `${minute} ${hour} * * *`
    case 'weekly':
      return `${minute} ${hour} * * ${s.dayOfWeek}`
    case 'monthly':
      return `${minute} ${hour} ${s.dayOfMonth} * *`
    case 'yearly':
      return `${minute} ${hour} ${s.dayOfMonth} ${s.month} *`
    case 'custom':
      return s.cron.trim()
    case 'interval':
      return null
  }
}

const isNum = (v: string): boolean => /^\d+$/.test(v)

/** Parse an existing cron expression back into the friendly form. Falls back to "custom". */
export function parseCron(cron: string): ScheduleForm {
  const base = defaultSchedule()
  const parts = cron.trim().split(/\s+/)
  if (parts.length !== 5 || !isNum(parts[0])) {
    return { ...base, frequency: 'custom', cron }
  }
  const [min, hr, dom, mon, dow] = parts
  const time = isNum(hr) ? `${pad(Number(hr))}:${pad(Number(min))}` : `00:${pad(Number(min))}`

  if (hr === '*' && dom === '*' && mon === '*' && dow === '*') {
    return { ...base, frequency: 'hourly', time }
  }
  if (isNum(hr) && dom === '*' && mon === '*' && dow === '*') {
    return { ...base, frequency: 'daily', time }
  }
  if (isNum(hr) && dom === '*' && mon === '*' && isNum(dow)) {
    return { ...base, frequency: 'weekly', time, dayOfWeek: Number(dow) % 7 }
  }
  if (isNum(hr) && isNum(dom) && mon === '*' && dow === '*') {
    return { ...base, frequency: 'monthly', time, dayOfMonth: Number(dom) }
  }
  if (isNum(hr) && isNum(dom) && isNum(mon) && dow === '*') {
    return { ...base, frequency: 'yearly', time, dayOfMonth: Number(dom), month: Number(mon) }
  }
  return { ...base, frequency: 'custom', cron }
}

/** The IANA timezone the user's browser is currently set to (e.g. "Asia/Ho_Chi_Minh"). */
export function currentTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  } catch {
    return 'UTC'
  }
}

/** Full list of IANA timezones, always including UTC. */
export function timezoneList(): string[] {
  try {
    const zones = (Intl as unknown as { supportedValuesOf?: (key: string) => string[] }).supportedValuesOf?.(
      'timeZone',
    )
    if (zones && zones.length) return zones.includes('UTC') ? zones : ['UTC', ...zones]
  } catch {
    // fall through to minimal default
  }
  return ['UTC', currentTimezone()]
}

/** Localized weekday names, index 0 = Sunday. */
export function weekdayNames(locale: string): string[] {
  const fmt = new Intl.DateTimeFormat(locale, { weekday: 'long' })
  return Array.from({ length: 7 }, (_, i) => fmt.format(new Date(Date.UTC(2023, 0, 1 + i))))
}

/** Localized month names, index 0 = January. */
export function monthNames(locale: string): string[] {
  const fmt = new Intl.DateTimeFormat(locale, { month: 'long' })
  return Array.from({ length: 12 }, (_, i) => fmt.format(new Date(Date.UTC(2023, i, 1))))
}
