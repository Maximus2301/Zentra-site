# Zantra Website — CLAUDE.md

## Project Overview
Static website for the **Zantra** brand, hosted on **GitHub Pages** at `https://zantraai.in`.
This is a pure HTML/CSS single-page site — no build step, no framework, no JS dependencies.

## File Structure
```
zantra-site/
├── index.html        # Main landing page
├── CNAME             # GitHub Pages custom domain (zantraai.in)
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
- **Domain**: `zantraai.in` (purchased on Namecheap)
- **App package**: `in.zantra.app`
- **Play Store**: `https://play.google.com/store/apps/details?id=in.zantra.app`
- **Contact email**: `hello@zantraai.in`

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

## TODO
- [ ] Replace Play Store URL with live listing link
- [ ] Add real app screenshots inside phone mockup (or swap mockup for actual screenshot)
- [ ] Update `hello@zantraai.in` once email is configured
- [ ] Add Zantra Health entry once MedVault is ready for public beta
