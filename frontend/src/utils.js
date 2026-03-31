export function displayName(name) {
  if (!name) return ''
  return name.replace(/\b\w/g, c => c.toUpperCase())
}

export function normalizeCategory(value) {
  if (!value) return value
  return value.trim().replace(/\s+/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
