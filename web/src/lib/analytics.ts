/**
 * Simple client-side analytics — fire-and-forget event tracking via localStorage.
 */

const STORAGE_KEY = "x-brief-analytics"
const MAX_EVENTS = 5000 // cap to prevent localStorage bloat

export interface AnalyticsEvent {
  type: "page_view" | "post_impression" | "post_click" | "tab_switch" | "media_open"
  ts: number // Unix timestamp (ms)
  meta?: Record<string, string | number>
}

function loadEvents(): AnalyticsEvent[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    return JSON.parse(raw) as AnalyticsEvent[]
  } catch {
    return []
  }
}

function saveEvents(events: AnalyticsEvent[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events))
  } catch {
    // localStorage full — drop oldest half
    try {
      const trimmed = events.slice(Math.floor(events.length / 2))
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed))
    } catch {
      // give up
    }
  }
}

/** Track a single event. Fire-and-forget — never throws. */
export function trackEvent(
  type: AnalyticsEvent["type"],
  meta?: Record<string, string | number>
): void {
  try {
    const events = loadEvents()
    events.push({ type, ts: Date.now(), meta })
    // Trim if over cap
    if (events.length > MAX_EVENTS) {
      events.splice(0, events.length - MAX_EVENTS)
    }
    saveEvents(events)
  } catch {
    // never throw
  }
}

/** Get all events, optionally filtered by since date */
export function getAnalytics(since?: Date): AnalyticsEvent[] {
  const events = loadEvents()
  if (!since) return events
  const cutoff = since.getTime()
  return events.filter((e) => e.ts >= cutoff)
}

/** Clear all analytics data */
export function clearAnalytics(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}
