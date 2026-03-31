# MedRecords — Investor Presentation Deck
### *Your Health History, Always With You*

---

## SLIDE 1 — TITLE

# MedRecords
**The Personal Medical Records Vault for Everyone**

> Secure. Searchable. Always accessible.

- Platform: Android & iOS (Flutter)
- Stage: MVP Complete — Pre-Seed
- Date: March 2026

---

## SLIDE 2 — THE PROBLEM

### Managing medical records is broken

**3 painful realities patients face today:**

1. **Scattered records** — prescriptions on paper, lab reports in different clinic portals, old reports lost or damaged
2. **No single source of truth** — patients spend hours hunting for past test results before a new doctor's appointment
3. **No portability** — records locked in hospital systems or physical folders; inaccessible in emergencies

> *"43% of patients cannot produce a complete medication history when visiting a new doctor"*
> — NCBI, 2024

---

## SLIDE 3 — THE SOLUTION

### MedRecords: A secure personal health vault in your pocket

| Pain Point | MedRecords Solution |
|---|---|
| Records are scattered | One app to store all prescriptions and lab reports |
| Paper records are fragile | Scan via camera — OCR extracts & indexes text automatically |
| Locked in hospital portals | Patient-owned cloud storage — accessible anywhere |
| Hard to share with doctors | Organised, categorised records ready to show or share |

**Core insight:** The patient — not the hospital — should own their health data.

---

## SLIDE 4 — PRODUCT OVERVIEW

### What MedRecords does

**Add records in 4 ways:**
- Camera scan (point and shoot)
- Gallery upload
- File upload (PDF, JPG, PNG)
- Manual text entry

**Automatic OCR** — Google ML Kit reads text from scanned documents and makes records searchable

**Organised by category:**
- Prescriptions
- Lab Reports

**Cloud-synced** — records stored securely via Firebase; accessible on any device

---

## SLIDE 5 — PRODUCT SCREENSHOTS (WIREFRAME SUMMARY)

```
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│   HOME SCREEN        │   │   ADD RECORD         │   │   RECORD DETAIL     │
│─────────────────────│   │─────────────────────│   │─────────────────────│
│  [All] [Rx] [Lab]   │   │  Title:  __________  │   │  Blood Test - Jan   │
│                     │   │  Type:   [Rx] [Lab]  │   │  Type: Lab Report   │
│  ┌───────────────┐  │   │                     │   │  Date: 2026-01-15   │
│  │ Blood Test    │  │   │  [Camera] [Gallery]  │   │                     │
│  │ Jan 2026  Lab │  │   │  [File]   [Manual]   │   │  OCR Text:          │
│  └───────────────┘  │   │                     │   │  Haemoglobin 14.2   │
│  ┌───────────────┐  │   │  OCR Text Preview:  │   │  WBC Count 7,400    │
│  │ Dr. Smith Rx  │  │   │  ________________   │   │  Platelets 2.1L     │
│  │ Feb 2026  Rx  │  │   │                     │   │                     │
│  └───────────────┘  │   │      [Save]          │   │      [Delete]       │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
```

---

## SLIDE 6 — MARKET OPPORTUNITY

### A massive, underserved market

| Segment | Size |
|---|---|
| Global digital health market (2025) | $560 Billion |
| Personal health records (PHR) segment | $39 Billion |
| Projected PHR CAGR (2025–2030) | 15.2% |
| Smartphone users in target markets | 4.4 Billion |

**Primary target markets:**
- **India** — 1.4B population, fragmented healthcare, low EHR adoption by clinics
- **Southeast Asia** — Rapid smartphone penetration, minimal hospital digitisation
- **Emerging markets globally** — Paper-heavy healthcare systems

**Why now:**
- Post-COVID patients are more health-conscious and expect digital tools
- Google ML Kit and Firebase make enterprise-grade features accessible at low cost
- Flutter enables one codebase for Android + iOS — faster go-to-market

---

## SLIDE 7 — BUSINESS MODEL

### Multiple monetisation paths

**Phase 1 — Freemium (Launch)**
| Tier | Price | Features |
|---|---|---|
| Free | $0 | Up to 50 records, basic categories |
| Premium | $2.99/month | Unlimited records, search, PDF export, cloud backup |

**Phase 2 — B2B / Platform (12–18 months)**
| Revenue Stream | Description |
|---|---|
| Clinic/hospital API | Clinics pay to push records directly into patient vaults |
| Insurance integrations | Insurers pay for verified, structured health data (with user consent) |
| Telemedicine partnerships | Embed records sharing into telehealth consult flows |

