/**
 * Read state tracking — localStorage-backed utility for marking posts as read.
 * Posts viewed via IntersectionObserver are stored with timestamps.
 * Auto-cleanup removes entries older than 7 days.
 */

const STORAGE_KEY = "x-brief-read-posts"

interface ReadEntry {
  /** Unix timestamp (ms) when post was marked read */
  t: number
}

type ReadStore = Record<string, ReadEntry>

function loadStore(): ReadStore {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    return JSON.parse(raw) as ReadStore
  } catch {
    return {}
  }
}

function saveStore(store: ReadStore): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
  } catch {
    // localStorage full — silently fail
  }
}

/** Mark an array of post IDs as read */
export function markPostsAsRead(postIds: string[]): void {
  const store = loadStore()
  const now = Date.now()
  for (const id of postIds) {
    if (!store[id]) {
      store[id] = { t: now }
    }
  }
  saveStore(store)
}

/** Get all read post IDs as a Set */
export function getReadPostIds(): Set<string> {
  const store = loadStore()
  return new Set(Object.keys(store))
}

/** Remove entries older than maxAgeHours (default 168 = 7 days) */
export function clearOldReadState(maxAgeHours: number = 168): void {
  const store = loadStore()
  const cutoff = Date.now() - maxAgeHours * 60 * 60 * 1000
  let changed = false
  for (const id of Object.keys(store)) {
    if (store[id].t < cutoff) {
      delete store[id]
      changed = true
    }
  }
  if (changed) saveStore(store)
}
