#!/usr/bin/env python3
"""
scrape_timeline.py - Playwright-based X timeline scraper
Extracts rich post data: avatars, full text, media URLs, metrics, link cards, quoted posts.

Usage:
  python3 scrape_timeline.py --tab foryou --output ~/projects/x-brief/timeline_scans/2026-03-27-14-foryou.json
  python3 scrape_timeline.py --tab following --output ~/projects/x-brief/timeline_scans/2026-03-27-14-following.json
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

COOKIES_DB = Path("/home/cluvis/.config/chrome-cdp/Default/Cookies")
PROFILE_DIR = Path("/home/cluvis/.config/chrome-cdp")


def load_x_cookies():
    """Load X.com session cookies from Chrome's SQLite cookie store."""
    import sqlite3
    conn = sqlite3.connect(str(COOKIES_DB))
    cur = conn.cursor()
    cur.execute("""
        SELECT name, value, host_key, path, is_secure, is_httponly, expires_utc
        FROM cookies
        WHERE host_key LIKE '%.x.com%' OR host_key LIKE '%.twitter.com%'
    """)
    cookies = []
    for name, value, host_key, path, secure, httponly, expires_utc in cur.fetchall():
        domain = host_key if host_key.startswith('.') else '.' + host_key
        # Convert Chrome epoch to Unix timestamp
        expires = (expires_utc - 11644473600000000) / 1000000 if expires_utc else None
        cookies.append({
            "name": name,
            "value": value,
            "domain": domain,
            "path": path,
            "secure": bool(secure),
            "httpOnly": bool(httponly),
            "expires": expires,
            "sameSite": "None"
        })
    conn.close()
    return cookies


