#!/usr/bin/env python3
"""
Zentra Content Pipeline — Stage 4
Generates up to POSTS_PER_DAY finance blog posts for zentraai.in/blog/

Pipeline:
  1. Fetch RSS from top-authority sources (same as Gyan section)
  2. Score articles (source authority + keyword impact + freshness)
  3. Deduplicate against recently published posts
  4. Call Gemini 2.5 Flash to generate structured blog content
  5. Write HTML posts to blog/
  6. Update blog/index.html and blog/feed.xml
"""

import os
import re
import json
import hashlib
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from email.utils import formatdate
import html as html_lib

import feedparser
import google.generativeai as genai

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY  = os.environ["GEMINI_API_KEY"]
POSTS_PER_DAY   = int(os.environ.get("POSTS_PER_DAY", "3"))
SITE_URL        = "https://zentraai.in"
BLOG_URL        = f"{SITE_URL}/blog"
APP_URL         = (
    "https://play.google.com/store/apps/details?id=in.zentra.app"
    "&utm_source=blog&utm_medium=cta&utm_campaign=content"
)
BLOG_DIR        = Path(__file__).parent.parent / "blog"
PUBLISHED_LOG   = BLOG_DIR / "published.json"

# ── RSS sources — high-authority only for blog content ───────────────────────
RSS_SOURCES = [
    {"name": "RBI",          "url": "https://rbi.org.in/pressreleases_rss.xml"},
    {"name": "SEBI",         "url": "https://www.sebi.gov.in/sebirss.xml"},
    {"name": "ET Wealth",    "url": "https://economictimes.indiatimes.com/wealth/rssfeeds/44877303.cms"},
    {"name": "ET Economy",   "url": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms"},
    {"name": "Moneycontrol", "url": "https://www.moneycontrol.com/rss/personalfinance.xml"},
    {"name": "Mint Money",   "url": "https://www.livemint.com/rss/money"},
    {"name": "NDTV Profit",  "url": "https://www.ndtvprofit.com/stories.rss"},
]

SOURCE_SCORES = {
    "RBI": 25, "SEBI": 25,
    "ET Wealth": 20, "ET Economy": 17,
    "Moneycontrol": 18, "Mint Money": 17,
    "NDTV Profit": 16,
}

HIGH_IMPACT_KW = [
    "repo rate", "rbi policy", "monetary policy",
    "union budget", "income tax", "itr",
    "tax slab", "gst", "tds", "80c",
    "inflation", "cpi", "gdp",
    "emi", "home loan",
    "mutual fund", "sip", "nifty", "sensex", "ipo",
    "sebi", "interest rate",
]

BLOCKED_KW = [
    "election", "cricket", "ipl", "bollywood", "murder", "rape",
    "arrest", "covid", "earthquake", "cyclone", "blast", "terror",
]

DEDUPLICATION_WINDOW_DAYS = 14  # skip topics published in last 14 days


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_article(title: str, description: str, source: str, pub_dt: datetime.datetime) -> int:
    score = SOURCE_SCORES.get(source, 10)
    haystack = f"{title} {description}".lower()

    hits = sum(1 for kw in HIGH_IMPACT_KW if kw in haystack)
    score += min(hits * 5, 25)

    age_hours = (datetime.datetime.utcnow() - pub_dt).total_seconds() / 3600
    if age_hours < 3:    score += 25
    elif age_hours < 8:  score += 18
    elif age_hours < 24: score += 10
    elif age_hours < 48: score += 4

    return min(score, 100)


def is_finance_content(title: str, description: str) -> bool:
    haystack = f"{title} {description}".lower()
    if any(kw in haystack for kw in BLOCKED_KW):
        return False
    return any(kw in haystack for kw in HIGH_IMPACT_KW)


# ── RSS fetch ─────────────────────────────────────────────────────────────────

def fetch_articles() -> list[dict]:
    articles = []
    for src in RSS_SOURCES:
        try:
            req = Request(src["url"], headers={"User-Agent": "ZentraBot/1.0"})
            with urlopen(req, timeout=10) as resp:
                feed = feedparser.parse(resp.read())
            for entry in feed.entries[:15]:
                title = entry.get("title", "").strip()
                desc  = entry.get("summary", entry.get("description", "")).strip()
                url   = entry.get("link", "").strip()
                # Parse publish date
                pub_dt = datetime.datetime.utcnow()
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    import time
                    pub_dt = datetime.datetime.utcfromtimestamp(
                        time.mktime(entry.published_parsed)
                    )
                if not title or not url:
                    continue
                if not is_finance_content(title, desc):
                    continue
                articles.append({
                    "title":       title,
                    "description": _strip_html(desc)[:400],
                    "url":         url,
                    "source":      src["name"],
                    "pub_dt":      pub_dt,
                    "score":       score_article(title, desc, src["name"], pub_dt),
                })
        except Exception as e:
            print(f"[warn] {src['name']} fetch failed: {e}")
    articles.sort(key=lambda a: a["score"], reverse=True)
    return articles


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# ── Deduplication ─────────────────────────────────────────────────────────────

def load_published() -> list[dict]:
    if PUBLISHED_LOG.exists():
        return json.loads(PUBLISHED_LOG.read_text())
    return []


def save_published(log: list[dict]) -> None:
    cutoff = (datetime.datetime.utcnow()
              - datetime.timedelta(days=DEDUPLICATION_WINDOW_DAYS)).isoformat()
    log = [e for e in log if e["date"] >= cutoff]
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    PUBLISHED_LOG.write_text(json.dumps(log, indent=2))


def already_published(title: str, log: list[dict]) -> bool:
    title_lower = title.lower()
    for entry in log:
        # Fuzzy: if 5+ consecutive words overlap, consider it a duplicate topic
        entry_words = set(entry["title"].lower().split())
        title_words  = set(title_lower.split())
        if len(entry_words & title_words) >= 5:
            return True
    return False


# ── Gemini content generation ─────────────────────────────────────────────────

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={"response_mime_type": "application/json"},
)

