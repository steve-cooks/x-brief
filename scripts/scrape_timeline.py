#!/usr/bin/env python3
"""
scrape_timeline.py - CDP-based X timeline scraper
Usage: python3 scrape_timeline.py --tab foryou --output ~/projects/x-brief/timeline_scans/YYYY-MM-DD-HH-foryou.json
"""
import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CDP_URL = "http://127.0.0.1:18800"


def get_cdp_target():
    """Get the first available CDP target (tab)"""
    with urllib.request.urlopen(f"{CDP_URL}/json") as r:
        tabs = json.loads(r.read())
    # Find x.com tab or first page tab
    for tab in tabs:
        if 'x.com' in tab.get('url', '') and tab.get('type') == 'page':
            return tab
    for tab in tabs:
        if tab.get('type') == 'page':
            return tab
    raise RuntimeError("No CDP page tab found")


def cdp_eval(ws_url, js_code):
    """Execute JS via CDP WebSocket and return result"""
    import websocket  # pip install websocket-client

    ws = websocket.create_connection(ws_url, timeout=30)
    msg_id = 1

    ws.send(json.dumps({
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": js_code,
            "returnByValue": True,
            "awaitPromise": True,
            "timeout": 20000
        }
    }))

    while True:
        result = json.loads(ws.recv())
        if result.get("id") == msg_id:
            break

    ws.close()

    if "error" in result:
        raise RuntimeError(f"CDP error: {result['error']}")

    val = result.get("result", {}).get("result", {})
    if val.get("type") == "string":
        return val["value"]
    return val.get("value")


