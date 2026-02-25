# Bug: Tab Navigation Bar Position Broken

## Screenshot
See `TAB_NAV_BROKEN.jpg` in project root — Steve's iPhone showing a gap between the header and tab bar. The tabs should stick directly below the header when scrolling.

## Root Cause
The `<div className="w-full overflow-hidden">` wrapper added in commit `7963fca` to fix mobile content clipping is BREAKING `position: sticky` on the tab navigation bar.

**CSS rule:** `overflow: hidden` (or `overflow: auto/scroll`) on an ancestor creates a new scroll container. `position: sticky` only works within its nearest scrolling ancestor. When that ancestor has `overflow: hidden`, the sticky element has nowhere to stick — it scrolls away with its container.

## The Fix
Replace `overflow-hidden` with `overflow-x-clip` (or `overflow: clip` in CSS) on the wrapper. `overflow: clip` clips content the same way but does NOT create a scroll container, so `position: sticky` still works.

Alternatively, remove the wrapper div entirely and move the overflow containment to BELOW the sticky tab bar — i.e. only on the tab content area, not wrapping the whole Tabs component.

## Files to check
- `web/src/components/briefing-view.tsx` — line ~262, the `<div className="w-full overflow-hidden">` wrapper
- The sticky tab bar is at line ~271: `<div className="sticky top-[53px] z-40 ...">` 

## Acceptance Criteria
1. Tab navigation sticks directly below the header when scrolling (no gap)
2. Content still doesn't clip/overflow at 390px viewport width
3. Build compiles clean
4. Desktop (598px max) layout still works

## Key constraint
BOTH fixes must coexist: no clipping AND working sticky tabs.
