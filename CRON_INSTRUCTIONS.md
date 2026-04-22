# X Brief Cron Instructions

This file documents what the OpenClaw cron jobs for X Brief should do.
Do NOT edit the actual OpenClaw cron config directly - update this file and let Cluvis apply the changes.

---

## Cron 1: X Timeline Scan (every 4 hours)
**Cron ID:** `3c6f01a1-7e41-4089-b11d-bd7508e9f6e6`
**Agent:** rabbit
**Schedule:** `0 */4 * * *` (America/Chicago, ±5 min stagger)
**Session:** isolated

### What the cron message says:

```text
Open a FRESH tab using `browser action=open url=https://x.com/home profile=openclaw` and capture the targetId. Wait 5 seconds for posts to load.

⚠️ READ-ONLY. NEVER like, retweet, reply, follow, bookmark, or click on any post content. Only navigate, scroll, switch tabs, and expand truncated text.

**Step 1 — For You tab (10 posts):**

You should be on the For You tab by default. Scroll slowly. For each post collect ALL of these fields:
- id: tweet ID from URL (number after /status/)
- authorName: display name
- authorUsername: handle without @
- avatar_url: profile picture src URL (the img tag inside the avatar circle)
- is_verified: true if blue or gold checkmark visible
- text: FULL tweet text. If you see a "Show more" link at the bottom of the tweet text, click it to expand BEFORE reading the text. Always get the complete text.
- url: full https://x.com/handle/status/id URL
- tab: "foryou"
- metrics: { likes, retweets, replies, bookmarks, views } as integers
- media: collect carefully per type:
  - Photos: { type: "photo", url: "https://pbs.twimg.com/media/..." } — must be a pbs.twimg.com CDN URL, NOT x.com/photo/1
  - Videos: { type: "video", preview_image_url: "https://pbs.twimg.com/amplify_video_thumb/VIDEOID/..." } — the thumbnail URL MUST contain the same numeric VIDEOID as the video itself. Do NOT mix thumbnails from one post with video from another post. If you cannot confirm the thumbnail belongs to this specific video, use empty string for preview_image_url.
  - Empty array if no media or if only x.com/photo redirect URLs are available
- is_article: true if there is a link preview card
- article_url: the linked URL if is_article is true
- quotedPost: if this post quotes another tweet, collect the quoted tweet as an object with these fields: { authorName, authorUsername, text, postUrl, media: [] }. The quoted tweet appears as an embedded card with a border inside the post. If there is no quoted tweet, set to null.

After collecting 10 posts, save to:
~/projects/x-brief/timeline_scans/YYYY-MM-DD-HH-foryou.json
Format: {"scan_time": "<ISO8601 UTC>", "tab": "foryou", "posts": [...]}

**Step 2 — Following tab (10 posts):**

⚠️ IMPORTANT: You must actually click the "Following" tab button at the top of the feed. It is right next to the "For You" tab. After clicking it, wait 4 seconds for the feed to refresh. The posts should be DIFFERENT from the For You posts. If you see the same posts, you did not switch tabs — try clicking Following again.

Collect 10 posts using the same fields. Set tab: "following" for all.

Save to: ~/projects/x-brief/timeline_scans/YYYY-MM-DD-HH-following.json

**Step 3 — Ingest:**
```
TIMESTAMP=$(date +%Y-%m-%d-%H)
cd ~/projects/x-brief
python3 -m x_brief.posts_store --ingest timeline_scans/${TIMESTAMP}-foryou.json --tab foryou
python3 -m x_brief.posts_store --ingest timeline_scans/${TIMESTAMP}-following.json --tab following
python3 ~/projects/x-brief/scripts/enrich_videos.py
python3 -m x_brief.tldr
```

**Step 4 — CLOSE CHROME (mandatory cleanup):**
First close the X.com tab: `browser action=close targetId=<the targetId from Step 1>`.

Then stop the entire Chrome instance for the openclaw profile:
`browser action=stop profile=openclaw`

This ensures no zombie Chrome process is left behind regardless of whether Chrome was already running before this job started.

If `browser action=stop` fails, fall back to: `pkill -f "remote-debugging-port=18800" 2>/dev/null || true`

Report: posts collected per tab, confirm Following posts are different from For You posts, and confirm Chrome was stopped.
```

---

## Cron 2: Midnight Reset
**Cron ID:** `0cfc1aca-0f25-4fc6-9a2d-2cec9983e668`
**Agent:** main
**Schedule:** `0 0 * * *` (midnight, America/Chicago)
**Session:** isolated

### What the cron message says:

```text
Clear X Brief posts for the daily reset: cd ~/projects/x-brief && python3 -m x_brief.posts_store --clear && python3 -m x_brief.tldr
```

---

## Notes

- `YYYY-MM-DD-HH` in filenames uses the actual date/hour at scan time
- JSON top-level key for posts array is `"posts"` (not `"timeline"`)
- `python3 -m x_brief.tldr` regenerates `data/latest-briefing.json` from current unseen posts
- `python3 -m x_brief.posts_store --clear` resets `data/posts.json` to `[]`
- `enrich_videos.py` runs after ingest to resolve video metadata
- Chrome must be explicitly stopped after each scan (Step 4) to prevent zombie processes
