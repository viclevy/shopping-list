export function displayName(name) {
  if (!name) return ''
  return name.replace(/\b\w/g, c => c.toUpperCase())
}

export function normalizeCategory(value) {
  if (!value) return value
  return value.trim().replace(/\s+/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// Server timestamps are UTC but carry no "Z", which the browser would read as local time
export function serverDate(iso) {
  if (!iso) return null
  return new Date(/[zZ]$|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z')
}

export function formatDateTime(date, locale) {
  if (!date || isNaN(date)) return ''
  return date.toLocaleString(locale, {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

export function formatMoney(value) {
  return value == null || isNaN(value) ? '' : `$${Number(value).toFixed(2)}`
}
