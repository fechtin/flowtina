export function formatDate(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDateShort(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString(undefined, { month: 'short', day: '2-digit', year: 'numeric' })
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat().format(value ?? 0)
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(value ?? 0)
}

export function formatPercent(value: number): string {
  const v = value ?? 0
  const normalized = v > 1 ? v : v * 100
  return `${normalized.toFixed(1)}%`
}

export function truncate(text: string, max = 120): string {
  if (!text) return ''
  return text.length > max ? `${text.slice(0, max)}…` : text
}
