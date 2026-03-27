# X Brief Cron Instructions

This file documents what the OpenClaw cron jobs for X Brief should do.
Do NOT edit the actual OpenClaw cron config directly - update this file and let Cluvis apply the changes.

---

## Cron 1: X Timeline Scan (every 4 hours)
**Existing cron ID:** `3c6f01a1-7e41-4089-b11d-bd7508e9f6e6`

### What the cron message should say:

```text
Navigate to x.com/home (For You tab). Hard refresh the page. Wait for feed to load.

Scroll down slowly, collecting post data as you go. Stop when you have collected 10 unique posts. Save the scan to:
  ~/projects/x-brief/timeline_scans/YYYY-MM-DD-HH-foryou.json

Format:
{
  "scan_time": "<ISO8601 UTC>",
  "tab": "foryou",
  "timeline": [
    {
      "id": "<tweet_id>",
      "authorName": "<display name>",
      "authorUsername": "<@handle without @>",
      "text": "<full tweet text>",
      "postUrl": "https://x.com/<handle>/status/<id>",
      "scraped_at": "<ISO8601 UTC>"
    }
    // ... up to 10 posts
  ]
}

Then click the "Following" tab. Scroll and collect 10 unique posts. Save to:
  ~/projects/x-brief/timeline_scans/YYYY-MM-DD-HH-following.json

Same format, with "tab": "following".

Then run the pipeline to ingest and generate TL;DR:
  cd ~/projects/x-brief && python3 -m x_brief.posts_store --ingest timeline_scans/YYYY-MM-DD-HH-foryou.json --tab foryou && python3 -m x_brief.posts_store --ingest timeline_scans/YYYY-MM-DD-HH-following.json --tab following && python3 -m x_brief.tldr

NEVER: like, retweet, reply, follow, bookmark, or click on post content. Only navigate, scroll, and switch tabs.
```

---

## Cron 2: Midnight Reset (new - runs at midnight CT)
**Schedule:** 0 0 * * * (midnight, America/Chicago)

### What the cron message should say:

```text
Clear X Brief posts for the day reset:
  cd ~/projects/x-brief && python3 -m x_brief.posts_store --clear && python3 -m x_brief.tldr

This gives a fresh slate for the new day.
```

---

## Notes

- The scan files YYYY-MM-DD-HH should use the actual date/hour at scan time
- `python3 -m x_brief.tldr` regenerates `data/latest-briefing.json` from current unseen posts
- `python3 -m x_brief.posts_store --clear` resets `data/posts.json` to `[]`
