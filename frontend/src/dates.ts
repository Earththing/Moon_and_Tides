// Calendar dates in the browser's local timezone. Don't use
// toISOString().slice(0, 10) for this: that's the UTC date, which is already
// tomorrow on US evenings (after 4–5 pm Pacific).

/** YYYY-MM-DD for a Date, in local time. */
export function localDateStr(d: Date = new Date()): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** Today's local date as YYYY-MM-DD. */
export function todayStr(): string {
  return localDateStr()
}