def wait_for_posts(ws_url, max_wait=15):
    """Wait until article elements appear on the page"""
    check_js = 'document.querySelectorAll(\'article[data-testid="tweet"]\').length'
    for i in range(max_wait):
        try:
            count = cdp_eval(ws_url, check_js)
            if count and int(count) > 0:
                print(f"Found {count} articles after {i+1}s")
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def navigate_to_tab(ws_url, tab_name):
    """Navigate to x.com/home and switch to the correct tab"""
    import websocket

    ws = websocket.create_connection(ws_url, timeout=30)

    def send_cmd(method, params, cmd_id):
        ws.send(json.dumps({"id": cmd_id, "method": method, "params": params}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == cmd_id:
                return msg

    print("Navigating to x.com/home...")
    send_cmd("Page.navigate", {"url": "https://x.com/home"}, 2)
    ws.close()

    # Wait for page load
    time.sleep(4)

    # Click the right tab
    if tab_name == "foryou":
        click_js = """
        const tabs = document.querySelectorAll('[role="tab"]');
        for (const t of tabs) {
            if (t.textContent.toLowerCase().includes('for you')) { t.click(); break; }
        }
        'done';
        """
    else:
        click_js = """
        const tabs = document.querySelectorAll('[role="tab"]');
        for (const t of tabs) {
            if (t.textContent.toLowerCase().includes('following')) { t.click(); break; }
        }
        'done';
        """

    cdp_eval(ws_url, click_js)
    time.sleep(3)
    print(f"Switched to {tab_name} tab")


EXTRACT_JS = """
(async () => {
  const articles = document.querySelectorAll('article[data-testid="tweet"]');
  const posts = [];

  for (const article of articles) {
    try {
      // Tweet URL and ID
      const timeLink = article.querySelector('a[href*="/status/"]');
      const url = timeLink ? 'https://x.com' + timeLink.getAttribute('href').split('?')[0] : '';
      const id = url.match(/\\/status\\/(\\d+)/)?.[1] || '';

      // Author info
      const userNameEl = article.querySelector('[data-testid="User-Name"]');
      const authorName = userNameEl?.querySelector('span')?.innerText || '';
      const handleEl = userNameEl?.querySelectorAll('span')[1];
      const authorUsername = (handleEl?.innerText || '').replace('@','');

      // Avatar
      const avatarImg = article.querySelector('[data-testid="Tweet-User-Avatar"] img');
      const avatar_url = avatarImg?.src || '';

      // Verified
      const isVerified = !!article.querySelector('[data-testid="icon-verified"]') ||
                         !!article.querySelector('svg[aria-label="Verified account"]');

      // Full text - click Show more if present
      const showMore = article.querySelector('[data-testid="tweet-text-show-more-link"]');
      if (showMore) showMore.click();
      await new Promise(r => setTimeout(r, 300));
      const textEl = article.querySelector('[data-testid="tweetText"]');
      const text = textEl?.innerText || '';

      // Metrics
      const getMetric = (testid) => {
        const el = article.querySelector('[data-testid="' + testid + '"]');
        if (!el) return 0;
        const span = el.querySelector('span[data-testid]') || el.querySelector('span');
        const txt = span?.innerText?.replace(/[^0-9.KMkm]/g, '') || '0';
        if (txt.endsWith('K') || txt.endsWith('k')) return Math.round(parseFloat(txt) * 1000);
        if (txt.endsWith('M') || txt.endsWith('m')) return Math.round(parseFloat(txt) * 1000000);
        return parseInt(txt) || 0;
      };

      const likes = getMetric('like');
      const retweets = getMetric('retweet');
      const replies = getMetric('reply');

      // Views
      const viewsEl = article.querySelector('[aria-label*="view"]');
      const viewsMatch = viewsEl?.getAttribute('aria-label')?.match(/[\\d,]+/)?.[0]?.replace(/,/g,'');
      const views = parseInt(viewsMatch || '0');

      // Bookmarks
      const bookmarksEl = article.querySelector('[data-testid="bookmark"]');
      const bookmarkSpan = bookmarksEl?.querySelector('span');
      const bookmarks = parseInt(bookmarkSpan?.innerText?.replace(/[^0-9]/g,'') || '0');

      // Media
      const media = [];
      const photos = article.querySelectorAll('[data-testid="tweetPhoto"] img');
      for (const img of photos) {
        if (img.src && img.src.includes('pbs.twimg.com')) {
          media.push({ type: 'photo', url: img.src.split('?')[0] + '?format=jpg&name=large', preview_image_url: img.src });
        }
      }
      const videos = article.querySelectorAll('video');
      for (const vid of videos) {
        const poster = vid.poster || '';
        const src = vid.src || '';
        media.push({ type: 'video', url: src, preview_image_url: poster, video_url: src });
      }

      // Link card
      let linkCard = null;
      const cardEl = article.querySelector('[data-testid="card.wrapper"]');
      if (cardEl) {
        const cardTitle = cardEl.querySelector('[data-testid="card.layoutLarge.title"]')?.innerText ||
                          cardEl.querySelector('[data-testid="card.layoutSmall.title"]')?.innerText || '';
        const cardDesc = cardEl.querySelector('[data-testid="card.layoutLarge.detail"]')?.innerText || '';
        const cardImg = cardEl.querySelector('img')?.src || '';
        const cardLink = cardEl.querySelector('a')?.href || '';
        let domain = '';
        try { domain = cardLink ? new URL(cardLink).hostname : ''; } catch(e) {}
        if (cardTitle || cardLink) {
          linkCard = { title: cardTitle, description: cardDesc, thumbnail: cardImg, domain, url: cardLink };
        }
      }

      // Quoted post
      let quotedPost = null;
      const quotedEl = article.querySelector('[data-testid="tweet"] [data-testid="tweet"]');
      if (quotedEl && quotedEl !== article) {
        const qText = quotedEl.querySelector('[data-testid="tweetText"]')?.innerText || '';
        const qHandle = quotedEl.querySelector('[data-testid="User-Name"]')?.querySelectorAll('span')?.[1]?.innerText?.replace('@','') || '';
        const qName = quotedEl.querySelector('[data-testid="User-Name"] span')?.innerText || '';
        quotedPost = { authorName: qName, authorUsername: qHandle, text: qText };
      }

      if (id && text) {
        posts.push({
          id, authorName, authorUsername, avatar_url, is_verified: isVerified,
          text, url, media,
          metrics: { likes, retweets, replies, bookmarks, views },
          quotedPost, linkCard, thread_posts: [],
          is_article: !!linkCard,
          article_url: linkCard?.url || null
        });
      }
    } catch(e) {}
  }

  return JSON.stringify(posts);
})()
"""


def main():
    parser = argparse.ArgumentParser(description='CDP-based X timeline scraper')
    parser.add_argument('--tab', choices=['foryou', 'following'], default='foryou')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    parser.add_argument('--navigate', action='store_true', help='Force navigate to x.com/home first')
    args = parser.parse_args()

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to CDP at {CDP_URL}...")
    try:
        target = get_cdp_target()
    except Exception as e:
        print(f"ERROR: Could not connect to CDP: {e}")
        print("Make sure Chrome/Chromium is running with --remote-debugging-port=18800")
        sys.exit(1)

    ws_url = target['webSocketDebuggerUrl']
    current_url = target.get('url', '')
    print(f"CDP target: {current_url}")

    # Navigate if not on x.com or if explicitly requested
    if args.navigate or 'x.com' not in current_url:
        navigate_to_tab(ws_url, args.tab)
        # Re-get target after navigation
        try:
            target = get_cdp_target()
            ws_url = target['webSocketDebuggerUrl']
        except Exception:
            pass
    else:
        print(f"Already on x.com, switching to {args.tab} tab...")
        if args.tab == "foryou":
            click_js = """
            const tabs = document.querySelectorAll('[role="tab"]');
            for (const t of tabs) {
                if (t.textContent.toLowerCase().includes('for you')) { t.click(); break; }
            }
            'done';
            """
        else:
            click_js = """
            const tabs = document.querySelectorAll('[role="tab"]');
            for (const t of tabs) {
                if (t.textContent.toLowerCase().includes('following')) { t.click(); break; }
            }
            'done';
            """
        cdp_eval(ws_url, click_js)
        time.sleep(3)

    # Wait for posts to load
    print("Waiting for posts to load...")
    if not wait_for_posts(ws_url):
        print("WARNING: No posts found after waiting. Proceeding anyway.")

    # Extract posts via CDP
    print("Extracting posts via CDP JS injection...")
    raw = cdp_eval(ws_url, EXTRACT_JS)

    if not raw:
        print("ERROR: No data returned from JS extraction")
        sys.exit(1)

    posts = json.loads(raw)
    print(f"Extracted {len(posts)} posts")

    # Save output
    scan_time = datetime.now(timezone.utc).isoformat()
    output_data = {
        "posts": posts,
        "scan_time": scan_time,
        "tab": args.tab
    }

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"Saved to {output_path}")
    print(f"Posts found: {len(posts)}")
    if posts:
        p = posts[0]
        print(f"Sample - author: @{p.get('authorUsername')}, avatar: {'yes' if p.get('avatar_url') else 'MISSING'}, text_len: {len(p.get('text', ''))}, media: {len(p.get('media', []))}")


if __name__ == '__main__':
    main()
