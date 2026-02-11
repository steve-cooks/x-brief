# X-Style Video Player Component — Design Spec

## Overview
Build a custom video player React component for the Cluvis Design System that looks and feels exactly like X (Twitter)'s video player. Replace the vanilla HTML5 `<video>` tag currently used in X Brief.

## X Video Player — Features & Behavior

### Layout
- Video fills the container with `object-fit: cover` (no letterboxing for feed)
- Rounded corners (16px on X, matching our card radius)
- 16:9 aspect ratio container by default, adapts to video's natural ratio
- Dark overlay gradient at bottom for controls visibility

### Controls (appear on hover/tap, auto-hide after 3s)
- **Play/Pause button** — centered large play icon when paused, bottom-left small icon when playing
- **Progress bar** — thin line at bottom, expands on hover. Shows buffered range. Draggable scrubber thumb
- **Time display** — current time / duration (e.g., "0:23 / 1:45") left-aligned near progress bar
- **Volume** — mute/unmute toggle icon + volume slider on hover (desktop only)
- **Fullscreen** — expand icon bottom-right
- **Settings gear** — playback speed options (0.5x, 1x, 1.5x, 2x) — optional for v1

### Behavior
- **Auto-play muted in feed** — starts playing when visible (Intersection Observer), muted by default
- **Tap to unmute** — first tap unmutes, shows volume indicator
- **Click to play/pause** — clicking video area toggles play/pause
- **Double-click to fullscreen** — standard behavior
- **Progress bar hover preview** — shows time tooltip at cursor position
- **Mobile**: controls appear on tap, hide after 3s, no volume slider (uses device volume)
- **Smooth transitions** — controls fade in/out with opacity animation (200ms)

### GIF Mode
- No controls visible
- Auto-play, loop, muted
- "GIF" badge bottom-left
- No progress bar, no time, no volume

### Visual Design
- Controls background: linear gradient from transparent to rgba(0,0,0,0.6) at bottom
- Icon color: white with slight drop shadow for readability
- Progress bar: gray track, white played, lighter white buffered
- Scrubber: white circle, 12px, appears on hover
- Font: system font, 13px for time display
- Animations: all transitions 200ms ease

### Props Interface
```typescript
interface VideoPlayerProps {
  src: string                    // Video source URL
  poster?: string               // Poster/thumbnail image URL
  type?: 'video' | 'gif'       // Player mode (default: 'video')
  autoPlay?: boolean            // Auto-play when visible (default: true)
  muted?: boolean               // Start muted (default: true in feed)
  loop?: boolean                // Loop playback (default: false, true for gif)
  aspectRatio?: string          // CSS aspect-ratio (default: '16/9')
  className?: string            // Additional CSS classes
  onPlay?: () => void
  onPause?: () => void
  onEnded?: () => void
  onTimeUpdate?: (time: number) => void
}
```

### Implementation Notes
- Use `useRef` for video element access
- `IntersectionObserver` for auto-play/pause on scroll visibility
- Custom controls overlay (NOT native browser controls)
- `requestAnimationFrame` for smooth progress bar updates
- All icons from lucide-react (Play, Pause, Volume2, VolumeX, Maximize, Settings)
- Must work with our `/api/media` proxy URLs
- Must be fully responsive (mobile-first)
- No external dependencies beyond React + lucide-react + tailwind

### File Structure
- `components/ui/video-player.tsx` — the component
- Styled with Tailwind classes (no separate CSS file)
- Export from design system for reuse
