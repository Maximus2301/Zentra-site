# MedVault — Product Feature Document
### Version 1.0 | March 2026

---

## 1. Product Vision

**MedVault** is a private, cross-platform health record management platform serving two interconnected markets:

- **B2C** — Individuals and families who need a secure, portable, government-ID-free health vault accessible anywhere in the world.
- **B2B** — Employers in hazardous industries (manufacturing, construction, mining, gig platforms) who need digital occupational health record management for regulatory compliance.

**Core Positioning:**
> "Your health records, your control — from family care to factory floor."

---

## 2. Target Segments

### B2C Segments

| Segment | Profile | Key Need |
|--------|---------|----------|
| Urban families | Middle-income, smartphone users | Manage records for self, elderly parents, children |
| Indian diaspora (NRI) | Abroad but managing family health in India | Remote access, no ABHA dependency |
| Chronic condition patients | Diabetes, hypertension, cardiac | Long-term record continuity across hospitals |
| Health-conscious individuals | Post-COVID awareness | Preventive tracking, easy doctor sharing |

### B2B Segments

| Segment | Example Employers | Regulatory Driver | Worker Count |
|--------|------------------|------------------|-------------|
| Gig platforms | Swiggy, Zomato, Ola, Urban Company | Code on Social Security 2020 | 7.7M now, 23.5M by 2030 |
| Manufacturing / Factories | Auto, textiles, electronics plants | Factories Act 1948, OSH Code 2020 | ~50M |
| Construction | Real estate developers, contractors | BOCW Act 1996 | ~50M |
| Mining | Coal India, private mines | Mines Act 1952 | ~2.4M |
| Chemical / Pharma plants | BASF, Sun Pharma, local units | OSH Code 2020, OSHA standards | ~3M |
| Hazardous white-collar | Hospitals, labs, aviation, radiation facilities | Periodic fitness mandates | ~10M |

---

## 3. Product Architecture

```
MedVault Platform
│
├── Worker App (Android + iOS)          ← Flutter, individual-facing
│   ├── B2C Mode (personal/family)
│   └── B2B Mode (employer-linked)
│
├── Employer Web Dashboard              ← React/Flutter Web
│   ├── Compliance management
│   ├── Workforce health overview
│   └── Reporting & exports
│
├── Backend (Firebase)
│   ├── Firebase Auth (Email + Phone OTP)
│   ├── Cloud Firestore (records, users, orgs)
│   ├── Firebase Storage (documents, images)
│   └── Cloud Functions (alerts, expiry jobs)
│
└── Integrations (Phase 3+)
    ├── ESI portal API
    ├── Insurance provider APIs
    └── HR systems (Darwinbox, Keka, SAP)
```

---

## 4. Feature Specification

---

### MODULE 1 — Authentication & User Management

#### 1.1 User Registration & Login (B2C)
- Email + password registration
- Phone OTP login (for low-literacy blue-collar workers)
- Biometric unlock (fingerprint / face ID) for repeat access
- Guest emergency view (pre-configured, no login required)

#### 1.2 Worker Onboarding (B2B)
- Employee joins via employer-issued QR code or invite link
- Auto-links to employer's organisation on first login
- Single worker profile, dual mode — personal records + employer compliance records are separate vaults
- Worker always owns their personal vault; employer can only view compliance records they are granted access to

#### 1.3 Employer Admin Account
- Organisation registration (company name, GST, industry type)
- Role-based access: Super Admin, HR Manager, Safety Officer, View-only
- Bulk worker invite via CSV upload (name, phone, employee ID)

---

### MODULE 2 — Health Record Management (B2C Core)

#### 2.1 Record Capture
- Camera scan (live capture)
- Gallery image upload
- File upload (PDF, JPG, PNG)
- Manual text entry
- Auto OCR text extraction via Google ML Kit

#### 2.2 Record Types & Categorisation
- Prescriptions
- Lab reports
- Radiology (X-ray, MRI, CT scan)
- Vaccination records
- Insurance documents
- Discharge summaries
- Fitness / medical certificates
- Occupational exposure logs *(new — B2B)*

#### 2.3 Record Organisation
- Filter by type, date, doctor, hospital
- Full-text search across OCR-extracted content
- Tag records (e.g., "pre-employment", "annual checkup", "accident")
- Mark records as critical (surfaces in emergency card)

#### 2.4 Offline Access
- All records viewable offline via Hive local storage
- Sync to Firestore when connection resumes
- Offline indicator shown in UI

---

### MODULE 3 — Family Profiles (B2C)

#### 3.1 Multi-Member Management
- Primary user manages profiles for spouse, children, elderly parents
- Per-member record vaults
- Member relationship tagging (self, spouse, child, parent, dependent)
- Up to 6 family members on single account

#### 3.2 Caregiver Access Levels
| Role | Permissions |
|------|------------|
| Owner | Full access, add/delete records |
| Caregiver | View + add records, cannot delete |
| Emergency viewer | View emergency card only, read-only |

