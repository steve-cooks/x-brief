"use client"

import { useRef, useCallback, useEffect } from "react"

interface UseSwipeTabsOptions {
  /** Ordered list of tab IDs */
  tabIds: string[]
  /** Currently active tab */
  activeTab: string
  /** Callback to change tab */
  onTabChange: (tabId: string) => void
  /** Minimum distance (px) for a swipe to register. Default: 50 */
  threshold?: number
  /** Minimum velocity (px/ms) for a flick to register. Default: 0.3 */
  velocityThreshold?: number
  /** Whether swipe is enabled. Default: true */
  enabled?: boolean
}

/**
 * Hook that attaches horizontal swipe detection to a container ref.
 * Distinguishes horizontal swipes from vertical scrolling so they don't conflict.
 */
export function useSwipeTabs({
  tabIds,
  activeTab,
  onTabChange,
  threshold = 50,
  velocityThreshold = 0.3,
  enabled = true,
}: UseSwipeTabsOptions) {
  const containerRef = useRef<HTMLDivElement>(null)
  const touchState = useRef<{
    startX: number
    startY: number
    startTime: number
    locked: "horizontal" | "vertical" | null
  } | null>(null)

  const handleTouchStart = useCallback(
    (e: TouchEvent) => {
      if (!enabled || tabIds.length < 2) return
      const touch = e.touches[0]
      touchState.current = {
        startX: touch.clientX,
        startY: touch.clientY,
        startTime: Date.now(),
        locked: null,
      }
    },
    [enabled, tabIds.length]
  )

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      const state = touchState.current
      if (!state) return

      const touch = e.touches[0]
      const dx = touch.clientX - state.startX
      const dy = touch.clientY - state.startY

      // Lock direction after 10px of movement
      if (!state.locked && (Math.abs(dx) > 10 || Math.abs(dy) > 10)) {
        state.locked = Math.abs(dx) > Math.abs(dy) ? "horizontal" : "vertical"
      }

      // If horizontal swipe, prevent vertical scroll
      if (state.locked === "horizontal") {
        e.preventDefault()
      }
    },
    []
  )

  const handleTouchEnd = useCallback(
    (e: TouchEvent) => {
      const state = touchState.current
      if (!state) return
      touchState.current = null

      if (state.locked !== "horizontal") return

      const touch = e.changedTouches[0]
      const dx = touch.clientX - state.startX
      const elapsed = Date.now() - state.startTime
      const velocity = Math.abs(dx) / elapsed

      const currentIndex = tabIds.indexOf(activeTab)
      if (currentIndex === -1) return

      // Check if swipe meets threshold or velocity
      const isSwipe =
        Math.abs(dx) >= threshold || velocity >= velocityThreshold

      if (!isSwipe) return

      if (dx < 0 && currentIndex < tabIds.length - 1) {
        // Swipe left → next tab
        onTabChange(tabIds[currentIndex + 1])
      } else if (dx > 0 && currentIndex > 0) {
        // Swipe right → previous tab
        onTabChange(tabIds[currentIndex - 1])
      }
    },
    [tabIds, activeTab, onTabChange, threshold, velocityThreshold]
  )

  useEffect(() => {
    const el = containerRef.current
    if (!el || !enabled) return

    el.addEventListener("touchstart", handleTouchStart, { passive: true })
    el.addEventListener("touchmove", handleTouchMove, { passive: false })
    el.addEventListener("touchend", handleTouchEnd, { passive: true })

    return () => {
      el.removeEventListener("touchstart", handleTouchStart)
      el.removeEventListener("touchmove", handleTouchMove)
      el.removeEventListener("touchend", handleTouchEnd)
    }
  }, [enabled, handleTouchStart, handleTouchMove, handleTouchEnd])

  return containerRef
}
