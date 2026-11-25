# 📋 Personal Brand Engine (HITL Edition) — Session Log & Engineering Memory

---

### 🏷️ Session Metadata
| Property | Value |
| :--- | :--- |
| **Project** | **Personal_Brand** (Autonomous Brand Operating System & HITL Engine) |
| **Date** | November 19, 2026 |
| **Status** | 🟢 **Session Frozen & Memory Persisted** |
| **Target Audience** | Personal Brands (Tech Founders, Executives, Medical Leaders, Creators) |
| **Live Doctor Site** | `https://zentraai.in/drhimanibharti/` (Dr. Himani J Bharti, NMC-compliant) |
| **Lead Platform** | Instagram (Authority 4:5 Carousels, Status Cards, Kinetic 9:16 Reels) |
| **Governance Mode** | **Human-on-the-Loop (HITL)** via Telegram Mobile One-Tap Approval Gate |
| **Base Reusability** | Modular reuse of verified media & video engines from `instagram_adk` |
| **Artifacts Created** | `brand_os_blueprint.md`, `personal_brand_instagram_hitl_spec.md` |

---

## 🎯 Executive Summary & Context

This session initiated the design and foundation of an autonomous tool to build, launch, and continuously grow a **Personal Brand** digitally, with minimal human friction.

### 1. Key Strategic Alignments (User Decisions)
1. **Target Persona**: Personal Brands first (founders, knowledge leaders, creators), expanding to SMBs later.
2. **Governance Model**: Human-on-the-loop (automated generation with a mobile push review gate before publishing).
3. **Primary Initial Channel**: Instagram first, emphasizing:
   - **Multi-Slide Carousels (4:5)**: The primary format for high saves, shares, and authority.
   - **Status / Quote Cards**: High-signal contrarian takes for grid cohesion.
   - **Kinetic Reels ($\le 30$s)**: Top-of-funnel reach.

---

## 🔍 In-Depth Review of `instagram_adk`

### What Was Evaluated
- **Architecture**: 7-stage directed line graph on Google ADK 2.0 (`Workflow`, `Runner`, `InMemorySessionService`).
- **Live Verification**: Ran test pipeline producing 4:5 feed visual, 9:16 story, 30s vertical 1080x1920 MP4 reel via FFmpeg, and Stage 5 Critic check in ~8 seconds.
- **Pre-Existing Persona**: Already contains `@alex_tech_ceo` in `accounts.json` (Tech CEO / Startup Leadership).

### Verdict & Architectural Recommendation
- **Modular Reuse Strategy**: Do NOT rewrite video composition (`video_composer.py`), media tools (`google_media_tools.py`), or Instagram Graph API publishing logic (`publisher.py`).
- **What Must Be Built in `Personal_Brand`**:
  1. **5–7 Slide Carousel Generator & Renderer** (`carousel_generator.py` + `carousel_renderer.py`): Missing in `instagram_adk`. Needs 1080×1350 multi-slide PIL renderer with page counters, swipe cues, and creator avatar.
  2. **Telegram HITL Gate** (`telegram_gate.py`): Replaces passive publishing with mobile interactive push cards (`[Approve]`, `[Regenerate]`, `[Edit]`).
  3. **Creator Brand Profile** (`brand_profile.json`): Clean, decoupled personal brand DNA without legacy corporate disclaimers or multi-user auth overhead.

---

## 📁 Project Structure Defined for `Personal_Brand/`

