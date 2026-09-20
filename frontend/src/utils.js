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
  const trimmed = iso.replace(/(\.\d{3})\d+/, '$1') // some browsers reject microseconds
  return new Date(/[zZ]$|[+-]\d\d:?\d\d$/.test(trimmed) ? trimmed : trimmed + 'Z')
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
