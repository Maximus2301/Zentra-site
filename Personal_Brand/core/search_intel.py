"""
Zero-Cost SEO, AEO (Answer Engine Optimization) & Profile Search Intelligence.
- Fetches real-world autocomplete search queries ($0.00 via public suggest API)
- Audits & optimizes Instagram Display Name + 150-char Bio for in-app search
- Exports citation-ready AEO Markdown + FAQPage JSON-LD snippets per generated post
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional
import requests
from pydantic import BaseModel, Field

from ..config.settings import BrandSettings, settings
from .llm_client import build_brand_context_block, call_structured_llm

logger = logging.getLogger("personal_brand.search_intel")


def fetch_autocomplete_queries(seed_query: str, max_results: int = 6) -> List[str]:
    """
    Fetches real-world search autocomplete queries from Google Suggest at $0.00.
    Non-blocking: returns empty list on network timeout/error.
    """
    q = (seed_query or "").strip()
    if not q:
        return []

    queries: List[str] = []
    for prefix in (q, f"how to {q}", f"why {q}"):
        try:
            res = requests.get(
                "https://suggestqueries.google.com/complete/search",
                params={"client": "firefox", "q": prefix},
                timeout=3,
            )
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                    for item in data[1]:
                        if isinstance(item, str) and item not in queries:
                            queries.append(item)
                        if len(queries) >= max_results:
                            return queries
        except Exception:
            continue
    return queries[:max_results]


class InstagramBioOptimization(BaseModel):
    optimized_display_name: str = Field(
        ...,
        description="Search-weighted Instagram Name field (<=30 chars ideal, e.g. 'Name | Keyword Niche')",
    )
    optimized_bio: str = Field(
        ...,
        description="High-converting <=150 character bio with target audience, authority proof & CTA",
    )
    primary_search_keywords: List[str] = Field(
        default_factory=list,
        description="5 core keywords this account should rank for in Instagram & Google search",
    )
    why_this_ranks: str = Field(..., description="Brief explanation of SEO/search weight improvements")


def optimize_instagram_bio(brand: Optional[BrandSettings] = None) -> InstagramBioOptimization:
    """Generates an Instagram Search-optimized Display Name and <=150 char Bio."""
    b = brand or settings
    brand_context = build_brand_context_block(b)

    system_instruction = f"""You are an Instagram Search & Profile Conversion Specialist.

{brand_context}

Optimize this creator's Instagram Profile for maximum Instagram Search & Google Indexing visibility:
1. `optimized_display_name`: MUST stay compact (<=35 chars) and pair the creator's name with their #1 searchable niche/role keyword (and city if local), because Instagram's Name field carries the highest search ranking weight.
2. `optimized_bio`: Strictly <=150 characters across 3 crisp lines: (Line 1: Who you help + niche keyword; Line 2: Credibility/proof; Line 3: Actionable CTA).
3. Respect any compliance or ethical rules in the profile (e.g. NMC medical guidelines if clinical).
"""

    return call_structured_llm(
        prompt="Generate the search-optimized Instagram Display Name, <=150 char Bio, and top 5 search keywords.",
        system_instruction=system_instruction,
        response_schema=InstagramBioOptimization,
        temperature=0.5,
    )


def export_aeo_snippet(
    topic: str,
    aeo_question: str,
    aeo_direct_answer: str,
    primary_keyword: str,
    caption: str,
    hashtags: List[str],
    output_dir: Path,
    brand: Optional[BrandSettings] = None,
) -> Path:
    """
    Exports a citation-ready AEO Markdown + FAQPage JSON-LD snippet alongside the social post
    so content can also be mirrored on a personal site / blog for Google & AI Overviews.
    """
    b = brand or settings
    question = aeo_question or f"What should you know about {topic}?"
    answer = aeo_direct_answer or caption[:280].replace("\n", " ").strip()

    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": answer,
                },
            }
        ],
        "author": {
            "@type": "Person",
            "name": b.name or "Creator",
            "sameAs": b.creator.get("socials", {}).get("instagram", ""),
        },
    }

    md_content = (
        f"# {topic}\n\n"
        f"**Target Search Keyword:** `{primary_keyword}`  \n"
        f"**AEO Question:** {question}  \n"
        f"**Author:** {b.name or 'Creator'} ({b.handle or '@creator'}) — {b.creator.get('genre') or ''}\n\n"
        f"## Direct Answer\n\n"
        f"{answer}\n\n"
        f"## Full Social Breakdown\n\n"
        f"{caption}\n\n"
        f"**Tags:** {' '.join(hashtags)}\n\n"
        f"## Structured Schema (JSON-LD)\n\n"
        f"```json\n{json.dumps(faq_ld, indent=2)}\n```\n"
    )

    out_path = output_dir / "aeo_article.md"
    out_path.write_text(md_content, encoding="utf-8")
    return out_path
