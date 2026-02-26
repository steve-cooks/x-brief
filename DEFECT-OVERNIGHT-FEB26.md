# X Brief Overnight Fixes — Feb 26, 2026

## Task 1: Fresher Viral Posts (Backend — Python)

### Problem
Posts going viral 2+ days ago still appear in X Brief. The scraper uses `scan_time` as `created_at` for ALL posts (scan_reader.py line ~280: `created_at=scan_time`), defeating the time decay in scorer.py. The actual post time is in `posted_at` field (relative strings like "57 minutes ago", "2h", "Feb 23") but it's IGNORED.

### Fix
1. **`x_brief/scan_reader.py`** — `parse_scan_post()`:
   - Parse `posted_at` field from scan data into an actual datetime
   - Handle formats: "Xm ago", "Xh ago", "Xd ago", "Feb DD", "YYYY-MM-DD", relative timestamps
   - Use parsed `posted_at` for `created_at` if available, fall back to `scan_time`
   
2. **`x_brief/scorer.py`** — `score_post()`:
   - Make time decay MORE aggressive:
     - 0-6h: 2.0x (keep)
     - 6-12h: 1.5x (keep)
     - 12-24h: 1.0x (keep)
     - 24-36h: 0.5x (was 0.7x)
     - 36-48h: 0.3x (was 0.7x)
     - 48h+: 0.1x (was nothing — posts just stayed at 0.7x forever)
   - Mega-viral posts (>1M views) get a softer decay: halve all penalties

3. **`x_brief/pipeline.py`** — `run_briefing_from_scans()`:
   - Default `hours` from 48 to 36 (tighter window)
   - Pass hours parameter to scan_reader

### Acceptance
- Posts >48h old almost never appear unless mega-viral
- Posts <6h old get strong priority
- `posted_at` parsed correctly for common formats

## Task 2: Read State — Viewed Posts Don't Reappear (Frontend — React)

### Problem
Every time Steve opens X Brief, he sees the same posts again. Unlike X/Twitter where scrolled-past posts don't reappear.

### Fix — `web/src/` changes:
1. **New: `src/lib/read-state.ts`** — localStorage utility:
   - `markPostsAsRead(postIds: string[]): void` — stores IDs with timestamp
   - `getReadPostIds(): Set<string>` — returns all read IDs
   - `clearOldReadState(maxAgeHours: number = 168): void` — cleanup >7 days
   - Key: `x-brief-read-posts` in localStorage

2. **`src/components/briefing-view.tsx`**:
   - On mount: load read state, filter out read posts from each section
   - Show count: "3 new posts" badge per tab
   - On scroll into viewport (IntersectionObserver): mark posts as read
   - "Mark all as read" action (optional button)
   - Persist read state after each marking cycle

3. **`src/app/api/briefing/route.ts`**:
   - Add `postId` to each post in the response (already has it via postUrl)
   - No backend changes needed — read state is purely client-side

### Acceptance
- Open X Brief → see posts → close → reopen → those posts are gone
- New posts from next pipeline run appear fresh
- Read state persists across browser sessions (localStorage)
- Read state auto-cleans after 7 days

## Task 3: Surface Viral Articles (Backend — Python)

### Problem
Steve sees viral articles on his X For You page but X Brief doesn't surface them. The scan data doesn't capture article-type content well, and there's no ARTICLES section.

### Fix
1. **`x_brief/scan_reader.py`**:
   - Detect article posts: posts containing external URLs (not x.com/twitter.com), posts with link_card data
   - Add `is_article: bool` flag to Post model or detect in curation
   
2. **`x_brief/curator.py`**:
   - After VIRAL section, before WORTH A LOOK, add **ARTICLES & THREADS** section
   - Select posts with external URLs (non-twitter), long text (>280 chars = thread indicator), or link cards
   - Max 4 posts, cap 1 per account
   - Minimum engagement: 500 likes or 50K views

3. **`x_brief/models.py`**:
   - Add `link_card` field to Post model if not present
   - Add `is_thread: bool` field

### Acceptance
- Articles with viral engagement appear in a dedicated section
- Long threads appear alongside articles
- Section only shows when there are qualifying posts

## Task 4: Analytics (Frontend — React)

### Problem
No tracking of what Steve views, clicks, or engages with. Can't improve the algorithm without data.

### Fix — `web/src/` changes:
1. **New: `src/lib/analytics.ts`**:
   - Track: page_view, section_view, post_impression, post_click, tab_switch
   - Store in localStorage as JSON array with timestamps
   - `trackEvent(type, metadata): void`
   - `getAnalytics(since?: Date): AnalyticsEvent[]`
   - Export endpoint: `GET /api/analytics` returns JSON dump
   
2. **`src/components/briefing-view.tsx`**:
   - Track tab switches
   - Track post impressions (IntersectionObserver — same as read state)
   
3. **`src/components/x-brief/post-card.tsx`**:
   - Track clicks on post (link to X)
   - Track media opens

### Acceptance
- Analytics accumulate in localStorage
- GET /api/analytics returns structured event data
- No impact on page performance (fire-and-forget tracking)

## Constraints
- Tailwind v4 CSS config (no tailwind.config.ts)
- `cn()`/tailwind-merge eats class overrides — use inline styles when needed
- Build MUST compile clean: `cd web && npx next build`
- Don't break existing functionality
- Don't break the mobile layout (390px viewport)
