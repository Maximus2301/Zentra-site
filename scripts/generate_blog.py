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
import time
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
    for attempt in range(3):
        try:
            response = _model.generate_content(prompt)
            data = json.loads(response.text)
            required = {"seo_title", "meta_description", "slug", "hook",
                        "body_paragraphs", "key_takeaways"}
            if not required.issubset(data.keys()):
                print(f"[warn] Gemini response missing keys for: {article['title']}")
                return None
            if not isinstance(data["body_paragraphs"], list) or len(data["body_paragraphs"]) < 2:
                return None
            return data
        except Exception as e:
            msg = str(e)
            if "429" in msg and attempt < 2:
                # Parse the suggested retry delay from the API error message
                m = re.search(r"retry in ([\d.]+)s", msg)
                wait = float(m.group(1)) + 5 if m else 65.0
                print(f"[rate-limit] Quota hit — sleeping {wait:.0f}s then retrying ({attempt + 2}/3)…")
                time.sleep(wait)
                continue
            print(f"[warn] Gemini generation failed: {e}")
            return None
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
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0D0D0F; color: #F0F0EC; font-family: 'DM Sans', sans-serif;
            font-size: 16px; line-height: 1.7; -webkit-font-smoothing: antialiased; }}
    a {{ color: #E2C05E; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    nav {{ padding: 18px 24px; border-bottom: 1px solid #2A2A2E;
            display: flex; align-items: center; gap: 14px;
            background: rgba(10,10,12,0.88); backdrop-filter: blur(20px);
            position: sticky; top: 0; z-index: 100; }}
    .logo {{ display: flex; align-items: center; gap: 10px; text-decoration: none; }}
    .logo-mark {{ width: 32px; height: 32px; border-radius: 9px;
      background: #0D0D1F; border: 1.2px solid rgba(201,162,42,0.30);
      box-shadow: inset 0 1px 0 rgba(241,215,122,0.08);
      display: grid; place-items: center; flex-shrink: 0; }}
    .logo-mark span {{ font-family: 'Cinzel', serif; font-size: 17px; font-weight: 700; line-height: 1;
      background: linear-gradient(90deg,#8B6914,#B48A1E,#D4AF37,#F1D77A,#D4AF37,#B48A1E,#8B6914);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
    .logo-copy {{ display: flex; flex-direction: column; gap: 2px; }}
    .logo-name {{ font-family: 'Cinzel', serif; font-size: 16px; font-weight: 700;
      letter-spacing: 0.18em; text-transform: uppercase; color: #E2C05E; line-height: 1; }}
    .logo-sub {{ font-size: 9px; font-weight: 600; letter-spacing: 0.24em;
      text-transform: uppercase; color: #8A8A90; line-height: 1; }}
    .nav-sep {{ color: #2A2A2E; font-size: 14px; }}
    .nav-link {{ color: #8A8A90; font-size: 14px; }}
    .container {{ max-width: 760px; margin: 0 auto; padding: 40px 24px 80px; }}
    .meta {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: center;
              margin-bottom: 20px; }}
    .tag {{ background: rgba(201,162,42,0.10); color: #E2C05E; font-size: 12px;
             font-weight: 600; padding: 4px 10px; border-radius: 20px;
             border: 1px solid rgba(201,162,42,0.22); }}
    .date {{ color: #5A5A60; font-size: 13px; }}
    .source {{ color: #5A5A60; font-size: 13px; }}
    h1 {{ font-size: clamp(24px, 4vw, 36px); font-weight: 800; line-height: 1.25;
           margin-bottom: 14px; }}
    .hook {{ font-size: 18px; color: #A0A0A8; font-style: italic;
              border-left: 3px solid #C9A22A; padding-left: 16px;
              margin-bottom: 32px; line-height: 1.6; }}
    .body p {{ margin-bottom: 20px; color: #C8C8C0; }}
    .takeaways {{ background: #131315; border: 1px solid #2A2A2E;
                   border-radius: 12px; padding: 24px; margin: 32px 0; }}
    .takeaways h2 {{ font-size: 16px; font-weight: 700; color: #6ECFDB;
                      margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }}
    .takeaways ul {{ list-style: none; display: flex; flex-direction: column; gap: 10px; }}
    .takeaways li {{ padding-left: 24px; position: relative; color: #C8C8C0; font-size: 15px; }}
    .takeaways li::before {{ content: "→"; position: absolute; left: 0;
                               color: #6ECFDB; font-weight: 700; }}
    .disclaimer {{ font-size: 12px; color: #5A5A60; border-top: 1px solid #2A2A2E;
                    padding-top: 16px; margin-top: 32px; }}
    /* ── Carousel section ── */
    .carousel-wrap {{ margin: 36px 0 0; padding-top: 28px; border-top: 1px solid #2A2A2E; }}
    .carousel-wrap h3 {{ font-size: 15px; font-weight: 700; color: #E2C05E;
      margin-bottom: 8px; }}
    .carousel-wrap > p {{ font-size: 13px; color: #5A5A60; margin-bottom: 18px; }}
    .slide-strip {{ display: flex; gap: 12px; overflow-x: auto; padding-bottom: 10px;
      scrollbar-width: thin; scrollbar-color: rgba(201,162,42,0.25) transparent; }}
    .slide-strip::-webkit-scrollbar {{ height: 4px; }}
    .slide-strip::-webkit-scrollbar-thumb {{ background: rgba(201,162,42,0.25); border-radius: 4px; }}
    .slide-card {{ flex-shrink: 0; position: relative; }}
    .slide-card img {{ width: 172px; height: 172px; object-fit: cover;
      border-radius: 10px; border: 1px solid rgba(201,162,42,0.18); display: block; }}
    .slide-dl {{ position: absolute; top: 6px; right: 6px;
      background: rgba(13,13,15,0.82); color: #E2C05E; font-size: 11px;
      font-weight: 700; padding: 3px 8px; border-radius: 6px;
      text-decoration: none; backdrop-filter: blur(4px);
      border: 1px solid rgba(201,162,42,0.22); }}
    .slide-label {{ font-size: 10px; color: #5A5A60; text-align: center; margin-top: 5px; }}
    .platform-row {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }}
    .pbtn {{ display: inline-flex; align-items: center; gap: 6px;
      padding: 9px 16px; border-radius: 10px; font-size: 13px; font-weight: 700;
      text-decoration: none; cursor: pointer; border: none; font-family: inherit;
      transition: opacity 0.2s; white-space: nowrap; }}
    .pbtn:hover {{ opacity: 0.82; }}
    .p-insta {{ background: linear-gradient(135deg,#F58529,#DD2A7B,#515BD4); color: #fff; }}
    .p-li {{ background: #0A66C2; color: #fff; }}
    .p-wa {{ background: #25D366; color: #fff; }}
    .p-tw {{ background: #000; color: #fff; border: 1px solid #2A2A2E; }}
    .p-copy {{ background: rgba(201,162,42,0.10); color: #E2C05E;
      border: 1.5px solid rgba(201,162,42,0.25); }}
    .p-zip {{ background: rgba(110,207,219,0.10); color: #6ECFDB;
      border: 1.5px solid rgba(110,207,219,0.25); }}
    /* ── Simple share bar (fallback) ── */
    .share-bar {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
      margin: 32px 0 0; padding-top: 24px; border-top: 1px solid #2A2A2E; }}
    .share-label {{ font-size: 13px; color: #5A5A60; font-weight: 600;
      letter-spacing: 0.06em; text-transform: uppercase; }}
    .share-btn, .copy-btn {{ display: inline-flex; align-items: center; gap: 7px;
      padding: 9px 18px; border-radius: 10px; font-size: 13px; font-weight: 700;
      cursor: pointer; border: none; transition: opacity 0.2s; font-family: inherit; }}
    .share-btn {{ background: linear-gradient(135deg, #F1D77A, #C9A22A); color: #1A1200; }}
    .copy-btn  {{ background: rgba(201,162,42,0.10); color: #E2C05E;
      border: 1.5px solid rgba(201,162,42,0.25); }}
    .share-btn:hover, .copy-btn:hover {{ opacity: 0.85; }}
    .cta-box {{ background: linear-gradient(135deg, #0F0F11, #131315);
                 border: 1px solid rgba(201,162,42,0.22); border-radius: 16px;
                 padding: 28px; margin-top: 40px; text-align: center; }}
    .cta-box p {{ color: #A0A0A8; margin-bottom: 16px; font-size: 15px; }}
    .cta-btn {{ display: inline-block;
                 background: linear-gradient(135deg, #F1D77A, #C9A22A, #9A7515);
                 color: #1A1200; font-weight: 700; font-size: 15px;
                 padding: 12px 28px; border-radius: 8px; }}
    .back {{ color: #8A8A90; font-size: 14px; display: inline-flex;
              align-items: center; gap: 6px; margin-bottom: 32px; }}
    .share-bar {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
                   margin: 32px 0 0; padding-top: 24px; border-top: 1px solid #2A2A2E; }}
    .share-label {{ font-size: 13px; color: #5A5A60; font-weight: 600;
                     letter-spacing: 0.06em; text-transform: uppercase; }}
    .share-btn, .copy-btn {{
      display: inline-flex; align-items: center; gap: 7px;
      padding: 9px 18px; border-radius: 10px; font-size: 13px;
      font-weight: 700; cursor: pointer; border: none; transition: opacity 0.2s;
      font-family: inherit;
    }}
    .share-btn {{ background: linear-gradient(135deg, #F1D77A, #C9A22A); color: #1A1200; }}
    .copy-btn  {{ background: rgba(201,162,42,0.10); color: #E2C05E;
                   border: 1.5px solid rgba(201,162,42,0.25); }}
    .share-btn:hover, .copy-btn:hover {{ opacity: 0.85; }}
    @media (max-width: 600px) {{
      .container {{ padding: 24px 16px 60px; }}
    }}
  </style>
</head>
<body>
  <nav>
    <a href="{site_url}" class="logo">
      <div class="logo-mark"><span>H</span></div>
      <div class="logo-copy">
        <span class="logo-name">HYT</span>
        <span class="logo-sub">Money</span>
      </div>
    </a>
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

    {carousel_section}

    <div class="cta-box">
      <p>Track your spending, monitor your EMIs, and get AI-powered insights
         on how news events affect <em>your</em> finances — all in HYT MONEY.</p>
      <a href="{app_url}" class="cta-btn">Get HYT MONEY — Free</a>
    </div>
  </main>
</body>
</html>"""


def _build_carousel_section(post_url: str, title: str, desc: str, carousel_slug: str) -> str:
    from urllib.parse import quote
    base     = f"{BLOG_URL}/carousels/{carousel_slug}/"
    enc_url  = quote(post_url, safe="")
    enc_text = quote(f"{title[:100]} {post_url}", safe="")
    enc_li   = quote(desc[:120], safe="")

    slides = [
        ("slide-1-hook.jpg",   "Hook"),
        ("slide-2-point1.jpg", "Point 1"),
        ("slide-3-point2.jpg", "Point 2"),
        ("slide-4-cta.jpg",    "HYT Money"),
    ]
    cards = "".join(
        f'<div class="slide-card">'
        f'<img src="{base}{fname}" alt="{label}" loading="lazy">'
        f'<a href="{base}{fname}" download class="slide-dl">↓</a>'
        f'<div class="slide-label">{label}</div>'
        f'</div>'
        for fname, label in slides
    )

    li_url = f"https://www.linkedin.com/shareArticle?mini=true&url={enc_url}&title={quote(title,safe='')}&summary={enc_li}"
    wa_url = f"https://wa.me/?text={enc_text}"
    tw_url = f"https://twitter.com/intent/tweet?text={enc_text}"
    zip_url = f"{base}carousel.zip"

    return (
        '<div class="carousel-wrap">'
          '<h3>&#128247; Share as Carousel</h3>'
          '<p>Save the slides below and post as a carousel on Instagram, LinkedIn, or WhatsApp — or share the article link directly.</p>'
          f'<div class="slide-strip">{cards}</div>'
          '<div class="platform-row">'
            '<button class="pbtn p-insta" onclick="_wsShare()">&#128247; Instagram</button>'
            f'<a href="{li_url}" target="_blank" rel="noopener" class="pbtn p-li">LinkedIn</a>'
            f'<a href="{wa_url}" target="_blank" rel="noopener" class="pbtn p-wa">WhatsApp</a>'
            f'<a href="{tw_url}" target="_blank" rel="noopener" class="pbtn p-tw">Twitter / X</a>'
            '<button class="pbtn p-copy" onclick="_cpLink()" id="cpBtn">Copy link</button>'
            f'<a href="{zip_url}" download class="pbtn p-zip">&#8595; Download all slides</a>'
          '</div>'
        '</div>'
        '<script>'
          'function _wsShare(){'
            'var d=document.querySelector(\'meta[name="description"]\');'
            'if(navigator.share){navigator.share({title:document.title,text:d?d.content:"",url:location.href}).catch(function(){});}'
            'else{_cpLink();}'
          '}'
          'function _cpLink(){'
            'navigator.clipboard.writeText(location.href).then(function(){'
              'var b=document.getElementById("cpBtn");'
              'b.textContent="✓ Copied!";'
              'setTimeout(function(){b.textContent="Copy link";},2000);'
            '});'
          '}'
        '</script>'
    )


def _build_simple_share() -> str:
    return (
        '<div class="share-bar">'
          '<span class="share-label">Share</span>'
          '<button class="share-btn" onclick="_wsShare2()">Share to Instagram / WhatsApp</button>'
          '<button class="copy-btn" onclick="_cpLink2()" id="cpBtn2">Copy link</button>'
        '</div>'
        '<script>'
          'function _wsShare2(){'
            'var d=document.querySelector(\'meta[name="description"]\');'
            'if(navigator.share){navigator.share({title:document.title,text:d?d.content:"",url:location.href}).catch(function(){});}'
            'else{_cpLink2();}'
          '}'
          'function _cpLink2(){'
            'navigator.clipboard.writeText(location.href).then(function(){'
              'var b=document.getElementById("cpBtn2");'
              'b.textContent="✓ Copied!";'
              'setTimeout(function(){b.textContent="Copy link";},2000);'
            '});'
          '}'
        '</script>'
    )


def build_post_html(data: dict, article: dict, pub_date_str: str, post_url: str,
                    carousel_slug: str | None = None) -> str:
    tags = data.get("tags", [])[:3]
    tag_chips = " ".join(f'<span class="tag">{html_lib.escape(t)}</span>' for t in tags)
    body_html = "\n      ".join(
        f"<p>{html_lib.escape(p)}</p>" for p in data["body_paragraphs"]
    )
    takeaway_items = "\n        ".join(
        f"<li>{html_lib.escape(t)}</li>" for t in data["key_takeaways"]
    )
    if carousel_slug:
        carousel_section = _build_carousel_section(
            post_url, data["seo_title"], data["meta_description"], carousel_slug
        )
    else:
        carousel_section = _build_simple_share()

    return _POST_TEMPLATE.format(
        seo_title        = html_lib.escape(data["seo_title"]),
        meta_description = html_lib.escape(data["meta_description"]),
        post_url         = post_url,
        site_url         = SITE_URL,
        blog_url         = BLOG_URL,
        app_url          = APP_URL,
        tag_chips        = tag_chips,
        pub_date         = pub_date_str,
        source           = html_lib.escape(article["source"]),
        hook             = html_lib.escape(data["hook"]),
        body_html        = body_html,
        takeaway_items   = takeaway_items,
        carousel_section = carousel_section,
    )


# ── Blog index page ───────────────────────────────────────────────────────────

def rebuild_index(published_log: list[dict]) -> None:
    recent = sorted(published_log, key=lambda e: e["date"], reverse=True)[:30]
    rows = ""
    slide_names = [
        ("slide-1-hook.jpg",   "Hook"),
        ("slide-2-point1.jpg", "Point 1"),
        ("slide-3-point2.jpg", "Point 2"),
        ("slide-4-cta.jpg",    "HYT Money"),
    ]
    for i, entry in enumerate(recent):
        tags_html = " ".join(
            f'<span class="tag">{html_lib.escape(t)}</span>'
            for t in entry.get("tags", [])[:2]
        )
        filename = entry["url"].rstrip("/").split("/")[-1].replace(".html", "")
        carousel_base = f"{BLOG_URL}/carousels/{filename}"
        slides_html = ""
        dots_html = ""
        for j, (sname, slabel) in enumerate(slide_names):
            err = ' onerror="this.closest(\'.post-carousel\').style.display=\'none\';this.closest(\'.post-row\').classList.add(\'no-carousel\')"' if j == 0 else ""
            slides_html += (
                f'<div class="slide"><a href="{entry["url"]}">'
                f'<img src="{carousel_base}/{sname}" alt="{html_lib.escape(slabel)}" loading="lazy"{err}>'
                f"</a></div>"
            )
            dots_html += f'<span class="dot{" active" if j == 0 else ""}"></span>'
        cid = f"c{i}"
        rows += f"""
    <div class="post-row">
      <div class="post-carousel">
        <div class="mini-carousel" id="{cid}">
          <div class="slides-track">{slides_html}</div>
          <button class="nav-btn prev">&#8249;</button>
          <button class="nav-btn next">&#8250;</button>
          <div class="dots">{dots_html}</div>
          <span class="slide-counter" id="{cid}-counter">1 / 4</span>
        </div>
      </div>
      <a href="{entry['url']}" class="post-content">
        <div class="card-meta">{tags_html}<span class="date">{entry['date'][:10]}</span></div>
        <h2 class="post-title">{html_lib.escape(entry['title'])}</h2>
        <p class="post-desc">{html_lib.escape(entry['description'])}</p>
        <span class="read-more">Read article &#x203A;</span>
      </a>
    </div>"""

    empty_or_rows = '<p class="empty">No posts yet — check back soon.</p>' if not recent else rows
    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Finance Blog | HYT MONEY</title>
  <meta name="description" content="Daily finance insights for Indian salaried professionals — explained simply by HYT MONEY." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=DM+Sans:wght@400;600;700;800&display=swap" rel="stylesheet" />
  <link rel="alternate" type="application/rss+xml" title="HYT MONEY Blog" href="{BLOG_URL}/feed.xml" />
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0D0D0F; color: #F0F0EC; font-family: 'DM Sans', sans-serif;
            -webkit-font-smoothing: antialiased; }}
    a {{ text-decoration: none; }}
    nav {{ padding: 18px 24px; border-bottom: 1px solid #2A2A2E;
           display: flex; align-items: center; gap: 14px;
           background: rgba(10,10,12,0.88); backdrop-filter: blur(20px);
           position: sticky; top: 0; z-index: 100; }}
    .logo {{ display: flex; align-items: center; gap: 10px; text-decoration: none; }}
    .logo-mark {{ width: 32px; height: 32px; border-radius: 9px;
      background: #0D0D1F; border: 1.2px solid rgba(201,162,42,0.30);
      box-shadow: inset 0 1px 0 rgba(241,215,122,0.08);
      display: grid; place-items: center; flex-shrink: 0; }}
    .logo-mark span {{ font-family: 'Cinzel', serif; font-size: 17px; font-weight: 700; line-height: 1;
      background: linear-gradient(90deg,#8B6914,#B48A1E,#D4AF37,#F1D77A,#D4AF37,#B48A1E,#8B6914);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
    .logo-copy {{ display: flex; flex-direction: column; gap: 2px; }}
    .logo-name {{ font-family: 'Cinzel', serif; font-size: 16px; font-weight: 700;
      letter-spacing: 0.18em; text-transform: uppercase; color: #E2C05E; line-height: 1; }}
    .logo-sub {{ font-size: 9px; font-weight: 600; letter-spacing: 0.24em;
      text-transform: uppercase; color: #8A8A90; line-height: 1; }}
    .nav-sep {{ color: #2A2A2E; font-size: 14px; }}
    .nav-link {{ color: #8A8A90; font-size: 14px; }}
    .page {{ max-width: 1400px; margin: 0 auto; padding: 48px 32px 80px; }}
    .hero {{ margin-bottom: 40px; }}
    .hero h1 {{ font-size: clamp(28px, 5vw, 48px); font-weight: 800; margin-bottom: 10px; }}
    .hero p {{ color: #8A8A90; font-size: 16px; }}
    .post-list {{ display: flex; flex-direction: column; }}
    .post-row {{ display: flex; align-items: center; gap: 28px;
      padding: 28px 16px; border-bottom: 1px solid rgba(42,42,46,0.8);
      border-radius: 12px; transition: background 0.2s; }}
    .post-row:first-child {{ border-top: 1px solid rgba(42,42,46,0.8); }}
    .post-row:hover {{ background: rgba(20,20,24,0.7); }}
    .post-carousel {{ flex-shrink: 0; width: 240px; }}
    .mini-carousel {{ position: relative; width: 240px; aspect-ratio: 1 / 1;
      border-radius: 14px; overflow: hidden; background: #131315;
      border: 1px solid #2A2A2E; }}
    .slides-track {{ display: flex; height: 100%;
      transition: transform 0.3s ease; will-change: transform; }}
    .slide {{ height: 100%; }}
    .slide a {{ display: block; width: 100%; height: 100%; }}
    .slide img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .nav-btn {{ position: absolute; top: 50%; transform: translateY(-50%);
      background: rgba(13,13,15,0.85); color: #E2C05E;
      border: 1px solid rgba(201,162,42,0.35); border-radius: 8px;
      width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
      cursor: pointer; font-size: 18px; font-weight: 700; line-height: 1;
      backdrop-filter: blur(8px); transition: background 0.2s, opacity 0.2s;
      z-index: 2; opacity: 0; }}
    .mini-carousel:hover .nav-btn {{ opacity: 1; }}
    .nav-btn:hover {{ background: rgba(201,162,42,0.20); }}
    .prev {{ left: 7px; }}
    .next {{ right: 7px; }}
    .dots {{ position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%);
      display: flex; gap: 5px; z-index: 2; }}
    .dot {{ width: 6px; height: 6px; border-radius: 50%; cursor: pointer;
      background: rgba(255,255,255,0.22); transition: background 0.2s; }}
    .dot.active {{ background: #C9A22A; }}
    .slide-counter {{ position: absolute; top: 8px; right: 9px; z-index: 2;
      font-size: 10px; font-weight: 700; color: #E2C05E;
      background: rgba(13,13,15,0.75); padding: 2px 7px; border-radius: 20px;
      backdrop-filter: blur(6px); border: 1px solid rgba(201,162,42,0.22); }}
    .post-content {{ flex: 1; display: flex; flex-direction: column; gap: 10px;
      color: #F0F0EC; padding: 4px 0; min-width: 0; }}
    .post-content:hover .post-title {{ color: #E2C05E; }}
    .card-meta {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
    .tag {{ background: rgba(201,162,42,0.10); color: #E2C05E; font-size: 11px;
      font-weight: 600; padding: 3px 9px; border-radius: 20px;
      border: 1px solid rgba(201,162,42,0.20); }}
    .date {{ color: #5A5A60; font-size: 12px; }}
    .post-title {{ font-size: clamp(17px, 1.8vw, 22px); font-weight: 700;
      line-height: 1.3; color: #F0F0EC; transition: color 0.2s; }}
    .post-desc {{ font-size: 14px; color: #8A8A90; line-height: 1.6; }}
    .read-more {{ display: inline-flex; align-items: center; gap: 5px;
      color: #C9A22A; font-size: 13px; font-weight: 700; margin-top: 2px; }}
    .post-row.no-carousel .post-carousel {{ display: none; }}
    .empty {{ color: #5A5A60; text-align: center; padding: 60px 0; }}
    @media (max-width: 900px) {{
      .page {{ padding: 32px 20px 60px; }}
      .post-carousel {{ width: 200px; }}
      .mini-carousel {{ width: 200px; }}
    }}
    @media (max-width: 640px) {{
      .page {{ padding: 24px 16px 60px; }}
      .post-row {{ flex-direction: column; align-items: flex-start; gap: 14px; padding: 20px 12px; }}
      .post-carousel {{ width: 100%; }}
      .mini-carousel {{ width: 100%; }}
      .nav-btn {{ opacity: 1; }}
      .post-title {{ font-size: 17px; }}
    }}
  </style>
</head>
<body>
  <nav>
    <a href="{SITE_URL}" class="logo">
      <div class="logo-mark"><span>H</span></div>
      <div class="logo-copy">
        <span class="logo-name">HYT</span>
        <span class="logo-sub">Money</span>
      </div>
    </a>
    <span class="nav-sep">/</span>
    <span class="nav-link">Finance Blog</span>
  </nav>
  <main class="page">
    <div class="hero">
      <h1>Finance Insights</h1>
      <p>Daily finance news explained simply for Indian salaried professionals.</p>
    </div>
    <div class="post-list">
      {empty_or_rows}
    </div>
  </main>
  <script>
  (function () {{
    var state = {{}};
    function go(id, n) {{
      var el = document.getElementById(id);
      if (!el) return;
      var slides = el.querySelectorAll('.slide');
      var total = slides.length;
      n = ((n % total) + total) % total;
      state[id] = n;
      el.querySelector('.slides-track').style.transform = 'translateX(-' + (n * (100 / total)) + '%)';
      el.querySelectorAll('.dot').forEach(function (d, i) {{ d.classList.toggle('active', i === n); }});
      var counter = document.getElementById(id + '-counter');
      if (counter) counter.textContent = (n + 1) + ' / ' + total;
    }}
    document.addEventListener('DOMContentLoaded', function () {{
      document.querySelectorAll('.mini-carousel').forEach(function (el) {{
        var id = el.id;
        state[id] = 0;
        var slides = el.querySelectorAll('.slide');
        var total = slides.length;
        var track = el.querySelector('.slides-track');
        if (track && total) {{
          track.style.width = (total * 100) + '%';
          slides.forEach(function (s) {{ s.style.flex = '0 0 ' + (100 / total) + '%'; }});
        }}
        var counter = document.getElementById(id + '-counter');
        if (counter) counter.textContent = '1 / ' + total;
        var prevBtn = el.querySelector('.prev');
        var nextBtn = el.querySelector('.next');
        if (prevBtn) prevBtn.addEventListener('click', function (e) {{ e.preventDefault(); e.stopPropagation(); go(id, (state[id] || 0) - 1); }});
        if (nextBtn) nextBtn.addEventListener('click', function (e) {{ e.preventDefault(); e.stopPropagation(); go(id, (state[id] || 0) + 1); }});
        el.querySelectorAll('.dot').forEach(function (dot, i) {{
          dot.addEventListener('click', function (e) {{ e.preventDefault(); e.stopPropagation(); go(id, i); }});
        }});
      }});
    }});
  }})();
  </script>
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


# ── Carousel generation ───────────────────────────────────────────────────────
# Uses content already produced by Gemini (zero extra AI tokens).
# Playwright renders 4 HTML slides → JPEG 85 quality → carousel.zip.
# Output goes to blog/carousels/<slug>/ which is gitignored — uploaded
# as a GitHub Actions artifact so the repo stays lean.

_CAROUSEL_CSS = """
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,600;0,700;0,800;1,400&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1080px; height: 1080px; overflow: hidden;
    font-family: 'DM Sans', -apple-system, sans-serif;
    background: #131210; color: #F0F0EC;
    -webkit-font-smoothing: antialiased; position: relative;
  }
  .glow { position: absolute; border-radius: 50%; pointer-events: none; }
  /* Top header row */
  .header {
    position: absolute; top: 48px; left: 64px; right: 64px;
    display: flex; align-items: center; justify-content: space-between;
  }
  /* Brand badge — solid box for high legibility */
  .brand-wrap {
    background: rgba(201,162,42,0.12);
    border: 1.5px solid rgba(201,162,42,0.38);
    padding: 8px 20px; border-radius: 12px;
  }
  .brand {
    font-size: 18px; font-weight: 800; letter-spacing: 0.22em; text-transform: uppercase;
    background: linear-gradient(90deg, #C8961A, #EAC94E, #FAF0A8, #EAC94E, #C8961A);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  }
  /* Category pill */
  .pill {
    background: rgba(201,162,42,0.20); border: 1.5px solid rgba(201,162,42,0.55);
    color: #F4DC7A; font-size: 13px; font-weight: 700;
    padding: 8px 20px; border-radius: 999px;
    letter-spacing: 0.08em; text-transform: uppercase;
  }
  /* Content zone — vertically centred between header (148px) and footer (130px) */
  .content-zone {
    position: absolute; top: 148px; bottom: 130px;
    left: 64px; right: 64px;
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    gap: 30px; text-align: center;
  }
  /* Footer row */
  .footer {
    position: absolute; bottom: 46px; left: 64px; right: 64px;
    display: flex; align-items: center; justify-content: space-between;
  }
  .site { font-size: 15px; font-weight: 600; color: #9090A0; letter-spacing: 0.06em; }
  .n    { font-size: 13px; font-weight: 700; color: #808090; letter-spacing: 0.12em; }
  .accent-bar {
    position: absolute; bottom: 0; left: 0; right: 0; height: 5px;
    background: linear-gradient(90deg, #8B6914, #D4AF37, #F1D77A, #6ECFDB, transparent);
  }
  .rule {
    height: 1px; width: 220px;
    background: linear-gradient(90deg, transparent, rgba(201,162,42,0.60), rgba(110,207,219,0.35), transparent);
  }
"""

_SLIDE1_CSS = """
  .glow-top { top: -80px; left: 50%; transform: translateX(-50%);
    width: 760px; height: 480px;
    background: radial-gradient(circle, rgba(201,162,42,0.18) 0%, transparent 70%); }
  /* Watermark quote mark — behind centred content */
  .qmark { position: absolute; top: 50%; left: 36px;
    transform: translateY(-48%);
    font-size: 210px; line-height: 1; font-family: Georgia, serif;
    color: rgba(201,162,42,0.06); pointer-events: none; user-select: none; }
  /* Centred main text */
  .hook {
    font-size: 52px; font-weight: 800; line-height: 1.18;
    letter-spacing: -0.025em; max-width: 920px;
  }
  .sub { font-size: 18px; font-weight: 500; color: #6E6E7A; line-height: 1.45; max-width: 860px; }
"""

_SLIDE_TW_CSS = """
  /* Giant watermark number — centred vertically, pushed right */
  .bg-num { position: absolute; top: 50%; right: 16px;
    transform: translateY(-54%);
    font-size: 330px; font-weight: 800; line-height: 1;
    color: rgba(201,162,42,0.05); letter-spacing: -0.06em; pointer-events: none; user-select: none; }
  /* Point label */
  .num-label {
    font-size: 15px; font-weight: 700;
    color: rgba(201,162,42,0.88);
    letter-spacing: 0.26em; text-transform: uppercase;
  }
  /* Key point text */
  .tw {
    font-size: 48px; font-weight: 800; line-height: 1.22;
    letter-spacing: -0.025em; max-width: 940px;
  }
"""

_SLIDE_CTA_CSS = """
  .glow-c { top: 50%; left: 50%; transform: translate(-50%, -50%);
    width: 860px; height: 680px;
    background: radial-gradient(circle, rgba(201,162,42,0.18) 0%, transparent 70%); }
  .center { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    text-align: center; width: 920px; }
  .big-brand { font-size: 80px; font-weight: 800; letter-spacing: 0.16em;
    background: linear-gradient(90deg, #C8961A, #EAC94E, #FAF0A8, #EAC94E, #C8961A);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    margin-bottom: 24px; }
  .tagline { font-size: 30px; font-weight: 600; color: #8A8A9A; line-height: 1.4; margin-bottom: 54px; }
  .divider-c { height: 1px; width: 400px; margin: 0 auto 54px;
    background: linear-gradient(90deg, transparent, rgba(201,162,42,0.55), rgba(110,207,219,0.35), transparent); }
  .cta-line { font-size: 24px; font-weight: 700; color: #EAC94E;
    letter-spacing: 0.05em; margin-bottom: 16px; }
  .site-line { font-size: 16px; color: #6A6A78; letter-spacing: 0.06em; }
"""


def _e(text: str) -> str:
    return html_lib.escape(str(text))


def _make_slide(extra_css: str, body_inner: str) -> str:
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8"><style>'
        + _CAROUSEL_CSS + extra_css
        + '</style></head><body>'
        + body_inner
        + '</body></html>'
    )


def _slide_hook(title: str, hook: str, tag: str) -> str:
hook_s = (hook[:137] + "…") if len(hook) > 140 else hook
    body = (
        '<div class=”glow glow-top”></div>'
        '<div class=”accent-bar”></div>'
        '<div class=”header”>'
          '<div class=”brand-wrap”><div class=”brand”>HYT MONEY</div></div>'
          '<div class=”pill”>' + _e(tag) + '</div>'
        '</div>'
        '<div class=”qmark”>“</div>'
        '<div class=”content-zone”>'
          '<div class=”hook”>' + _e(hook_s) + '</div>'
          '<div class=”rule”></div>'
          '<div class=”sub”>' + _e(title) + '</div>'
        '</div>'
        '<div class=”footer”>'
          '<div class=”site”>zentraai.in</div>'
          '<div class=”n”>1 / 4</div>'
        '</div>'
    )
    return _make_slide(_SLIDE1_CSS, body)


def _slide_takeaway(takeaway: str, num_str: str, slide_n: int) -> str:
    tw_s = (takeaway[:160] + "…") if len(takeaway) > 163 else takeaway
    body = (
        '<div class="accent-bar"></div>'
        '<div class="header">'
          '<div class="brand-wrap"><div class="brand">HYT MONEY</div></div>'
          '<div class="pill">Key Takeaway</div>'
        '</div>'
        '<div class="bg-num">' + num_str + '</div>'
        '<div class="content-zone">'
          '<div class="num-label">' + num_str + ' &nbsp;|&nbsp; KEY POINT</div>'
          '<div class="tw">' + _e(tw_s) + '</div>'
          '<div class="rule"></div>'
        '</div>'
        '<div class="footer">'
          '<div class="site">zentraai.in</div>'
          '<div class="n">' + str(slide_n) + ' / 4</div>'
        '</div>'
    )
    return _make_slide(_SLIDE_TW_CSS, body)


def _slide_cta() -> str:
    body = (
        '<div class="glow glow-c"></div>'
        '<div class="accent-bar"></div>'
        '<div class="center">'
          '<div class="big-brand">HYT MONEY</div>'
          '<div class="tagline">Your money, understood.</div>'
          '<div class="divider-c"></div>'
          '<div class="cta-line">Free on Android</div>'
          '<div class="site-line">zentraai.in &nbsp;·&nbsp; Finance &nbsp;·&nbsp; Track &nbsp;·&nbsp; Grow</div>'
        '</div>'
        '<div class="footer">'
          '<div class="site">zentraai.in</div>'
          '<div class="n">4 / 4</div>'
        '</div>'
    )
    return _make_slide(_SLIDE_CTA_CSS, body)


def generate_carousels(data: dict, slug: str) -> Path | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[warn] playwright not installed — skipping carousels")
        return None

    import zipfile as _zf

    carousel_dir = BLOG_DIR / "carousels" / slug
    carousel_dir.mkdir(parents=True, exist_ok=True)

    tags   = data.get("tags", [])
    tag    = tags[0].title() if tags else "Finance Insight"
    tws    = data.get("key_takeaways", ["", ""])
    slides = [
        _slide_hook(data["seo_title"], data["hook"], tag),
        _slide_takeaway(tws[0] if len(tws) > 0 else "", "01", 2),
        _slide_takeaway(tws[1] if len(tws) > 1 else "", "02", 3),
        _slide_cta(),
    ]

    names = ["slide-1-hook", "slide-2-point1", "slide-3-point2", "slide-4-cta"]

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1080, "height": 1080})
            for name, html in zip(names, slides):
                page.set_content(html, wait_until="networkidle", timeout=20000)
                page.screenshot(
                    path=str(carousel_dir / f"{name}.jpg"),
                    type="jpeg",
                    quality=85,
                    full_page=False,
                )
            browser.close()
    except Exception as exc:
        print(f"[warn] Playwright render failed: {exc}")
        return None

    # Bundle into a single ZIP for easy download
    zip_path = carousel_dir / "carousel.zip"
    with _zf.ZipFile(zip_path, "w", _zf.ZIP_DEFLATED) as zf:
        for name in names:
            img = carousel_dir / f"{name}.jpg"
            if img.exists():
                zf.write(img, img.name)

    total_kb = sum((carousel_dir / f"{n}.jpg").stat().st_size for n in names
                   if (carousel_dir / f"{n}.jpg").exists()) // 1024
    print(f"[carousel] 4 slides ({total_kb} KB) → {carousel_dir}")
    return carousel_dir


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

        # Generate carousel images first so the post HTML can reference their URLs
        carousel_slug = f"{today}-{slug}"
        carousel_ok   = generate_carousels(data, carousel_slug)

        post_html = build_post_html(
            data, article,
            pub_date_str=datetime.datetime.utcnow().strftime("%B %d, %Y"),
            post_url=post_url,
            carousel_slug=carousel_slug if carousel_ok else None,
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
