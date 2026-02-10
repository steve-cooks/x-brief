"""
Output formatting for briefings (Markdown and HTML)
"""

from datetime import datetime
from jinja2 import Template

from .models import Briefing, BriefingSection


def format_number(n: int) -> str:
    """Format number with K/M suffix for readability."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    else:
        return f"{n:,}"


def format_engagement(post) -> str:
    """Format engagement metrics inline: ❤️ 42 🔁 12 👁 1.2K"""
    metrics = post.metrics
    parts = []
    if metrics.likes > 0:
        parts.append(f"❤️ {format_number(metrics.likes)}")
    if metrics.reposts > 0:
        parts.append(f"🔁 {format_number(metrics.reposts)}")
    if metrics.views > 0:
        parts.append(f"👁 {format_number(metrics.views)}")
    return " ".join(parts) if parts else ""


# Telegram-friendly Markdown template
MARKDOWN_TEMPLATE = """🌅 **𝕏 Brief** — {{ header }}

{% for section in sections %}
────────────────────

{{ section.emoji }} **{{ section.title }}**

{% for item in section.items %}
**{{ item.post.author_name }}** · [@{{ item.post.author_username }}](https://x.com/{{ item.post.author_username }})
{{ item.summary }}

{{ item.engagement }}
[→ View post](https://x.com/{{ item.post.author_username }}/status/{{ item.post.id }})

{% endfor %}
{% endfor %}
────────────────────

📊 **Stats**
{% for key, value in stats.items() %}• {{ key }}: {{ value }}
{% endfor %}

_Generated {{ generated_at }}_
"""

# HTML email template
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>𝕏 Brief — {{ date }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            border-bottom: 3px solid #1DA1F2;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        h1 {
            margin: 0;
            color: #1DA1F2;
            font-size: 28px;
        }
        .date {
            color: #666;
            font-size: 16px;
            margin-top: 5px;
        }
        .section {
            margin-bottom: 40px;
        }
        .section-title {
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #1DA1F2;
        }
        .item {
            background-color: #f8f9fa;
            border-left: 4px solid #1DA1F2;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .author {
            font-weight: bold;
            color: #14171A;
            margin-bottom: 5px;
        }
        .username {
            color: #657786;
            font-size: 14px;
        }
        .summary {
            margin: 10px 0;
            color: #14171A;
        }
        .post-link {
            display: inline-block;
            margin-top: 10px;
            color: #1DA1F2;
            text-decoration: none;
            font-size: 14px;
        }
        .post-link:hover {
            text-decoration: underline;
        }
        .score {
            color: #657786;
            font-size: 13px;
            margin-top: 5px;
        }
        .stats {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 4px;
            margin-top: 30px;
        }
        .stats-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .stats ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .stats li {
            padding: 5px 0;
            color: #14171A;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e1e8ed;
            color: #657786;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌅 𝕏 Brief</h1>
            <div class="date">{{ date }}</div>
        </div>
        
        {% for section in sections %}
        <div class="section">
            <div class="section-title">{{ section.emoji }} {{ section.title }}</div>
            {% for item in section.items %}
            <div class="item">
                <div class="author">
                    {{ item.post.author_name }}
                    <span class="username"><a href="https://x.com/{{ item.post.author_username }}" target="_blank" style="color: #657786; text-decoration: none;">@{{ item.post.author_username }}</a></span>
                </div>
                <div class="summary">{{ item.summary }}</div>
                {% if item.engagement %}
                <div class="score" style="color: #14171A; margin-top: 8px;">{{ item.engagement }}</div>
                {% endif %}
                <a href="https://x.com/{{ item.post.author_username }}/status/{{ item.post.id }}" 
                   class="post-link" target="_blank">View post →</a>
            </div>
            {% endfor %}
        </div>
        {% endfor %}
        
        <div class="stats">
            <div class="stats-title">📊 Stats</div>
            <ul>
                {% for key, value in stats.items %}
                <li><strong>{{ key }}:</strong> {{ value }}</li>
                {% endfor %}
            </ul>
        </div>
        
        <div class="footer">
            Generated {{ generated_at }} by 𝕏 Brief
        </div>
    </div>
</body>
</html>
"""


def format_markdown(briefing: Briefing) -> str:
    """
    Format briefing as Telegram-friendly Markdown
    
    Args:
        briefing: Briefing to format
    
    Returns:
        Formatted markdown string
    """
    template = Template(MARKDOWN_TEMPLATE)
    
    # Calculate time period for header
    period_hours = int((briefing.period_end - briefing.period_start).total_seconds() / 3600)
    date_str = briefing.generated_at.strftime("%A, %B %d")
    header = f"{date_str} (past {period_hours}h)"
    
    # Enhance sections with formatted engagement
    enhanced_sections = []
    for section in briefing.sections:
        enhanced_items = []
        for item in section.items:
            # Create enhanced item with engagement string (not modifying original)
            enhanced_item = type('EnhancedItem', (), {
                'post': item.post,
                'summary': item.summary,
                'category': item.category,
                'score': item.score,
                'engagement': format_engagement(item.post),
            })()
            enhanced_items.append(enhanced_item)
        
        enhanced_section = type('EnhancedSection', (), {
            'title': section.title,
            'emoji': section.emoji,
            'items': enhanced_items,
        })()
        enhanced_sections.append(enhanced_section)
    
    return template.render(
        header=header,
        sections=enhanced_sections,
        stats=briefing.stats,
        generated_at=briefing.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
    )


def format_html(briefing: Briefing) -> str:
    """
    Format briefing as email-ready HTML
    
    Args:
        briefing: Briefing to format
    
    Returns:
        Formatted HTML string
    """
    template = Template(HTML_TEMPLATE)
    
    # Enhance sections with formatted engagement (same as markdown)
    enhanced_sections = []
    for section in briefing.sections:
        enhanced_items = []
        for item in section.items:
            enhanced_item = type('EnhancedItem', (), {
                'post': item.post,
                'summary': item.summary,
                'category': item.category,
                'score': item.score,
                'engagement': format_engagement(item.post),
            })()
            enhanced_items.append(enhanced_item)
        
        enhanced_section = type('EnhancedSection', (), {
            'title': section.title,
            'emoji': section.emoji,
            'items': enhanced_items,
        })()
        enhanced_sections.append(enhanced_section)
    
    return template.render(
        date=briefing.generated_at.strftime("%A, %B %d, %Y"),
        sections=enhanced_sections,
        stats=briefing.stats,
        generated_at=briefing.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
    )


def format_plain(briefing: Briefing) -> str:
    """
    Format briefing as plain text (no markdown)
    
    Args:
        briefing: Briefing to format
    
    Returns:
        Formatted plain text string
    """
    lines = [
        f"𝕏 Brief — {briefing.generated_at.strftime('%A, %B %d, %Y')}",
        "",
    ]
    
    for section in briefing.sections:
        lines.append(f"{section.emoji} {section.title}")
        lines.append("")
        
        for item in section.items:
            lines.append(f"{item.post.author_name} (@{item.post.author_username})")
            lines.append(item.summary)
            lines.append(f"https://x.com/{item.post.author_username}/status/{item.post.id}")
            if item.score:
                lines.append(f"Score: {item.score:.2f}")
            lines.append("")
    
    lines.append("📊 Stats")
    for key, value in briefing.stats.items():
        lines.append(f"• {key}: {value}")
    
    lines.append("")
    lines.append(f"Generated: {briefing.generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
    
    return "\n".join(lines)
