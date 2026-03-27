"""
tldr.py - Generate casual TL;DR from unseen posts using Anthropic Claude.

Output written to data/latest-briefing.json:
  { "tldr": "...", "updated_at": "...", "unseen_count": N }
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from x_brief.posts_store import get_unseen, load_posts


DEFAULT_DATA_DIR = "data"


def generate_tldr(unseen_posts: list) -> str:
    """Call Anthropic API to generate a casual TL;DR. Falls back to simple text if unavailable."""
    if not unseen_posts:
        return "Nothing new since your last check."

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        posts_text = "\n\n".join([f"@{post['handle']}: {post['text'][:280]}" for post in unseen_posts[:20]])

        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You're summarizing X/Twitter posts for a friend. Write 3-5 casual sentences "
                        "about what's happening. Be opinionated, specific, name accounts. Sound like "
                        "texting a friend, not a news article.\n\n"
                        'Example tone: "Karpathy is warning about LiteLLM being compromised, Claude '
                        "Code just shipped auto mode, and everyone's dunking on Sora getting killed.\"\n\n"
                        f"Posts to summarize:\n{posts_text}\n\n"
                        "Write the summary now (3-5 sentences, casual, no intro like "
                        '"here\'s what\'s happening"):'
                    ),
                }
            ],
        )
        return message.content[0].text.strip()
    except Exception:
        handles = list({post["handle"] for post in unseen_posts[:5]})
        return f"Latest from @{', @'.join(handles)} and others. {len(unseen_posts)} unseen posts."


def run_tldr(data_dir: str = DEFAULT_DATA_DIR) -> dict:
    """Generate TL;DR from unseen posts and write to latest-briefing.json."""
    unseen = get_unseen(data_dir)
    all_posts = load_posts(data_dir)
    now = datetime.now(timezone.utc).isoformat()
    tldr_text = generate_tldr(unseen)

    result = {
        "tldr": tldr_text,
        "updated_at": now,
        "unseen_count": len(unseen),
        "generated_at": now,
        "period_hours": 4,
        "sections": [],
        "stats": {
            "posts_scanned": len(all_posts),
            "unseen_count": len(unseen),
        },
    }

    out_path = Path(data_dir) / "latest-briefing.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate TL;DR from unseen posts")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    args = parser.parse_args()

    result = run_tldr(args.data_dir)
    print(f"TL;DR ({result['unseen_count']} unseen posts): {result['tldr']}")
