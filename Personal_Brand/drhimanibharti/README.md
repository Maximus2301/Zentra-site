# 🩺 Dr. Himani J Bharti — Clinical Authority Website & Personal Brand OS

Portable doctor brand website and autonomous personal brand content engine for **Dr. Himani J Bharti (Ophthalmologist, Indore, MP)**, engineered for clinical trust, local patient education, and **100% statutory compliance with National Medical Commission (NMC India — Oct 2026) regulations**.

---

## 📌 Executive Architecture & Core Principles

1. **Portable Brand Architecture**:
   - Dr. Himani J Bharti currently consults at a host clinic in Indore and is preparing an independent clinic in **Scheme 140, Indore**.
   - The platform positions **Dr. Himani J Bharti** as the primary, portable medical authority—NOT the host facility.
2. **Centralized Data-Driven Configurability (`src/config/doctorConfig.ts`)**:
   - Practice addresses, visiting OPD schedules, WhatsApp desk numbers, NMC registration numbers, and educational video links reside in one TypeScript config.
   - Updating her practice location or adding a new branch is a single-line edit that updates the entire website instantly.
3. **Strict NMC Ethical Compliance (Oct 2026 Regulations)**:
   - 🚫 **No Superlatives**: No claims like *"Best Eye Doctor"* or *"Top Surgeon"*. Factual, academic, reassuring tone throughout.
   - 🚫 **No Patient Testimonials or Star Ratings**: Replaced by verified academic qualifications, clinical focus areas, and educational guides.
   - 🚫 **No Commercial Offers or Urgency Timers**: No discount coupons or *"free checkup"* banners.
   - ⚖️ **Mandatory Credential & Registration Disclosures**: Qualifications and MP Medical Council / NMC registration displayed prominently across Hero, About, and Footer sections.
4. **Senior & Accessibility-First UX**:
   - Deep Clinical Navy (`#1B365D`) & Calming Teal (`#0D9488`) on warm alabaster (`#F8FAFC`).
   - High-contrast, large-base typography (Plus Jakarta Sans).
   - Instant **Text Size: A / A+ toggle** in the sticky header for patients with blurry or fatigued vision.
   - Bilingual FAQ accordion (English + Hinglish everyday summaries).

---

## 📁 Directory Structure

```
Personal_Brand/drhimanibharti/
├── brand_profile.json          # Personal brand DNA, clinical voice vectors, & Instagram specs
├── run_drhimani.py             # One-command CLI to generate 4:5 carousels & push to Telegram HITL gate
├── package.json                # React 18, Vite 6, Tailwind CSS, Lucide icons
├── tsconfig.json               # Strict TypeScript configuration
├── vite.config.ts              # Vite production bundler
├── tailwind.config.js          # Clinical navy & teal color system
├── postcss.config.js           # PostCSS autoprefixer
├── index.html                  # SEO metadata, OpenGraph, & Schema.org Physician JSON-LD
├── src/
│   ├── config/
│   │   └── doctorConfig.ts     # ⭐ Centralized single source of truth for all data & content
│   ├── components/
│   │   ├── Navbar.tsx          # Sticky nav with A/A+ font size toggle & WhatsApp desk CTA
│   │   ├── Hero.tsx            # Asymmetric clinical authority hero with doctor avatar & status
│   │   ├── ClinicalFocus.tsx   # 6 core non-promotional ophthalmic focus areas
│   │   ├── ConsultationSchedule.tsx # Portable visiting OPD schedule with WhatsApp & Maps
│   │   ├── AboutSection.tsx    # Academic credibility, verified degrees, & consultation values
│   │   ├── PatientEducation.tsx# Bilingual FAQ accordion (English + Hinglish) & video shelf
│   │   ├── ReferringPhysicians.tsx  # B2B liaison strip for diabetologists & optometrists
│   │   ├── Footer.tsx          # NMC statutory disclosure, registration number, & disclaimer
│   │   └── VideoModal.tsx      # Accessible educational YouTube video player modal
│   ├── App.tsx                 # Root application controller
│   ├── main.tsx                # React DOM bootstrap
│   └── index.css               # Tailwind directives & accessibility font scaling
├── assets/
│   └── avatar_drhimani.png     # Rendered doctor brand avatar for carousels
└── dist/                       # ⭐ Pre-built production static website (ready for cPanel/Vercel)
```

---

## 🚀 Website Quick Start

### 1. Run Local Development Server
```bash
cd Personal_Brand/drhimanibharti
npm run dev
# Server starts at http://localhost:3000
```

### 2. Build for Production
```bash
npm run build
# Compiles into optimized static files in ./dist
```

### 3. Deploy to Hosting (Namecheap / cPanel / GitHub Pages / Vercel)
- The entire application compiles to static HTML/CSS/JS in `Personal_Brand/drhimanibharti/dist/`.
- Upload the contents of `dist/` directly to your public web directory (e.g. `public_html` on Namecheap cPanel) or deploy via Vercel / Cloudflare Pages.

---

## ⚙️ Updating Doctor Details & Practice Locations

Open [`src/config/doctorConfig.ts`](file:///home/maximus/projects/llm-lab/Personal_Brand/drhimanibharti/src/config/doctorConfig.ts) to update:

| Parameter | Location in `doctorConfig.ts` |
| :--- | :--- |
| **NMC Registration Number** | `identity.registrationNumber` |
| **Exact Degrees & Qualifications** | `identity.degrees`, `identity.degreeNote` |
| **WhatsApp Desk Number** | `communication.whatsappDeskNumber` |
| **Visiting OPD Timings** | `practiceLocations[0].timings` |
| **Host Clinic Address** | `practiceLocations[0].fullAddress` |
| **Upcoming Scheme 140 Address** | `practiceLocations[1].fullAddress` |
| **YouTube Educational Videos** | `educationalVideos` |
| **Patient FAQs (English/Hinglish)**| `faqs` |

---

## 📱 Generating Instagram Educational Carousels

You can generate 6-slide authority Instagram carousels (1080×1350 4:5 portrait) grounded in Dr. Himani J Bharti's clinical brand profile and push them to your mobile Telegram review gate:

```bash
# 1. Generate, render 1080x1350 PNG slides, and push to Telegram bot for review
python run_drhimani.py --topic "Choosing Between Monofocal and Multifocal IOLs"

# 2. Generate and wait for mobile one-tap approval in the terminal
python run_drhimani.py --topic "When Is Cataract Surgery Really Needed?" --wait

# 3. Render offline without Telegram push
python run_drhimani.py --no-telegram --topic "Why Diabetics Need Annual Dilated Retina Exams"
```

Rendered carousel slides are saved to `Personal_Brand/output/post_<timestamp>_<topic>/`.

---

## ⚖️ NMC India Statutory Compliance Checklist

- [x] **Section 1**: Factual qualifications & registration displayed above the fold.
- [x] **Section 2**: Purely clinical, diagnostic, and medical focus (no promotional claims).
- [x] **Section 3**: Portable visiting OPD schedule with direct patient desk access.
- [x] **Section 4**: Academic residency and medical council registration disclosure.
- [x] **Section 5**: Evidence-based bilingual health literacy with Hinglish translations.
- [x] **Section 6**: Ethical peer co-management with diabetologists and optometrists.
- [x] **Section 7**: Prominent medical disclaimer and National Medical Commission compliance tag.
