# DEFECT: Mobile Right-Side Clipping on Post Cards

## Bug
On iPhone Safari (390px viewport), ALL post cards clip content on the right side. 
Text gets cut off mid-word, metrics row bookmark count truncated, images push too wide.

## Screenshot
See `MOBILE_CLIPPING_BUG.jpg` in this directory — Steve's actual iPhone screenshot.
Notice:
- "People giving OpenClaw root access to their entir" — text clipped
- "We've identified industrial-scale distillation attac" — clipped
- "24,000 fraudul" — clipped  
- Bookmark counts "15." and "11." — clipped
- This happens on EVERY post, not just some

## Where It Lives
- Project: `~/projects/x-brief/web` (Next.js)
- Main component: `web/src/components/x-brief/post-card.tsx` — PostCard
- Page component: `web/src/components/briefing-view.tsx` — tabs + post wrappers
- Tabs UI component: `web/src/components/ui/tabs.tsx` — shadcn/Radix tabs
- CSS: `web/src/app/globals.css`

## The Viral Tab Is The Worst
The Viral tab stress-tests PostCard with:
- Images/memes (full-width)
- Quoted tweets (nested cards)
- Link preview cards
- Multi-media grids
- Long engagement stats rows (5-6 metrics with SVG icons)

## Root Cause Analysis (What I Found)
The content area renders at **413px on a 390px viewport** — 23px wider than the screen.

The overflow chain:
1. `Tabs` (shadcn/Radix) creates `flex gap-2 flex-col` — children can grow wider than parent
2. `TabsContent` (`flex-1`) doesn't constrain width in flex-col
3. Content div `max-w-[598px]` doesn't cap below 598px
4. Post wrapper `px-4` gives 16px padding each side = 32px
5. Article `flex gap-3` = avatar(40px) + gap(12px) + content  
6. Content column grows to 329px (should be ~306px)
7. Total: 329 + 12 + 40 + 32 = 413px > 390px viewport

## What Was Tried (and didn't fully work)
- `overflow-hidden` on Tabs component — Tailwind class gets stripped by `cn()`/tailwind-merge
- `style={{overflow:'hidden'}}` on Tabs — Radix doesn't forward style prop to DOM
- CSS `!important` outside @layer for `[data-slot="tabs"]` — didn't apply
- `w-0 flex-1 overflow-hidden` on content column — helped but didn't fix root cause
- `style={{maxWidth:'min(598px,100%)'}}` on content div — verified 0 overflows on injected test HTML but real React components still clip

## What X.com Does (reference)
X.com mobile at 390px:
- 16px horizontal padding
- 40px avatar  
- 12px gap
- ~306px content column
- Content NEVER exceeds viewport — they likely use absolute width constraints, not just flex

## How To Verify
1. Run dev server: `cd web && npx next dev --port 3000`
2. Open Chrome DevTools → toggle device toolbar → iPhone 14 Pro (390px)
3. Navigate to localhost:3000, click Viral tab
4. Every post should have text fully visible to the right edge

## Acceptance Criteria
- Zero horizontal overflow at 390px viewport width
- All text, metrics, images, quoted posts contained within viewport
- Works across ALL tabs, not just Viral
- Don't break desktop layout (598px max content width on larger screens)
- Run the build (`npx next build`) — must compile clean