---

### MODULE 4 — Emergency Health Card

#### 4.1 Personal Emergency Card
- One-tap access card with: blood group, allergies, critical conditions, emergency contacts, current medications
- Accessible without login via PIN or biometric only
- Shareable as QR code or secure link (time-limited, 24h expiry)
- Designed for paramedic/ER use — large text, high contrast

#### 4.2 Worker Emergency Card (B2B)
- Includes employer name, employee ID, ESI number
- Lists occupational exposures (chemicals, radiation) relevant to treatment
- QR code printed on worker ID card (generated by employer dashboard)
- Hospital scans QR, gets read-only emergency view — no app install required

---

### MODULE 5 — Occupational Health Compliance (B2B Core)

#### 5.1 Medical Certificate Management
- Worker uploads fitness certificate (pre-employment, annual, post-illness)
- Certificate type tagging: pre-employment / periodic / return-to-work / fitness-for-hazardous-duty
- Expiry date extraction via OCR or manual entry
- Status per worker: Valid / Expiring Soon (30-day alert) / Expired

#### 5.2 Employer Compliance Dashboard
- Real-time workforce compliance overview
  - Total workers enrolled
  - % with valid medical certificates
  - Workers with expiring certificates (next 30/60/90 days)
  - Workers with expired certificates (flagged, action required)
- Filter by department, site, job role, certificate type
- Export compliance report as PDF or Excel

#### 5.3 Automated Alerts
- Push notification to worker: "Your fitness certificate expires in 30 days"
- Email alert to HR manager: weekly compliance digest
- Escalation alert to Safety Officer: worker with expired certificate still active

#### 5.4 Periodic Medical Examination Tracking
- Schedule periodic medical exams per regulatory requirement
  - Factories Act: annual for hazardous processes
  - Mines Act: pre-employment + every 2 years
  - BOCW: as per state rules
- Track exam completion status per worker
- Reminder workflow: notify worker → notify HR → escalate

#### 5.5 Occupational Exposure Log
- Worker logs or employer records:
  - Exposure type (chemical, radiation, dust, noise, biological)
  - Substance/agent name
  - Duration and intensity (low/medium/high)
  - Date and location
- Cumulative exposure tracking with threshold alerts
  - e.g., radiation dose tracker: alert when approaching permissible annual limit
- Lifetime exposure summary — portable with the worker across employers

---

### MODULE 6 — Record Sharing & Portability

#### 6.1 Secure Sharing (B2C)
- Share specific records with a doctor via time-limited secure link (24h / 72h / 7 days)
- QR code share for in-clinic use
- Share entire family member's record set for specialist referral
- Revoke access any time

#### 6.2 Claim Package Export (B2B)
- Worker generates ESI/insurance claim package: injury record + treatment records + employer certificate
- Single PDF bundle, digitally assembled
- Reduces claim rejection due to incomplete documentation

#### 6.3 Inter-Employer Record Transfer
- When worker changes jobs, transfers occupational health records to new employer
- Worker controls transfer — employer cannot pull records without worker consent
- Audit log of all record accesses

---

### MODULE 7 — AI-Powered Insights (Premium)

#### 7.1 Record Summarisation
- AI summary of OCR-extracted text from reports and prescriptions
- Plain-language explanation (avoid medical jargon)
- Key values highlighted: abnormal lab values flagged in red

#### 7.2 Health Trend Tracking
- Plot lab values over time (haemoglobin, blood sugar, creatinine, etc.)
- Auto-detected from OCR text across multiple reports
- Visual chart with normal range overlay

#### 7.3 Medication Timeline
- Extract medications from prescriptions via OCR
- Build timeline of medications taken over years
- Alert for potential duplications or contradictions (advisory only, not diagnostic)

#### 7.4 Compliance Risk Score (B2B)
- Per-worker occupational health risk score based on:
  - Exposure log history
  - Medical certificate validity
  - Reported incidents
- Aggregated site-level risk score for Safety Officers
- Input for insurance premium negotiation

---

### MODULE 8 — Notifications & Reminders

| Trigger | Recipient | Channel |
|--------|----------|---------|
| Medical certificate expiring in 30 days | Worker | Push + SMS |
| Certificate expired | Worker + HR Manager | Push + Email |
| Periodic medical exam due | Worker | Push |
| Radiation/exposure threshold approaching | Worker + Safety Officer | Push + Email |
| Shared record link expiring | Record owner | Push |
| New record added to family member | Caregiver | Push |
| Weekly compliance digest | HR Manager | Email |

---

### MODULE 9 — Privacy, Security & Compliance

#### 9.1 Data Privacy
- Worker personal vault is never accessible to employer without explicit consent
- Employer compliance vault is limited to compliance records only
- Full audit log: who accessed what record, when
- Worker can revoke employer access at any time (data portability under DPDP Act 2023)