_PROMPT_TEMPLATE = """
You are a financial education writer for HYT MONEY (zentraai.in), targeting Indian salaried professionals aged 25-40.

Write a 350-400 word educational blog post based on this news event.

Source article:
Title: {title}
Summary: {description}
Source: {source}

Return ONLY a JSON object with these exact keys:
{{
  "seo_title": "SEO headline under 60 characters — factual, no clickbait",
  "meta_description": "SEO description 120-150 characters — what the reader will learn",
  "slug": "url-slug-max-50-chars-lowercase-hyphens-no-special-chars",
  "hook": "2-sentence opening that creates curiosity without sensationalism",
  "body_paragraphs": [
    "Paragraph 1 — what happened (60-70 words)",
    "Paragraph 2 — why it matters for a salaried Indian (60-70 words)",
    "Paragraph 3 — what you can do about it (60-70 words, practical, no stock tips)"
  ],
  "key_takeaways": [
    "Takeaway 1 — concrete, actionable",
    "Takeaway 2 — concrete, actionable",
    "Takeaway 3 — concrete, actionable"
  ],
  "tags": ["tag1", "tag2", "tag3"]
}}

Rules:
- Educational only — no buy/sell/hold recommendations
- No sensationalism or fear-mongering
- Cite the source by name if referencing specific data
- Keep language simple enough for a non-finance audience
"""


def generate_post(article: dict) -> dict | None:
    prompt = _PROMPT_TEMPLATE.format(
        title=article["title"],
        description=article["description"],
        source=article["source"],
    )
    try:
        response = _model.generate_content(prompt)
        data = json.loads(response.text)
        # Validate required keys
        required = {"seo_title", "meta_description", "slug", "hook",
                    "body_paragraphs", "key_takeaways"}
        if not required.issubset(data.keys()):
            print(f"[warn] Gemini response missing keys for: {article['title']}")
            return None
        if not isinstance(data["body_paragraphs"], list) or len(data["body_paragraphs"]) < 2:
            return None
        return data
    except Exception as e:
        print(f"[warn] Gemini generation failed: {e}")
        return None


# ── HTML generation ───────────────────────────────────────────────────────────