```
Personal_Brand/
├── README.md                          # Project documentation
├── SESSION_LOG.md                     # This persistence file
├── config/
│   ├── brand_profile.json             # Persona: voice vectors, content pillars, visual palette, headshot
│   └── settings.py                    # Environment variables (IG tokens, Telegram keys)
├── core/
│   ├── dna_engine.py                  # Persona & voice validation
│   ├── ideator.py                     # Pillar-to-topic derivation
│   └── critic.py                      # Authenticity & hook quality scorer
├── generators/
│   ├── carousel_generator.py          # 5-7 slide high-retention narrative builder
│   ├── carousel_renderer.py           # 1080x1350 multi-slide PIL image rasterizer
│   ├── reel_generator.py              # Adapted from instagram_adk video composer
│   └── status_generator.py            # Single-slide quote & contrarian card builder
├── hitl/
│   ├── telegram_gate.py               # python-telegram-bot inline review gate
│   └── queue_manager.py               # PENDING_REVIEW / APPROVED state store
├── publishers/
│   └── instagram_publisher.py         # Meta Graph API carousel container publisher
└── main.py                            # CLI orchestrator: generate -> render -> send for review
```

---

## 🚀 Execution Progress

1. **Step 1: Brand Profile & Configuration** ✅
   - Created [`Personal_Brand/config/brand_profile.json`](file:///home/maximus/projects/llm-lab/Personal_Brand/config/brand_profile.json) with tailored creator identity, voice vectors, contrarian guardrails, 3 core pillars, typography, and a 6-slide carousel formula.
   - Implemented [`Personal_Brand/config/settings.py`](file:///home/maximus/projects/llm-lab/Personal_Brand/config/settings.py) with `.env` and Telegram credential auto-loading.
   - Generated default creator brand avatar in [`Personal_Brand/assets/avatar.png`](file:///home/maximus/projects/llm-lab/Personal_Brand/assets/avatar.png).

2. **Step 2: 4:5 Multi-Slide Carousel Generator & Renderer** ✅
   - Implemented [`generators/carousel_generator.py`](file:///home/maximus/projects/llm-lab/Personal_Brand/generators/carousel_generator.py) with structured Pydantic schemas (`CarouselSlide`, `CarouselDeck`), prompt grounding in brand DNA, and deterministic fallback generator.
   - Implemented [`generators/carousel_renderer.py`](file:///home/maximus/projects/llm-lab/Personal_Brand/generators/carousel_renderer.py) rendering 1080×1350 4:5 portrait PNGs with top progress bars, author pills, category badges, structured content cards, highlight boxes, and action swipe cues.
   - Successfully rendered and verified a sample 6-slide carousel at [`output/sample_carousel/`](file:///home/maximus/projects/llm-lab/Personal_Brand/output/sample_carousel).

3. **Step 3: Telegram HITL Gate & Queue Manager** ✅
   - Implemented [`hitl/queue_manager.py`](file:///home/maximus/projects/llm-lab/Personal_Brand/hitl/queue_manager.py) with structured states (`PENDING_REVIEW`, `APPROVED`, `REGENERATING`, `REJECTED`, `PUBLISHED`).
   - Implemented [`hitl/telegram_gate.py`](file:///home/maximus/projects/llm-lab/Personal_Brand/hitl/telegram_gate.py) with multi-slide photo album uploads (`sendMediaGroup`), formatted caption previews, and interactive inline buttons (`[🚀 Approve & Queue]`, `[🔄 Alternate Hook]`, `[❌ Reject]`).
   - Verified live connection to bot `@Vyantecbot` and delivered test album to Telegram chat.

4. **Step 4: Unified CLI Orchestrator & Live Verification** ✅
   - Implemented [`main.py`](file:///home/maximus/projects/llm-lab/Personal_Brand/main.py) running end-to-end: Topic $\rightarrow$ 6-slide carousel generation $\rightarrow$ 1080×1350 PNG rasterization $\rightarrow$ queue persistence $\rightarrow$ live Telegram mobile push.
   - Live verified with topic `"Architecting Scalable LLM Pipelines"` (Telegram Msg ID 19).

5. **Step 5: Dynamic Persona Studio, Voice Calibration & Granular Editing** ✅
   - Stripped all hardcoded mock content from [`brand_profile.json`](file:///home/maximus/projects/llm-lab/Personal_Brand/config/brand_profile.json) so initial state is clean and unconfigured until onboarding.
   - Implemented [`core/voice_processor.py`](file:///home/maximus/projects/llm-lab/Personal_Brand/core/voice_processor.py) using bundled FFmpeg + local cached `whisper-tiny` for real-time Telegram voice note transcription and cadence/perspective extraction.
   - Registered native Telegram command menu (`setMyCommands`) so the `[/]` shortcut menu is always available on phone/desktop.
   - Added granular profile editor with inline buttons (`[✏️ Name & Handle]`, `[📸 Update Photo]`, `[📝 Bio]`, `[🎙️ Voice DNA]`, `[🏛️ Pillars]`, `[🌐 Socials]`, `[🎨 Theme]`).

6. **Step 6: Google Cloud Run Serverless Webhook ($0 Idle Cost)** ✅
   - Containerized with [`Dockerfile`](file:///home/maximus/projects/llm-lab/Personal_Brand/Dockerfile) (Python 3.11-slim, CPU PyTorch, pre-cached Whisper-tiny model layer, and FFmpeg).
   - Serverless Webhook Server [`webhook_server.py`](file:///home/maximus/projects/llm-lab/Personal_Brand/webhook_server.py) (FastAPI + PTB async update processor with secret token verification).
   - Automated deployment script [`deploy_cloud_run.sh`](file:///home/maximus/projects/llm-lab/Personal_Brand/deploy_cloud_run.sh) configured for `min-instances=0` (scales to zero when idle for $0.00 cost, awakens on incoming Telegram updates).
   - **Live Production URL**: `https://personal-brand-agent-xl4fkzyaha-el.a.run.app`
   - **Telegram Webhook**: Verified live on `@Vyantecbot` (`{"ok":true,"result":true,"description":"Webhook was set"}`). Laptop can be safely closed.

6. **Step 6: Clinical Authority Brand Engine & Portable Website (`drhimanibharti/`)** ✅
   - Initialized doctor authority brand architecture for **Dr. Himani J Bharti (Ophthalmologist, Indore, MP)** at [`Personal_Brand/drhimanibharti/`](file:///home/maximus/projects/llm-lab/Personal_Brand/drhimanibharti).
   - **100% Statutory Compliance with National Medical Commission (NMC India — Oct 2026)**:
     - Strictly prohibited superlatives, promotional claims, discounts, patient testimonials, and commercial urgency timers.
     - Enforced mandatory qualification, state council registration disclosure, and statutory educational disclaimers.
   - **Single-Page Clinical Authority & Portable Doctor Website**:
     - Tech Stack: React 18, TypeScript, Tailwind CSS, Lucide icons, Vite 6 production bundling.
     - Centralized Data Source: [`src/config/doctorConfig.ts`](file:///home/maximus/projects/llm-lab/Personal_Brand/drhimanibharti/src/config/doctorConfig.ts) managing all visiting OPD locations, timings, WhatsApp booking desks, NMC registration, and bilingual FAQs.
     - Senior Accessibility: Instant **Text Size A / A+ toggle** in sticky navigation for patients with blurred/strained vision.
     - Bilingual Patient Education: Interactive FAQ accordion with detailed English clinical reasoning and everyday Hinglish summaries.
     - Production static build verified at [`Personal_Brand/drhimanibharti/dist/`](file:///home/maximus/projects/llm-lab/Personal_Brand/drhimanibharti/dist).
   - **Personal Brand Instagram Engine Integration**:
     - Created [`brand_profile.json`](file:///home/maximus/projects/llm-lab/Personal_Brand/drhimanibharti/brand_profile.json) with 4 ophthalmic content pillars (Cataracts & IOLs, Diabetic Retinopathy, Pediatric Myopia, Glaucoma).
     - Generated high-trust clinical avatar at [`assets/avatar_drhimani.png`](file:///home/maximus/projects/llm-lab/Personal_Brand/drhimanibharti/assets/avatar_drhimani.png).
     - Created one-command runner [`run_drhimani.py`](file:///home/maximus/projects/llm-lab/Personal_Brand/drhimanibharti/run_drhimani.py) generating 1080×1350 4:5 portrait carousels linked with Telegram HITL review gate.

7. **Step 7: Production Live Deployment on `zentraai.in`** ✅
   - Configured portable relative base path (`base: './'`) in [`vite.config.ts`](file:///home/maximus/projects/llm-lab/Personal_Brand/drhimanibharti/vite.config.ts).
   - Statically deployed built web application to [`drhimanibharti/`](file:///home/maximus/projects/llm-lab/drhimanibharti) in repository root.
   - **Zero-Link Isolation**: Maintained complete detachment from existing `zentraai.in` content (`index.html`, `/creator`, `/blog`, `/dashboard` left untouched).
   - Committed (`26c52ee`) and pushed to `origin/main` on `https://github.com/Maximus2301/Zentra-site.git`.
   - Live GitHub Pages deployment verified: **`https://zentraai.in/drhimanibharti/`** (`HTTP/2 200 OK` for HTML, CSS, and JS).


---

## 🔄 Session 2 — Core Realization, $0 Media Engine, SEO/AEO/Meta Reach & Multi-Tenant Hardening (Nov 24–25, 2026)

### 🔍 Scope Audit & Root Causes Resolved
1. **Eliminated Hardcoded Fallback Outputs**: Removed silent AI-agent/ophthalmology boilerplate masks when LLM keys were absent; added explicit `LLMNotConfiguredError`.
2. **Zero-Cost Multi-Provider LLM Brain (`core/llm_client.py`)**: Wired free-tier **Google Gemini (`gemini-3.6-flash`, `gemini-3.8-flash`) $\rightarrow$ Groq (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`)** failover with a 5-minute circuit breaker (zero `ANTHROPIC_API_KEY` dependency).
3. **Full Brand Persona Schema (`config/brand_profile.json`, `config/settings.py`)**: Added `genre`, `language_style`, `target_audience` (`primary_audience`, `pain_points`, `desired_outcomes`), `virality_strategy`, and 6 visual presets (`clean_minimal`, `warm_creator`, `bold_viral`, `dark_terminal`, `editorial_luxury`, `clinical_serene`) + `custom_accent` hex override. Switched default fonts to `DejaVuSans` with emoji sanitization (`sanitize_pil_text`) to eliminate glyph tofu boxes.

### 🎨 All 4 Instagram Formats ($0.00 Media Cost)
- **Status / Quote Cards (`generators/status_generator.py`)**: 1080×1350 tweet-style, contrarian, and quote cards.
- **Static Single-Image Posts (`generators/static_post_generator.py`)**: `$0` designer editorial layouts (`infographic_checklist`, `myth_vs_fact`, `stat_spotlight`) + user photo overlay (`photo_overlay`).
- **Carousels (`generators/carousel_generator.py`, `generators/carousel_renderer.py`)**: Persona-grounded 5–7 slide decks with overflow-safe layout.
- **Kinetic 9:16 Reels (`generators/reel_generator.py`)**: Timed scene scripts + `teleprompter.txt` + free `edge-tts` / `gTTS` / Telegram voiceover + FFmpeg `zoompan` 1080×1920 MP4 compilation.
- **Shared Render Helpers (`generators/render_utils.py`)** & **Unified Pipeline (`core/pipeline.py`)**.

### 🚀 SEO + AEO + Meta Reach Optimization & Q&A Advisor
- **Search Intelligence (`core/search_intel.py`)**: Live Google Suggest autocomplete (`$0.00`), `/bio_seo` (Instagram Display Name + `<=150`-char Search Bio), and `aeo_article.md` (`FAQPage` JSON-LD) export.
- **Multimodal Alignment**: 125-char caption keyword opener, `aeo_direct_answer`, descriptive `alt_text`, DM share triggers, and 3–5 semantic hashtags.
- **5-Axis Critic (`core/critic.py`)**: Scores Hook Power, Persona Fit, Meta Virality, SEO, and AEO + generates suggested pinned comments.
- **Zero-Cost Q&A Advisor (`core/assistant.py`)**: Grounded `/ask` mode + `[💬 Answer as Question]` button on freeform messages.

### 🔐 Multi-Tenant, Multi-Account & Security Hardening
- **Tenant & Licensing Store (`core/tenant_store.py`)**: SQLite (`data/brand_os.db`) + isolated `tenants/<telegram_user_id>/brands/<brand_slug>/` directories supporting `/brands` multi-IG account switching, `/register <user_id>`, `/activate <key>`, admin `/gen_key`, 1-tap approval, and daily per-tenant quota limits.
- **Webhook Hardening (`webhook_server.py`, `deploy_cloud_run.sh`)**: Constant-time `X-Admin-Key` auth on `/api/set-webhook` and `/api/delete-webhook`, fail-closed `TELEGRAM_WEBHOOK_SECRET` verification, sanitized `/health`, cross-tenant IDOR checks on caches/queues, and `html.escape()` on Telegram HTML rendering.
- **Bot SEO Naming Suggestions**: Recommended replacing `@Vyantecbot` via `@BotFather` with `@BrandCraftIGBot` (*BrandCraft AI — Instagram Post & Reel Maker*), `@InstaBrandAIBot`, `@CreatorOSAIBot`, or `@ViralBrandAIBot`.

### ✅ Verified Checks
- End-to-end live generation tested on `drhimanibharti` (`status`: 92/100, `carousel`: 86/100, `reel`: 82/100 MP4, `/bio_seo`, `/ask` multi-turn Q&A).
- Security & multi-tenant suite passed (`verify_security_multitenant.py`, exit code `0`): `/health` PII removal, `403` admin guards, fail-closed webhook secret, license redemption/reuse block, multi-brand isolation, daily quota limit, cross-tenant IDOR blocking, and HTML escaping.

### ⏭️ Remaining Before Paid Pilot on Cloud Run
- [ ] Replace ephemeral local SQLite + `tenants/` disk with persistent cloud backing (Supabase Postgres + GCS/S3) or host on a persistent VM.
- [ ] Implement direct Instagram Graph API / LinkedIn publishers inside `Personal_Brand/publishers/`.
- [ ] Rename `@Vyantecbot` via `@BotFather` and redeploy Cloud Run (`./Personal_Brand/deploy_cloud_run.sh`).

### ☁️ Persistent Cloud Memory & Live Cloud Run Deployment (`v2.0.0`, Nov 25, 2026)
- **GCS Persistent Memory (`core/cloud_memory.py`)**:
  - Provisioned `gs://personal-brand-memory-546102264289` (`asia-south1`).
  - Restores `data/brand_os.db`, `tenants/`, queues, and caches on container cold start (`lifespan` + `TenantStore.__init__`).
  - Syncs WAL-safe SQLite backups (`sqlite3.Connection.backup`), `brand_profile.json`, avatars, uploads, queues, and rendered post assets on every mutation.
- **Scoped Cloud Build (`Personal_Brand/.gcloudignore`)**: Reduced Cloud Build upload archive from 5.3 GiB to `666.7 KiB`.
- **Live Deployment Verified**:
  - Cloud Run Revision: `personal-brand-agent-00002-9tp` (`min-instances=0`, `max-instances=1`, `$0.00` idle cost).
  - Service URL: `https://personal-brand-agent-xl4fkzyaha-el.a.run.app` (`https://personal-brand-agent-546102264289.asia-south1.run.app`).
  - `/health`: `{"status":"healthy","service":"personal-brand-agent","version":"2.0.0"}` (no PII).
  - `/api/delete-webhook` & forged `/webhook/telegram`: `HTTP 403` verified live.
  - GCS state verified: `gs://personal-brand-memory-546102264289/state/data/brand_os.db` present.
  - Telegram Webhook (`@Vyantecbot`): `{"ok":true,"result":true,"description":"Webhook was set"}`.
