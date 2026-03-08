# X Brief v2 — Curation Engine Spec (Implemented)

## Mission

Replace 2 hours of mindless scrolling with ~5 minutes of useful signal.

X Brief is an anti-addiction product, not a feed maximizer.

---

## Pipeline flow

```text
scan ingest → dedup → score → curate 3 tabs → export JSON → frontend
```

- Ingest: `x_brief/scan_reader.py`
- Dedup history + re-emergence: `x_brief/dedup.py`
- Scoring: `x_brief/scorer.py`
- Curation: `x_brief/curator.py`
- Orchestration/export: `x_brief/pipeline.py`

---

## Tabs (current behavior)

## 1) Can't Miss 🔥
Purpose: rare, globally important events.

Selection gates (all required):
1. **Density >= 3**
2. **likes >= 10,000 and views >= 500,000**
3. **(bookmarks + replies) / likes >= 0.05**

Additional constraints:
- max 5 posts
- max 1 post per author
- ranked by `0.7*engagement + 0.3*density`

Empty-state text in UI:
> "Nothing major happened. Go live your life. ✌️"

## 2) For You 📌
Purpose: interest-aligned, high-substance, topic-diverse picks.

- Candidate rules:
  - not already selected in earlier tabs
  - not excluded re-emergent IDs (reserved for Can't Miss)
  - matches configured interests/keywords
- Topic clustering:
  - one winner per cluster
  - winner = highest score in cluster (threads preferred if present)
- Author cap: max 1 per author
- Limit: max 10
- Ranked by `0.4*engagement + 0.6*density`

## 3) Following 👥
Purpose: balanced updates from people user intentionally tracks.

- Candidate rules:
  - not already selected in earlier tabs
  - not excluded re-emergent IDs
  - source is `following` OR username in `tracked_accounts`
  - minimum traction: `likes >= 50 OR views >= 500`
- Topic-clustered (same as For You)
- Limit: max 10
- Ranked by `0.5*engagement + 0.5*density`

Empty-state text in UI:
> "Your follows haven't posted much. That's okay."

---

## Scoring

## Engagement (normalized 0-100 per run)

```text
raw = likes*1.0 + reposts*2.0 + replies*1.5 + bookmarks*3.0 + views*0.01
```

Why:
- bookmarks (3x) = strongest usefulness intent
- reposts/replies carry more signal than likes
- views are weak/passive

Normalized by max raw score in the current candidate batch.

## Information density (0-20)

```text
density = 0
+3 if has link
+5 if article
+4 if thread (2+ connected posts)
+2 if text > 200 chars
+2 if text > 500 chars
+1 if has media
-2 if short hot take (<100 chars, no link, no media)
clamped to [0, 20]
```

---

## Topic clustering

Fast heuristic (no embeddings):

1. Extract tokens per post:
   - normalized URLs
   - @mentions
   - hashtags
   - top 5 non-stopword terms
2. Two posts are same topic if:
   - they share any normalized URL, **or**
   - they share >= 2 tokens
3. Build connected clusters
4. Select one winner per cluster
5. If cluster contains thread posts, prefer highest-scored thread winner

Goal: force breadth and avoid 5 slots on one announcement.

---

## Dedup + re-emergence

- Dedup window is based on pipeline `hours` (default 36/48 depending command)
- Previously briefed posts are filtered within the active window
- Re-emergence rule: if a previously briefed post now has >=10x prior raw engagement **and** meets Can't Miss threshold, it is allowed back (Can't Miss only)

---

## Read-time estimate

UI displays `~X min read` where:
- `X = ceil(total_posts / 2)`
- heuristic: ~30 seconds per post scan

Purpose: reinforce "quick brief then leave" behavior.

---

## Text enrichment

Timeline scans capture truncated post text (X only shows ~280 chars in the feed).
The enrichment step replaces all post text with the full version from the syndication API.

Additionally, scanner-injected alt-text brackets (e.g. `[screenshot shows...]`, `[quoting...]`,
`[Video post - ...]`) are stripped at ingest time in `scan_reader.py`. Only the author's
actual text is stored and displayed.

Trailing `t.co` tracking URLs are also removed during enrichment.

---

## Notes on intentional non-features

- No embeddings/ML infrastructure (speed + simplicity)
- No DB required for core flow (JSON artifacts)
- No cloud dependency required for local run
