# Zantra Website — CLAUDE.md

## Project Overview
Static website for the **Zantra** brand, hosted on **GitHub Pages** at `https://zentraai.in`.
This is a pure HTML/CSS single-page site — no build step, no framework, no JS dependencies.

## File Structure
```
zantra-site/
├── index.html        # Main landing page
├── CNAME             # GitHub Pages custom domain (zentraai.in)
├── CLAUDE.md         # This file
└── privacy/
    └── index.html    # Privacy policy page
```

## Design System
- **Font**: Inter (Google Fonts)
- **Theme**: Dark — background `#080810`, surface `#10101C`
- **Primary accent**: `#7B6FF0` (purple)
- **Secondary accent**: `#4ECDC4` (teal)
- **Gold**: `#F5C542` (used for "coming soon" status)
- **Text**: `#F0F0FA` | Muted: `#7070A0`
- **Logo**: Inline SVG — stylized Z with purple→teal gradient, 10px border-radius rect

## Brand Architecture
Zantra is a **multi-product brand**. The site reflects this:
- **Zantra Finance** — Live (personal finance tracker, Android)
- **Zantra Health** — Coming Soon (medical records — see MedVault project)
- **Zantra —** — Future (TBD)

Do NOT collapse the brand to a single product. Always maintain the multi-product vision in copy and structure.

## Key Links
- **Domain**: `zentraai.in` (purchased on Namecheap)
- **App package**: `in.zentra.app`
- **Play Store**: `https://play.google.com/store/apps/details?id=in.zentra.app`
- **Contact email**: `hello@zentraai.in`

## Hosting — GitHub Pages
- Repo pushed to GitHub, `main` branch, root `/`
- Custom domain set in repo Settings → Pages
- HTTPS enforced via GitHub Pages
- DNS: 4 × A records on Namecheap pointing to GitHub Pages IPs (`185.199.108–111.153`)
- CNAME record: `www` → `yourusername.github.io`

## Editing Rules
- Keep all CSS inline in `index.html` — no separate stylesheet needed for a single page
- Keep the site dependency-free (no JS frameworks, no npm)
- Maintain mobile responsiveness — test at 375px width minimum
- The phone mockup in the product spotlight is pure CSS — update transaction labels/amounts to reflect real app data when screenshots are available
- Replace Play Store link placeholder once the app is live on the store

## Autonomous Instagram Campaign Agent (ADK 2.0)
- **Directory / Package**: `instagram_adk` (canonical package, symlinked to `adk - content creator` for path compatibility).
- **Architecture**: 7-stage Google ADK 2.0 directed line graph (`Workflow`, `InMemorySessionService`, `Runner`) with Stage 5 Critic loop.
- **System Baseline**: `v1.2.0` (Updated October 20, 2026; Multi-tenant studio, dual-route video generation, social linking, brand DNA).
- **Accounts**: `@workplace_rights_watch`, `@fintech_save_smart`, `@alex_tech_ceo`.
- **Formats & Media**:
  - Static Post (4:5 Portrait + Google Imagen 3 Feed Visual)
  - Interactive Story (9:16 4-Slide Arc + Google Imagen 3 Story Visual)
  - Reel Video (Dual-route: $\le 30$s In-Dashboard 1080x1920 MP4 via FFmpeg vs $> 30$s Google Vids Workspace Blueprint at `vids.new`)
  - Status Card (1:1 Micro Takeaway + Google Imagen 3 Status Graphic)
- **Multi-User History & Security**:
  - Multi-user authentication supporting `admin` (superuser) and creators (`vyantec@gmail.com`).
  - Forced first-time password change (`must_change_password`).
  - Zero-cost JSON session store (`instagram_adk/output/sessions/<user_id>.json`).
  - Admin superuser global audit toggle (`all_users=true`) to view all creator sessions.
- **Social Account Linking**:
  - Instagram Graph API v20.0 (masked token retrieval, handle, business ID, live publishing).
  - YouTube Data API v3 (Vidya Creator Studio, channel ID, API key, category, privacy).
  - Live connection testing ping endpoint (`POST /api/accounts/{id}/connections/test`).
  - Dynamic preview badges (`📷 IG Connected`, `▶️ YT Linked`).