_POST_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{seo_title} | HYT MONEY Blog</title>
  <meta name="description" content="{meta_description}" />
  <meta property="og:title" content="{seo_title}" />
  <meta property="og:description" content="{meta_description}" />
  <meta property="og:url" content="{post_url}" />
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="HYT MONEY" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{seo_title}" />
  <meta name="twitter:description" content="{meta_description}" />
  <link rel="canonical" href="{post_url}" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #080810; color: #F0F0FA; font-family: 'DM Sans', sans-serif;
            font-size: 16px; line-height: 1.7; }}
    a {{ color: #7B6FF0; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .nav {{ padding: 18px 24px; border-bottom: 1px solid #1A1A2E;
             display: flex; align-items: center; gap: 12px; }}
    .nav-logo {{ font-weight: 800; font-size: 18px; letter-spacing: 0.05em;
                  background: linear-gradient(135deg, #7B6FF0, #4ECDC4);
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .nav-sep {{ color: #3A3A5C; }}
    .nav-link {{ color: #7070A0; font-size: 14px; }}
    .container {{ max-width: 760px; margin: 0 auto; padding: 40px 24px 80px; }}
    .meta {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: center;
              margin-bottom: 20px; }}
    .tag {{ background: #1A1A2E; color: #7B6FF0; font-size: 12px;
             font-weight: 600; padding: 4px 10px; border-radius: 20px;
             border: 1px solid #2A2A4E; }}
    .date {{ color: #7070A0; font-size: 13px; }}
    .source {{ color: #7070A0; font-size: 13px; }}
    h1 {{ font-size: clamp(24px, 4vw, 36px); font-weight: 800; line-height: 1.25;
           margin-bottom: 14px; }}
    .hook {{ font-size: 18px; color: #B0B0D0; font-style: italic;
              border-left: 3px solid #7B6FF0; padding-left: 16px;
              margin-bottom: 32px; line-height: 1.6; }}
    .body p {{ margin-bottom: 20px; color: #D0D0EA; }}
    .takeaways {{ background: #10101C; border: 1px solid #1A1A2E;
                   border-radius: 12px; padding: 24px; margin: 32px 0; }}
    .takeaways h2 {{ font-size: 16px; font-weight: 700; color: #4ECDC4;
                      margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }}
    .takeaways ul {{ list-style: none; display: flex; flex-direction: column; gap: 10px; }}
    .takeaways li {{ padding-left: 24px; position: relative; color: #D0D0EA; font-size: 15px; }}
    .takeaways li::before {{ content: "→"; position: absolute; left: 0;
                               color: #4ECDC4; font-weight: 700; }}
    .disclaimer {{ font-size: 12px; color: #5050A0; border-top: 1px solid #1A1A2E;
                    padding-top: 16px; margin-top: 32px; }}
    .cta-box {{ background: linear-gradient(135deg, #0D0D20, #12122A);
                 border: 1px solid #2A2A5A; border-radius: 16px;
                 padding: 28px; margin-top: 40px; text-align: center; }}
    .cta-box p {{ color: #B0B0D0; margin-bottom: 16px; font-size: 15px; }}
    .cta-btn {{ display: inline-block; background: linear-gradient(135deg, #7B6FF0, #4ECDC4);
                 color: #fff; font-weight: 700; font-size: 15px;
                 padding: 12px 28px; border-radius: 8px; }}
    .back {{ color: #7070A0; font-size: 14px; display: inline-flex;
              align-items: center; gap: 6px; margin-bottom: 32px; }}
    @media (max-width: 600px) {{
      .container {{ padding: 24px 16px 60px; }}
    }}
  </style>
</head>
<body>
  <nav class="nav">
    <a href="{site_url}" class="nav-logo">ZENTRA</a>
    <span class="nav-sep">/</span>
    <a href="{blog_url}" class="nav-link">Finance Blog</a>
  </nav>
  <main class="container">
    <a href="{blog_url}" class="back">← All articles</a>
    <div class="meta">
      {tag_chips}
      <span class="date">{pub_date}</span>
      <span class="source">via {source}</span>
    </div>
    <h1>{seo_title}</h1>
    <p class="hook">{hook}</p>
    <div class="body">
      {body_html}
    </div>
    <div class="takeaways">
      <h2>&#9889; Key Takeaways</h2>
      <ul>
        {takeaway_items}
      </ul>
    </div>
    <p class="disclaimer">
      This article is for educational purposes only and does not constitute
      investment, tax, or financial advice. Please consult a qualified financial
      advisor before making any financial decisions.
    </p>
    <div class="cta-box">
      <p>Track your spending, monitor your EMIs, and get AI-powered insights
         on how news events affect <em>your</em> finances — all in HYT MONEY.</p>
      <a href="{app_url}" class="cta-btn">Get HYT MONEY — Free</a>
    </div>
  </main>
</body>
</html>"""


def build_post_html(data: dict, article: dict, pub_date_str: str, post_url: str) -> str:
    tags = data.get("tags", [])[:3]
    tag_chips = " ".join(f'<span class="tag">{html_lib.escape(t)}</span>' for t in tags)
    body_html = "\n      ".join(
        f"<p>{html_lib.escape(p)}</p>" for p in data["body_paragraphs"]
    )
    takeaway_items = "\n        ".join(
        f"<li>{html_lib.escape(t)}</li>" for t in data["key_takeaways"]
    )
    return _POST_TEMPLATE.format(
        seo_title      = html_lib.escape(data["seo_title"]),
        meta_description = html_lib.escape(data["meta_description"]),
        post_url       = post_url,
        site_url       = SITE_URL,
        blog_url       = BLOG_URL,
        app_url        = APP_URL,
        tag_chips      = tag_chips,
        pub_date       = pub_date_str,
        source         = html_lib.escape(article["source"]),
        hook           = html_lib.escape(data["hook"]),
        body_html      = body_html,
        takeaway_items = takeaway_items,
    )


# ── Blog index page ───────────────────────────────────────────────────────────

def rebuild_index(published_log: list[dict]) -> None:
    recent = sorted(published_log, key=lambda e: e["date"], reverse=True)[:30]
    cards = ""
    for entry in recent:
        tags_html = " ".join(
            f'<span class="tag">{html_lib.escape(t)}</span>'
            for t in entry.get("tags", [])[:2]
        )
        cards += f"""
    <a href="{entry['url']}" class="card">
      <div class="card-meta">{tags_html}<span class="date">{entry['date'][:10]}</span></div>
      <h2>{html_lib.escape(entry['title'])}</h2>
      <p>{html_lib.escape(entry['description'])}</p>
    </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Finance Blog | HYT MONEY</title>
  <meta name="description" content="Daily finance insights for Indian salaried professionals — explained simply by HYT MONEY." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;800&display=swap" rel="stylesheet" />
  <link rel="alternate" type="application/rss+xml" title="HYT MONEY Blog" href="{BLOG_URL}/feed.xml" />
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #080810; color: #F0F0FA; font-family: 'DM Sans', sans-serif; }}
    a {{ text-decoration: none; }}
    .nav {{ padding: 18px 24px; border-bottom: 1px solid #1A1A2E;
             display: flex; align-items: center; gap: 12px; }}
    .nav-logo {{ font-weight: 800; font-size: 18px;
                  background: linear-gradient(135deg, #7B6FF0, #4ECDC4);
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .nav-sep {{ color: #3A3A5C; }}
    .nav-link {{ color: #7070A0; font-size: 14px; }}
    .container {{ max-width: 900px; margin: 0 auto; padding: 48px 24px 80px; }}
    .hero {{ margin-bottom: 48px; }}
    .hero h1 {{ font-size: clamp(28px, 5vw, 42px); font-weight: 800; margin-bottom: 12px; }}
    .hero p {{ color: #7070A0; font-size: 16px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
              gap: 20px; }}
    .card {{ background: #10101C; border: 1px solid #1A1A2E; border-radius: 12px;
              padding: 20px; display: flex; flex-direction: column; gap: 10px;
              transition: border-color 0.2s; color: #F0F0FA; }}
    .card:hover {{ border-color: #7B6FF0; }}
    .card-meta {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
    .tag {{ background: #1A1A2E; color: #7B6FF0; font-size: 11px;
             font-weight: 600; padding: 3px 8px; border-radius: 20px; }}
    .date {{ color: #5050A0; font-size: 12px; }}
    .card h2 {{ font-size: 15px; font-weight: 700; line-height: 1.4; color: #E0E0F8; }}
    .card p {{ font-size: 13px; color: #7070A0; line-height: 1.5; flex: 1; }}
    .empty {{ color: #5050A0; text-align: center; padding: 60px 0; }}
  </style>
</head>
<body>
  <nav class="nav">
    <a href="{SITE_URL}" class="nav-logo">ZENTRA</a>
    <span class="nav-sep">/</span>
    <span class="nav-link">Finance Blog</span>
  </nav>
  <main class="container">
    <div class="hero">
      <h1>Finance Insights</h1>
      <p>Daily finance news explained simply for Indian salaried professionals.</p>
    </div>
    <div class="grid">
      {'<p class="empty">No posts yet — check back soon.</p>' if not recent else cards}
    </div>
  </main>
</body>
</html>"""
    (BLOG_DIR / "index.html").write_text(index_html, encoding="utf-8")


# ── RSS feed ──────────────────────────────────────────────────────────────────

def rebuild_feed(published_log: list[dict]) -> None:
    recent = sorted(published_log, key=lambda e: e["date"], reverse=True)[:20]
    items = ""
    for entry in recent:
        pub_rfc = formatdate(
            datetime.datetime.fromisoformat(entry["date"]).timestamp(),
            usegmt=True,
        )
        items += f"""
  <item>
    <title><![CDATA[{entry['title']}]]></title>
    <link>{entry['url']}</link>
    <guid isPermaLink="true">{entry['url']}</guid>
    <pubDate>{pub_rfc}</pubDate>
    <description><![CDATA[{entry['description']}]]></description>
    <source url="{BLOG_URL}/feed.xml">HYT MONEY Blog</source>
  </item>"""

    feed_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>HYT MONEY Blog</title>
    <link>{BLOG_URL}</link>
    <atom:link href="{BLOG_URL}/feed.xml" rel="self" type="application/rss+xml" />
    <description>Daily finance insights for Indian salaried professionals.</description>
    <language>en-in</language>
    <lastBuildDate>{formatdate(usegmt=True)}</lastBuildDate>
    {items}
  </channel>
</rss>"""
    (BLOG_DIR / "feed.xml").write_text(feed_xml, encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    published_log = load_published()
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    articles = fetch_articles()
    print(f"[info] Fetched {len(articles)} scored articles")

    generated = 0
    for article in articles:
        if generated >= POSTS_PER_DAY:
            break
        if already_published(article["title"], published_log):
            print(f"[skip] Already covered: {article['title'][:60]}")
            continue

        print(f"[gen]  Score={article['score']} — {article['title'][:70]}")
        data = generate_post(article)
        if data is None:
            continue

        # Sanitise slug
        slug = re.sub(r"[^a-z0-9-]", "", data["slug"].lower().replace(" ", "-"))[:50]
        filename = f"{today}-{slug}.html"
        post_url = f"{BLOG_URL}/{filename}"

        post_html = build_post_html(
            data, article,
            pub_date_str=datetime.datetime.utcnow().strftime("%B %d, %Y"),
            post_url=post_url,
        )
        (BLOG_DIR / filename).write_text(post_html, encoding="utf-8")
        print(f"[ok]   Written {filename}")

        published_log.append({
            "date":        datetime.datetime.utcnow().isoformat(),
            "title":       data["seo_title"],
            "description": data["meta_description"],
            "url":         post_url,
            "tags":        data.get("tags", []),
            "slug":        slug,
            "source":      article["source"],
        })
        generated += 1

    if generated == 0:
        print("[info] No new posts generated today.")
        return

    save_published(published_log)
    rebuild_index(published_log)
    rebuild_feed(published_log)
    print(f"[done] {generated} post(s) published. Index and feed updated.")


if __name__ == "__main__":
    main()