#### 9.2 Consent Framework
- Granular consent per record type and per accessor
- Consent stored immutably in Firestore with timestamp
- DPDP Act 2023 compliant consent collection and withdrawal flows

#### 9.3 Data Security
- All records encrypted at rest (Firebase Storage AES-256)
- TLS in transit
- Firestore security rules: users can only read/write their own records
- Employer dashboard access restricted by organisation-scoped Firestore rules

#### 9.4 Data Residency
- Firebase project deployed in asia-south1 (Mumbai) region
- Data stays within India for Indian clients
- Configurable region for NRI/international clients

---

## 5. Pricing Model

### B2C

| Plan | Price | Features |
|------|-------|---------|
| Free | ₹0 | 1 user, 20 records, basic storage |
| Family | ₹99/month or ₹799/year | 6 family members, unlimited records, offline access |
| Premium | ₹199/month or ₹1,599/year | Family + AI insights, health trends, priority support |

### B2B (Per Seat, Billed Annually)

| Plan | Price | Features |
|------|-------|---------|
| Starter | ₹50/worker/month | Up to 100 workers, compliance dashboard, certificate tracking |
| Growth | ₹75/worker/month | Up to 1,000 workers, exposure logs, automated alerts, claim export |
| Enterprise | Custom | 1,000+ workers, white-label, HR system integration, dedicated support |

> Minimum contract: 50 seats. Annual billing with quarterly review.

**Example Revenue:**
- 5 factories × 500 workers × ₹75/month = **₹18.75L/month ARR** at Growth tier
- 10 gig platform partnerships × 10,000 workers × ₹50/month = **₹50L/month ARR** at Starter tier

---

## 6. Phased Roadmap

### Phase 1 — Foundation (Months 1–3)
**Goal: Working B2C app, initial users**
- [x] Firebase Auth (email/password)
- [x] Firestore record storage
- [x] OCR via ML Kit
- [x] Record categories (Prescription, Lab Report)
- [ ] Offline access (Hive)
- [ ] Emergency health card
- [ ] Family profiles (up to 3 members)
- [ ] Secure record sharing (time-limited link)

### Phase 2 — B2B MVP (Months 4–6)
**Goal: 2–3 pilot employer clients**
- [ ] Employer organisation setup
- [ ] Worker B2B onboarding (QR code invite)
- [ ] Medical certificate tracking + expiry alerts
- [ ] Basic compliance dashboard (web)
- [ ] Worker emergency card (QR, employer-linked)
- [ ] Compliance report export (PDF)
- [ ] Phone OTP login (for low-literacy workers)

### Phase 3 — Growth (Months 7–12)
**Goal: Paid B2B clients, premium B2C tier**
- [ ] Occupational exposure log module
- [ ] AI record summarisation (premium)
- [ ] Health trend charts
- [ ] ESI/insurance claim package export
- [ ] Bulk worker CSV onboarding
- [ ] Automated alert workflows (push + email)
- [ ] Inter-employer record transfer
- [ ] Gig platform partnership integration

### Phase 4 — Scale (Year 2)
**Goal: Enterprise contracts, API ecosystem**
- [ ] HR system integrations (Darwinbox, Keka, SAP)
- [ ] White-label app for enterprise clients
- [ ] Compliance risk score (AI-driven)
- [ ] Multi-region data residency
- [ ] ABDM integration (optional, additive)
- [ ] International expansion (UAE, UK NRI corridor)

---

## 7. Competitive Differentiation Summary

| Dimension | Health-e | Eka Care | MedVault |
|-----------|---------|---------|---------|
| ABHA/Govt ID required | Yes | Optional | No |
| Works globally | No | No | Yes |
| B2B occupational health | No | No | **Yes** |
| Gig worker compliance | No | No | **Yes** |
| Offline access | No | Partial | **Yes** |
| Family management | Basic | Basic | **Full caregiver roles** |
| Exposure log tracking | No | No | **Yes** |
| Emergency card (no login) | No | No | **Yes** |
| Monetisation | Freemium (weak) | Freemium | B2B SaaS + B2C premium |
| Regulatory dependency | High (NHA/ABDM) | Medium | **Low** |

---

## 8. Key Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Code on Social Security enforcement delays | Delays gig platform B2B | Phase 1 focuses on factory/construction (already regulated) |
| Long B2B sales cycles | Slow revenue | Offer 3-month free pilot to first 5 clients |
| Data privacy concerns from workers | Low adoption | Worker-controlled consent, employer cannot access personal vault |
| Competition from ESI portal digitisation | Commoditises compliance | Add AI insights and portability — govt apps won't do this |
| DPDP Act compliance cost | Legal overhead | Build consent framework in Phase 1, not retrofitted later |

---

*Document Version: 1.0*
*Last Updated: March 2026*
*Product: MedVault*