def scrape_posts(page, tab_name, target_count=10):
    """Extract posts from the current X timeline tab."""
    
    # JS to extract all posts from current page
    extract_js = """
    () => {
      const articles = Array.from(document.querySelectorAll('article[data-testid="tweet"]'));
      const posts = [];
      
      for (const article of articles) {
        try {
          // URL and ID
          const timeLink = article.querySelector('a[href*="/status/"]');
          const href = timeLink ? timeLink.getAttribute('href') : '';
          const url = href ? 'https://x.com' + href.split('?')[0] : '';
          const idMatch = url.match(/\\/status\\/(\\d+)/);
          const id = idMatch ? idMatch[1] : '';
          if (!id) continue;
          
          // Author
          const userNameEl = article.querySelector('[data-testid="User-Name"]');
          const spans = userNameEl ? userNameEl.querySelectorAll('span') : [];
          const authorName = spans[0] ? spans[0].innerText.trim() : '';
          const authorUsername = spans.length > 1 ? spans[spans.length-1].innerText.replace('@','').trim() : '';
          
          // Avatar
          const avatarImg = article.querySelector('[data-testid="Tweet-User-Avatar"] img, [data-testid="UserAvatar-Container-"] img');
          const avatar_url = avatarImg ? avatarImg.src : '';
          
          // Verified
          const is_verified = !!article.querySelector('[data-testid="icon-verified"], svg[aria-label*="Verified"], svg[aria-label*="verified"]');
          
          // Full text
          const textEl = article.querySelector('[data-testid="tweetText"]');
          const text = textEl ? textEl.innerText.trim() : '';
          
          // Parse metric number
          function parseNum(str) {
            if (!str) return 0;
            const s = str.replace(/,/g,'').trim();
            if (s.endsWith('K') || s.endsWith('k')) return Math.round(parseFloat(s)*1000);
            if (s.endsWith('M') || s.endsWith('m')) return Math.round(parseFloat(s)*1000000);
            return parseInt(s) || 0;
          }
          
          // Metrics via aria-labels (most reliable)
          function getMetricFromAria(testid) {
            const el = article.querySelector('[data-testid="' + testid + '"]');
            if (!el) return 0;
            const aria = el.closest('[role="button"]')?.getAttribute('aria-label') || el.getAttribute('aria-label') || '';
            const m = aria.match(/([\\d,.]+\\s*[KkMm]?)/);
            if (m) return parseNum(m[1]);
            // fallback to innerText
            const span = el.querySelector('span[data-testid], span');
            return parseNum(span?.innerText || '0');
          }
          
          const likes = getMetricFromAria('like');
          const retweets = getMetricFromAria('retweet');
          const replies = getMetricFromAria('reply');
          const bookmarks = getMetricFromAria('bookmark');
          
          // Views via aria-label on analytics link
          let views = 0;
          const analyticsEls = article.querySelectorAll('a[href*="/analytics"], [aria-label*="View"]');
          for (const el of analyticsEls) {
            const aria = el.getAttribute('aria-label') || '';
            const m = aria.match(/([\\d,.]+\\s*[KkMm]?)\\s*[Vv]iew/);
            if (m) { views = parseNum(m[1]); break; }
          }
          
          // Media
          const media = [];
          const photos = article.querySelectorAll('[data-testid="tweetPhoto"] img, [data-testid="tweet-image-container"] img');
          for (const img of photos) {
            const src = img.src || '';
            if (src && src.includes('pbs.twimg.com')) {
              const cleanUrl = src.split('?')[0] + '?format=jpg&name=large';
              media.push({ type: 'photo', url: cleanUrl, preview_image_url: src });
            }
          }
          const videos = article.querySelectorAll('video');
          for (const vid of videos) {
            const poster = vid.poster || '';
            const src = vid.currentSrc || vid.src || '';
            media.push({ type: 'video', url: src, preview_image_url: poster, video_url: src });
          }
          
          // Link card
          let linkCard = null;
          const cardEl = article.querySelector('[data-testid="card.wrapper"]');
          if (cardEl) {
            const title = cardEl.querySelector('[data-testid*="title"]')?.innerText || '';
            const desc = cardEl.querySelector('[data-testid*="detail"], [data-testid*="description"]')?.innerText || '';
            const thumb = cardEl.querySelector('img')?.src || '';
            const linkEl = cardEl.querySelector('a[href]');
            const cardUrl = linkEl?.href || '';
            let domain = '';
            try { domain = new URL(cardUrl).hostname; } catch {}
            if (title || cardUrl) {
              linkCard = { title, description: desc, thumbnail: thumb, domain, url: cardUrl };
            }
          }
          
          // Quoted post (nested tweet)
          let quotedPost = null;
          const nested = article.querySelector('[data-testid="tweet"] [data-testid="tweetText"]');
          if (nested && nested !== textEl) {
            const qArticle = nested.closest('article') || nested.closest('[data-testid="tweet"]');
            if (qArticle && qArticle !== article) {
              const qUserEl = qArticle.querySelector('[data-testid="User-Name"]');
              const qSpans = qUserEl ? qUserEl.querySelectorAll('span') : [];
              quotedPost = {
                authorName: qSpans[0]?.innerText.trim() || '',
                authorUsername: qSpans.length > 1 ? qSpans[qSpans.length-1].innerText.replace('@','').trim() : '',
                text: nested.innerText.trim(),
                url: ''
              };
            }
          }
          
          if (text) {
            posts.push({
              id, authorName, authorUsername, avatar_url, is_verified,
              text, url,
              metrics: { likes, retweets, replies, bookmarks, views },
              media, linkCard, quotedPost,
              thread_posts: [],
              is_article: !!linkCard,
              article_url: linkCard ? linkCard.url : null
            });
          }
        } catch(e) {}
      }
      
      return JSON.stringify(posts);
    }
    """
    
    posts_json = page.evaluate(extract_js)
    posts = json.loads(posts_json) if posts_json else []
    return posts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tab', choices=['foryou', 'following'], default='foryou')
    parser.add_argument('--output', required=True)
    parser.add_argument('--count', type=int, default=10)
    args = parser.parse_args()
    
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        # Launch Chromium with persistent context (to load cookies)
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 900},
        )
        
        # Load cookies from Chrome profile
        cookies = load_x_cookies()
        context.add_cookies(cookies)
        print(f"Loaded {len(cookies)} cookies")
        
        page = context.new_page()
        
        # Navigate to x.com/home
        print("Navigating to x.com/home...")
        page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=30000)
        
        # Check we're logged in
        page.wait_for_timeout(3000)
        current_url = page.url
        print(f"Current URL: {current_url}")
        
        if 'login' in current_url or 'i/flow' in current_url:
            print("ERROR: Not logged in! Cookie injection failed.", file=sys.stderr)
            browser.close()
            sys.exit(1)
        
        # Switch to correct tab
        if args.tab == 'following':
            print("Clicking Following tab...")
            try:
                page.click('[role="tab"]:has-text("Following")', timeout=5000)
                page.wait_for_timeout(2000)
            except:
                print("Could not click Following tab, trying nav link...")
                try:
                    page.goto('https://x.com/home?tab=following', timeout=15000)
                    page.wait_for_timeout(2000)
                except:
                    pass
        else:
            print("On For You tab (default)")
        
        # Wait for posts
        print("Waiting for posts to load...")
        try:
            page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
        except:
            print("WARNING: No posts found after 15s wait")
        
        # Scroll to get more posts
        posts = []
        for scroll_attempt in range(5):
            posts = scrape_posts(page, args.tab)
            print(f"Scroll {scroll_attempt+1}: {len(posts)} posts found")
            if len(posts) >= args.count:
                break
            page.evaluate('window.scrollBy(0, 800)')
            page.wait_for_timeout(1500)
        
        # Trim to target count
        posts = posts[:args.count]
        
        # Add tab field
        tab_value = 'foryou' if args.tab == 'foryou' else 'following'
        for p_item in posts:
            p_item['tab'] = tab_value
        
        browser.close()
    
    # Save output
    output = {
        'scan_time': datetime.now(timezone.utc).isoformat(),
        'tab': args.tab,
        'posts': posts
    }
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    
    print(f"Saved {len(posts)} posts to {output_path}")
    
    # Print sample
    if posts:
        p0 = posts[0]
        print(f"Sample: @{p0.get('authorUsername')} | avatar={'✅' if p0.get('avatar_url') else '❌'} | text_len={len(p0.get('text',''))} | media={len(p0.get('media',[]))}")


if __name__ == '__main__':
    main()