**Phase 3 — Data & AI (24+ months)**
- Anonymised, aggregated health trend insights sold to research institutions
- AI-powered health summaries and alerts for premium subscribers

---

## SLIDE 8 — COMPETITIVE LANDSCAPE

### We sit at a unique intersection

| | MedRecords | Apple Health | Google Health | Hospital Patient Portals |
|---|---|---|---|---|
| Works on Android & iOS | Yes | iOS only | Android focus | Web/App (fragmented) |
| Cross-institution records | Yes | Partial | Partial | No |
| OCR scan of paper records | **Yes** | No | No | No |
| Patient-owned data | **Yes** | Partial | No | No |
| Works in low-connectivity markets | **Yes** | No | No | No |
| No hardware dependency | **Yes** | Requires Apple Watch | No | No |

**Our moat:** OCR-first capture + patient data ownership + cross-platform reach in emerging markets

---

## SLIDE 9 — TECHNOLOGY

### Built on proven, scalable infrastructure

```
┌─────────────────────────────────────────────────────┐
│                    MedRecords Stack                  │
│                                                     │
│  Frontend: Flutter 3.41 (Android + iOS, one codebase) │
│                                                     │
│  Auth:      Firebase Auth (email/password, OAuth ready) │
│  Database:  Cloud Firestore (real-time, offline-ready)  │
│  OCR:       Google ML Kit Text Recognition (on-device)  │
│  Storage:   Firebase Storage (Blaze) / Local path_provider │
│                                                     │
│  Key advantages:                                    │
│  - On-device OCR = no image sent to external server │
│  - Firestore scales to millions of users automatically │
│  - Flutter = 1 team ships Android + iOS             │
└─────────────────────────────────────────────────────┘
```

**Security highlights:**
- Per-user Firestore security rules (data isolated by UID)
- Firebase Auth with industry-standard JWT tokens
- On-device OCR processing — sensitive documents never leave the device for text extraction
- HTTPS-only data transit

---

## SLIDE 10 — TRACTION & ROADMAP

### Where we are today

**Completed (MVP):**
- Full Flutter app with 11 source modules
- Firebase Auth, Firestore, and ML Kit OCR integrated
- Camera scan, file upload, manual entry flows
- Record browsing with category tabs
- Build-ready for Android (APK) and iOS

**Roadmap:**

| Quarter | Milestone |
|---|---|
| Q2 2026 | Public beta launch (Android Play Store) |
| Q2 2026 | iOS App Store submission |
| Q3 2026 | Search & filter functionality |
| Q3 2026 | PDF export & sharing |
| Q3 2026 | 1,000 beta users, feedback loop |
| Q4 2026 | Premium subscription launch |
| Q1 2027 | Clinic API pilot (B2B) |
| Q2 2027 | Series A fundraise |

---

## SLIDE 11 — THE ASK

### Pre-Seed Round: $250,000

**Use of funds:**

| Allocation | % | Amount | Purpose |
|---|---|---|---|
| Engineering | 40% | $100,000 | 2 Flutter/backend engineers for 12 months |
| Growth & Marketing | 25% | $62,500 | User acquisition in India & SEA |
| Infrastructure | 10% | $25,000 | Firebase Blaze + storage scaling |
| Product & Design | 15% | $37,500 | UX research, UI polish, accessibility |
| Legal & Compliance | 10% | $25,000 | DPDP Act (India), GDPR alignment, incorporation |

**In return:**
- 8–12% equity (negotiable based on valuation discussion)
- Investor board observer seat available

**Target metrics by month 12:**
- 10,000 active users
- $5,000 MRR from premium subscriptions
- Signed LOI with 1 clinic/hospital partner

---

## SLIDE 12 — WHY NOW, WHY US

### The case for investing today

**Why now:**
- India's Digital Health Mission (ABDM) is pushing health digitisation but leaves personal record ownership unsolved
- Smartphone-first users in emerging markets have no incumbent to displace
- Firebase + Flutter reduce infra and development costs by 60% vs. 5 years ago

**Why us:**
- Deep understanding of the user pain — built by people who've experienced fragmented health records firsthand
- Full MVP shipped and ready to test — no vaporware
- Technology choices optimise for scale (Firestore) and privacy (on-device OCR)
- Cross-platform from day one — Android + iOS with a single engineering team

---

## SLIDE 13 — CLOSING

# MedRecords

**Your health history — secure, searchable, always with you.**

> We're building the personal health data layer that 4 billion smartphone users in emerging markets don't yet have.

---

**Contact:**
- App: MedRecords (Firebase Project: `medrecords2026`)
- Stage: Pre-Seed | MVP Complete
- Deck version: March 2026

---
*This document contains forward-looking statements and projections for discussion purposes only.*
