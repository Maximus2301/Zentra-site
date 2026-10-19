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

## TODO
- [ ] Replace Play Store URL with live listing link
- [ ] Add real app screenshots inside phone mockup (or swap mockup for actual screenshot)
- [ ] Update `hello@zentraai.in` once email is configured
- [ ] Add Zantra Health entry once MedVault is ready for public beta
