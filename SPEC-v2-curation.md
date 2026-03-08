# X Brief v2 — Curation Engine Spec

## Mission
Replace 2 hours of mindless scrolling with 5 minutes of curated signal.
X Brief is an anti-addiction tool that delivers the gems so you don't have to scroll.

---

## Tabs (3 + empty states)

### 1. Can't Miss 🔥 (3-5 posts max)
**Purpose:** Things you absolutely need to know about. Major events only.
**Criteria:**
- Extreme virality: top 0.1% engagement relative to what we see (views > 500K AND likes > 10K)
- OR: from a major account (>1M followers) with abnormally high engagement for THEM
- Any niche — this is global importance
- Any post type (tweet, thread, article, video)
- **If nothing qualifies, the tab shows "Nothing major happened. Go live your life. ✌️"**
- Empty is a feature, not a bug

### 2. For You 📌 (max 10, topic-diverse)
**Purpose:** Best posts from your For You page, one per topic.
**Criteria:**
- Source: `for_you` or either (not restricted)
- Must match user's interests/niches (semantic or keyword)
- **Topic clustering:** Group similar posts → pick the BEST from each cluster
  - Similarity = same subject (e.g., 5 posts about "GPT-5.4 launch" = 1 cluster)
  - Implementation: simple keyword overlap + author dedup. NOT full embeddings (keep it fast)
  - Pick the post with highest information density score from each cluster
- **Information density scoring:**
  - Has external link: +3 points
  - Is article (`/article/` URL): +5 points
  - Is thread (2+ posts): +4 points
  - Post length > 200 chars: +2 points
  - Has media (image/video): +1 point
  - Pure hot take (< 100 chars, no links, no media): -2 points
  - These bonuses ADD to the base engagement score
- Max 1 post per author
- Ranked by: (engagement_score × 0.4) + (information_density × 0.6)

### 3. Following 👥 (max 10)
**Purpose:** Best posts from people you actually follow.
**Criteria:**
- Source: `following` only (fallback: author in `tracked_accounts`)
- Lower engagement threshold than other tabs (these are YOUR people)
  - Minimum: 50 likes OR 500 views (just needs SOME traction)
- Same topic clustering as For You — one post per topic
- Same information density scoring
- Ranked by: (engagement_score × 0.5) + (information_density × 0.5)
  - Balanced — you care about what these people say even if it's not optimized for engagement

---

## Scoring Overhaul

### Base Engagement Score (0-100 scale, normalized)
```
raw = (likes × 1.0) + (reposts × 2.0) + (replies × 1.5) + (bookmarks × 3.0) + (views × 0.01)
```
- Bookmarks weighted 3x — bookmarks = "this is actually useful" (strongest signal)
- Replies weighted 1.5x — discussion = substance
- Reposts weighted 2x — people sharing = endorsement
- Views weighted low — views are cheap, passive

Normalize to 0-100 based on max score in current batch.

### Information Density Score (0-20 scale)
```
density = 0
if has_external_link: density += 3
if is_article: density += 5
if is_thread: density += 4
if len(text) > 200: density += 2
if len(text) > 500: density += 2  (additional)
if has_media: density += 1
if len(text) < 100 and not has_link and not has_media: density -= 2  (hot take penalty)
```

### Final Score per tab
- Can't Miss: pure engagement (must cross extreme threshold)
- For You: `engagement × 0.4 + density × 0.6` (favors substance)
- Following: `engagement × 0.5 + density × 0.5` (balanced)

---

## Topic Clustering (simple, fast)

Not ML-based. Simple heuristic:
1. Extract "topic tokens" from each post: URLs, @mentions, hashtags, and top 5 non-stopword terms
2. Two posts are "same topic" if they share ≥2 topic tokens OR link to the same URL
3. Group into clusters
4. From each cluster, pick the post with highest final score
5. If a cluster has a thread AND a standalone post about the same thing, prefer the thread

---

## Empty Tab Messaging

Each tab can be empty. Show encouraging messages:
- **Can't Miss:** "Nothing major happened. Go live your life. ✌️"
- **For You:** "Your timeline is quiet. Check back later."
- **Following:** "Your follows haven't posted much. That's okay."

---

## Read Time Estimate

Show at the top of the briefing: "~X min read"
- Estimate: 30 seconds per post (scanning, not reading every word)
- 15 posts = "~8 min read", 5 posts = "~3 min read"
- Reinforces the message: this is QUICK, then you're done

---

## Post-Dedup Behavior

- Dedup window stays at 48h
- Posts that were in a previous briefing don't reappear
- BUT: if a post's engagement jumps 10x since last briefed, it can reappear in Can't Miss
  - Handles "this blew up overnight" scenarios

---

## What does NOT change
- Scan process (Rabbit scrapes For You + Following)
- Enrichment (syndication API for avatars/media)
- Frontend rendering (post cards, media, threads)
- Pipeline flow (scan → score → curate → enrich → export)
- No API keys, no database, no cloud

---

## Implementation Order
1. New scorer (engagement + density scoring)
2. Topic clustering in curator
3. New 3-tab curation with thresholds
4. Empty tab messaging in frontend
5. Read time estimate in frontend
6. Update tab labels (Viral→Can't Miss, Top Picks→For You)
7. Update tests
