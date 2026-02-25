"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { X, ChevronLeft, ChevronRight, Play } from "lucide-react"

interface MediaViewerItem {
  type: string // "photo" | "video" | "animated_gif"
  url?: string
  preview_image_url?: string
  video_url?: string
  alt_text?: string
}

interface MediaViewerProps {
  items: MediaViewerItem[]
  initialIndex: number
  onClose: () => void
  proxyUrl: (url: string | undefined | null) => string | undefined
}

/**
 * Full-screen media viewer — X-style lightbox with dark overlay.
 * Supports pinch-to-zoom on images, swipe between multiple items,
 * swipe-to-dismiss, and video playback controls.
 */
export function MediaViewer({
  items,
  initialIndex,
  onClose,
  proxyUrl,
}: MediaViewerProps) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex)
  const [isClosing, setIsClosing] = useState(false)

  // Zoom state
  const [scale, setScale] = useState(1)
  const [translate, setTranslate] = useState({ x: 0, y: 0 })

  // Touch tracking
  const touchState = useRef<{
    startX: number
    startY: number
    startTime: number
    locked: "horizontal" | "vertical" | null
    initialDistance: number | null
    initialScale: number
    translateAtStart: { x: number; y: number }
  } | null>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [dismissProgress, setDismissProgress] = useState(0)

  const item = items[currentIndex]
  const isMultiple = items.length > 1
  const isZoomed = scale > 1.05

  const resetTransform = useCallback(() => {
    setScale(1)
    setTranslate({ x: 0, y: 0 })
  }, [])

  const goTo = useCallback(
    (index: number) => {
      if (index >= 0 && index < items.length) {
        setCurrentIndex(index)
        resetTransform()
      }
    },
    [items.length, resetTransform]
  )

  const close = useCallback(() => {
    setIsClosing(true)
    setTimeout(onClose, 200)
  }, [onClose])

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close()
      if (e.key === "ArrowLeft") goTo(currentIndex - 1)
      if (e.key === "ArrowRight") goTo(currentIndex + 1)
    }
    window.addEventListener("keydown", handleKey)
    return () => window.removeEventListener("keydown", handleKey)
  }, [close, goTo, currentIndex])

  // Lock body scroll
  useEffect(() => {
    const orig = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.overflow = orig
    }
  }, [])

  // ---- Touch handling ----

  const getTouchDistance = (touches: React.TouchList): number => {
    if (touches.length < 2) return 0
    const dx = touches[0].clientX - touches[1].clientX
    const dy = touches[0].clientY - touches[1].clientY
    return Math.sqrt(dx * dx + dy * dy)
  }

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      const touch = e.touches[0]
      touchState.current = {
        startX: touch.clientX,
        startY: touch.clientY,
        startTime: Date.now(),
        locked: null,
        initialDistance:
          e.touches.length >= 2 ? getTouchDistance(e.touches) : null,
        initialScale: scale,
        translateAtStart: { ...translate },
      }
    },
    [scale, translate]
  )

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      const state = touchState.current
      if (!state) return

      // Pinch-to-zoom
      if (e.touches.length >= 2 && state.initialDistance) {
        const newDist = getTouchDistance(e.touches)
        const ratio = newDist / state.initialDistance
        const newScale = Math.max(1, Math.min(5, state.initialScale * ratio))
        setScale(newScale)
        return
      }

      const touch = e.touches[0]
      const dx = touch.clientX - state.startX
      const dy = touch.clientY - state.startY

      if (!state.locked && (Math.abs(dx) > 8 || Math.abs(dy) > 8)) {
        if (isZoomed) {
          // When zoomed, allow panning in all directions
          state.locked = "horizontal"
        } else {
          state.locked =
            Math.abs(dx) > Math.abs(dy) ? "horizontal" : "vertical"
        }
      }

      if (!state.locked) return

      if (isZoomed) {
        // Pan while zoomed
        setTranslate({
          x: state.translateAtStart.x + dx,
          y: state.translateAtStart.y + dy,
        })
      } else if (state.locked === "horizontal" && isMultiple) {
        setDragOffset({ x: dx, y: 0 })
      } else if (state.locked === "vertical") {
        // Swipe-to-dismiss
        setDismissProgress(dy)
      }
    },
    [isZoomed, isMultiple]
  )

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      const state = touchState.current
      if (!state) return
      touchState.current = null

      const touch = e.changedTouches[0]
      const dx = touch.clientX - state.startX
      const dy = touch.clientY - state.startY
      const elapsed = Date.now() - state.startTime
      const velocity = Math.abs(dx) / elapsed

      // If user was zoomed and panning, just snap scale bounds
      if (isZoomed) {
        if (scale < 1) {
          resetTransform()
        }
        setDragOffset({ x: 0, y: 0 })
        setDismissProgress(0)
        return
      }

      // Horizontal swipe between items
      if (state.locked === "horizontal" && isMultiple) {
        const isSwipe = Math.abs(dx) > 60 || velocity > 0.3
        if (isSwipe) {
          if (dx < 0 && currentIndex < items.length - 1) {
            goTo(currentIndex + 1)
          } else if (dx > 0 && currentIndex > 0) {
            goTo(currentIndex - 1)
          }
        }
        setDragOffset({ x: 0, y: 0 })
        setDismissProgress(0)
        return
      }

      // Vertical swipe → dismiss
      if (state.locked === "vertical") {
        if (Math.abs(dy) > 100) {
          close()
        }
        setDismissProgress(0)
        return
      }

      setDragOffset({ x: 0, y: 0 })
      setDismissProgress(0)
    },
    [
      isZoomed,
      scale,
      isMultiple,
      currentIndex,
      items.length,
      goTo,
      close,
      resetTransform,
    ]
  )

  // Double-tap to zoom
  const lastTap = useRef(0)
  const handleTap = useCallback(
    (e: React.MouseEvent) => {
      const now = Date.now()
      if (now - lastTap.current < 300) {
        // Double-tap
        if (isZoomed) {
          resetTransform()
        } else {
          setScale(2)
          // Center zoom on tap point
          const rect = (
            e.currentTarget as HTMLElement
          ).getBoundingClientRect()
          const cx = e.clientX - rect.left - rect.width / 2
          const cy = e.clientY - rect.top - rect.height / 2
          setTranslate({ x: -cx, y: -cy })
        }
        lastTap.current = 0
      } else {
        lastTap.current = now
      }
    },
    [isZoomed, resetTransform]
  )

  // Compute dismiss opacity
  const dismissOpacity = Math.max(
    0,
    1 - Math.abs(dismissProgress) / 300
  )
  const contentTranslateY = dismissProgress

  return (
    <div
      className={`media-viewer-overlay ${isClosing ? "media-viewer-closing" : ""}`}
      style={{ opacity: dismissProgress !== 0 ? dismissOpacity : undefined }}
      onClick={(e) => {
        // Close when clicking backdrop (not content)
        if (e.target === e.currentTarget) close()
      }}
    >
      {/* Close button */}
      <button
        onClick={close}
        className="absolute top-3 left-3 z-[102] flex items-center justify-center w-9 h-9 rounded-full bg-black/70 text-white hover:bg-black/90 transition-colors backdrop-blur-sm"
        aria-label="Close"
      >
        <X className="h-5 w-5" />
      </button>

      {/* Image counter */}
      {isMultiple && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[102] text-white/80 text-sm font-medium">
          {currentIndex + 1} / {items.length}
        </div>
      )}

      {/* Previous/Next arrows (desktop) */}
      {isMultiple && currentIndex > 0 && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            goTo(currentIndex - 1)
          }}
          className="hidden sm:flex absolute left-2 top-1/2 -translate-y-1/2 z-[102] items-center justify-center w-10 h-10 rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
          aria-label="Previous"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>
      )}
      {isMultiple && currentIndex < items.length - 1 && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            goTo(currentIndex + 1)
          }}
          className="hidden sm:flex absolute right-2 top-1/2 -translate-y-1/2 z-[102] items-center justify-center w-10 h-10 rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
          aria-label="Next"
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      )}

      {/* Media content area */}
      <div
        className="media-viewer-content"
        style={{
          transform: `translateY(${contentTranslateY}px) translateX(${dragOffset.x}px)`,
          transition:
            dragOffset.x === 0 && dismissProgress === 0
              ? "transform 0.3s cubic-bezier(0.2, 0, 0, 1)"
              : "none",
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onClick={handleTap}
      >
        {item.type === "photo" && item.url && (
          <img
            src={proxyUrl(item.url)}
            alt={item.alt_text || "Image"}
            className="media-viewer-image"
            style={{
              transform: `scale(${scale}) translate(${translate.x / scale}px, ${translate.y / scale}px)`,
              transition:
                touchState.current
                  ? "none"
                  : "transform 0.3s cubic-bezier(0.2, 0, 0, 1)",
            }}
            draggable={false}
          />
        )}

        {item.type === "video" && (
          <ViewerVideo
            videoUrl={proxyUrl(item.video_url) || ""}
            posterUrl={proxyUrl(item.preview_image_url || item.url)}
          />
        )}

        {item.type === "animated_gif" && (
          <video
            src={proxyUrl(item.video_url) || ""}
            poster={proxyUrl(item.preview_image_url || item.url)}
            loop
            autoPlay
            muted
            playsInline
            className="media-viewer-image"
            onClick={(e) => e.stopPropagation()}
          />
        )}
      </div>

      {/* Dot indicators for multiple items */}
      {isMultiple && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[102] flex gap-1.5">
          {items.map((_, i) => (
            <button
              key={i}
              onClick={(e) => {
                e.stopPropagation()
                goTo(i)
              }}
              className={`w-1.5 h-1.5 rounded-full transition-all ${
                i === currentIndex
                  ? "bg-white w-2.5"
                  : "bg-white/40 hover:bg-white/60"
              }`}
              aria-label={`Go to image ${i + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  )
}

/** Video player inside the viewer — with play button and native controls */
function ViewerVideo({
  videoUrl,
  posterUrl,
}: {
  videoUrl: string
  posterUrl?: string
}) {
  const [playing, setPlaying] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  if (!playing) {
    return (
      <div
        className="relative flex items-center justify-center w-full h-full cursor-pointer"
        onClick={(e) => {
          e.stopPropagation()
          setPlaying(true)
        }}
      >
        {posterUrl && (
          <img
            src={posterUrl}
            alt="Video poster"
            className="media-viewer-image"
            draggable={false}
          />
        )}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-[#1d9bf0] shadow-lg">
            <Play className="h-8 w-8 text-white fill-white ml-1" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <video
      ref={videoRef}
      src={videoUrl}
      poster={posterUrl}
      controls
      autoPlay
      playsInline
      className="media-viewer-image"
      onClick={(e) => e.stopPropagation()}
    />
  )
}