- **Visual Brand DNA Engine**:
  - 6 curated presets (*Investigative Legal*, *FinTech Mint & Gold*, *Cyberpunk Glow*, *Editorial Luxury*, *Vibrant Pop*, *Nordic Minimal*) + *Custom*.
  - 4-color palette, custom icon emoji pills, iconography styles, Google Fonts typography pairings.
  - Live Brand DNA mini-card preview positioned below Reel Video Duration in Creator Studio.
- **Live Endpoints & Deployment**:
  - Google Cloud Run: `https://zentra-instagram-agent-546102264289.asia-south1.run.app`
  - Creator Studio UI: `https://zentraai.in/creator/` (mirrored in `creator/index.html`, `instagram_adk/web/index.html`, `zentra-site/creator/index.html`)
  - Notion Baseline Page ID: `3fd00b72-932a-81c6-bbea-e450a9a21e9c` (Parent: `35400b72-932a-8037-9e19-c675c6fdf8c2`)
- **CLI Commands**:
  - `python run_instagram_agent.py`
  - `python3 instagram_adk/test_server_api.py`
  - `.venv/bin/adk web --port 8000 instagram_adk`

## Personal Brand Engine (HITL Edition)
- **Directory**: `Personal_Brand/`
- **Session Memory**: `Personal_Brand/SESSION_LOG.md`
- **Core Strategy**: Autonomous brand recognition with Human-on-the-Loop review for Personal Brands on Instagram.
- **Key Formats**: 5–7 Slide Authority Carousels (4:5 portrait, saves/shares), Status Cards, Kinetic Reels ($\le 30$s).
- **Architecture**: Modular reuse of `instagram_adk` media engines (`tools/video_composer.py`, `tools/google_media_tools.py`, `nodes/publisher.py`) combined with new Carousel Generator/Renderer and Telegram Mobile Approval Gate (`hitl/telegram_gate.py`).

## Dr. Himani J Bharti — Clinical Authority Website & Personal Brand OS
- **Source Directory**: `Personal_Brand/drhimanibharti/`
- **Live Hosted URL**: `https://zentraai.in/drhimanibharti/` (statically deployed at `drhimanibharti/` in repo root, unlinked from Zantra content)
- **Custom Domain Config**: `https://drhimanibharti.com`
- **Entity**: Dr. Himani J Bharti (Ophthalmologist, Indore, MP)
- **Architecture**:
  - React 18 + Vite 6 + TypeScript + Tailwind CSS Single-Page Application.
  - Centralized single-source-of-truth configuration: `src/config/doctorConfig.ts`.
  - Senior accessibility: Top-bar `Text Size: A / A+` instant font-size scaler.
  - Bilingual patient education: 6 high-intent FAQs with detailed English clinical reasoning and everyday Hinglish summaries.
  - Portable OPD Schedule: Visiting host clinic + upcoming Scheme 140 independent clinic.
  - 100% compliance with National Medical Commission (NMC India — Oct 2026) ethical regulations.
  - Static production build deployed at `drhimanibharti/` with relative asset links (`base: './'`).
  - Multi-brand Instagram carousel generation via `run_drhimani.py` and `Personal_Brand/main.py --brand drhimanibharti`.

## TODO
- [x] Personal Brand: Configure `brand_profile.json` with persona voice, color palette, and pillars
- [x] Personal Brand: Implement `carousel_generator.py` and `carousel_renderer.py` (1080x1350 multi-slide PIL)
- [x] Personal Brand: Wire `hitl/telegram_gate.py` with 1-tap Approve/Regenerate buttons and queue manager
- [x] Personal Brand: End-to-end verified CLI orchestrator (`Personal_Brand/main.py`) with live Telegram push
- [x] Personal Brand: Telegram Persona Onboarding wizard (`/setup`), photo avatar auto-cropper, and `/overview` roadmap (`Personal_Brand/run_bot.py`)
- [x] Personal Brand: Cloud Run Serverless Webhook (`Personal_Brand/Dockerfile`, `webhook_server.py`, `deploy_cloud_run.sh`) with `min-instances=0` scale-to-zero ($0 idle cost)
- [x] Dr. Himani J Bharti: Clinical authority website & brand engine in `Personal_Brand/drhimanibharti/` with NMC compliance, `doctorConfig.ts`, and verified production build
- [ ] Replace Play Store URL with live listing link
- [ ] Add real app screenshots inside phone mockup (or swap mockup for actual screenshot)
- [ ] Update `hello@zentraai.in` once email is configured
- [ ] Add Zantra Health entry once MedVault is ready for public beta
