# Zentra — Session Reference

## Project Location
- **Windows path**: `C:\Users\panka\Documents\sms_finance_tracker`
- **WSL path**: `/mnt/c/Users/panka/Documents/sms_finance_tracker`
- **GitHub**: initialized; remote needs to be added by user if not already set
- **PRD**: `PRD.md` in project root (full feature spec)
- **Test Report**: `TEST_REPORT_2026-03-15.md` in project root (107 findings, all resolved)

## Stack
Flutter (Android), SQLite (`sqflite`), `flutter_sms_inbox`, `fl_chart`, `permission_handler`, `intl`, `excel`, `flutter_secure_storage`, `pointycastle`, `pdf`, `printing`, `flutter_local_notifications`, `googleapis`, `http`, `local_auth`, `google_sign_in`, `firebase_core`, `firebase_ai`, `firebase_app_check`, `table_calendar`, `xml`, `webview_flutter`, `cached_network_image`, `timeago`, `share_plus`

---

## DB Version History
| Version | Change |
|---|---|
| 1 | `transactions` table |
| 2 | `user_rules`, `custom_categories` |
| 3 | `account_type_overrides` |
| 4 | `dismissed_verifications` |
| 5 | `deleted INTEGER DEFAULT 0` on `transactions` (soft-delete) |
| 6 | `userModified INTEGER DEFAULT 0` on `transactions` |
| 7 | `account_type_overrides` extended with `nickname`, `closed`, nullable `type` |
| 8 | `bug_reports`, `sms_blocklist` |
| 9 | `users` table |
| 10 | `budgets` table |
| 11 | `is_duplicate INTEGER DEFAULT 0`, `duplicate_of INTEGER` on `transactions` |
| 12 | `pin_salt TEXT` on `users` (PBKDF2 migration) |
| 13 | `user_kept_as_separate INTEGER DEFAULT 0` on `transactions` |
| 14 | Performance indexes: `idx_txn_date`, `idx_txn_deleted_dup`, `idx_txn_category` |
| 15 | `audit_log` table (`id, operation, entity_id, performed_at, details`) |
| 16 | `uuid TEXT` on `users`; `user_profile` table (income/savings tier, top categories) |
| 17 | `gyan_articles` table (Finance Gyan RSS cache) |
| 18 | `gyan_feed_prefs` table (user feed source preferences: source_name PK, enabled INTEGER DEFAULT 1) |
| 19 | `cash_flow REAL` on `transactions` (SMS-parsed balance/outstanding) |
| 20 | `linked_to TEXT` on `account_type_overrides` (debit card → bank account linkage) |
| 21 | `subscriptions` table (plan, started_at, expires_at, source) |
| 22 | `manual_balance REAL`, `manual_balance_at INTEGER` on `account_type_overrides` |
| 23 | `video_articles` table (YouTube video feed cache) |

---

## Architecture Notes

### Authentication (UPDATED — v12 migration)
- PIN hashed with **PBKDF2-HMAC-SHA256** (100,000 iterations, 32-byte output)
- Per-user random 16-byte salt stored in `users.pin_salt`
- Session `userId` stored in **`flutter_secure_storage`** (not SharedPreferences)
- Gemini API key stored in **`flutter_secure_storage`** (not SharedPreferences)
- App lock enabled flag stored in **`flutter_secure_storage`**; **default ON**
- PIN attempt rate limiting: lockout after 3/5/10 failures (30s / 5min / 60min)
- "Forgot PIN?" flow: verifies Google identity → shows PIN reset dialog
- Existing users with old SHA-256 hash will be prompted to re-register on first launch after upgrade

### Security Controls
- `android:allowBackup="false"` — prevents ADB backup extraction
- `FLAG_SECURE` in `MainActivity` — blocks app-switcher screenshots
- `RECEIVE_SMS` permission removed — only `READ_SMS` used
- `applicationId = "in.zentra.app"`
- Backup exports replace `rawSms` with SHA-256 hash (no raw SMS text in exports)
- Bug report exports anonymise SMS content (digits → XXXX)
- Budget notifications use `NotificationVisibility.secret` on lock screen
- Merchant logo fetch disabled by default (opt-in toggle in backup/settings screen)
- Gemini AI consent dialog shown before first AI insights call

### Soft Delete (CRITICAL)
`DbService.deleteTransaction(id)` does `UPDATE SET deleted = 1`, NOT a hard delete.
This keeps the `UNIQUE(rawSms, date)` key in place so `ConflictAlgorithm.ignore` blocks re-import.
**After soft-delete, orphaned duplicates are auto-promoted:**
`UPDATE transactions SET is_duplicate=0, duplicate_of=NULL WHERE duplicate_of=? AND deleted=0`
**All read queries must include `WHERE deleted = 0 AND is_duplicate = 0`**

### Duplicate Detection (UPDATED)
- **Criteria**: same `amount` + same `type` + `ABS(date1-date2) <= 60000ms` + **same `smsAddress`**
- Old bucket method `(date/60000)=(date/60000)` replaced — was causing false positives at minute boundaries
- `user_kept_as_separate = 1` persists "Keep Both" decisions — scanner never re-marks them
- `unmarkDuplicate(id)` sets `is_duplicate=0, duplicate_of=NULL, user_kept_as_separate=1`

### Backup & Restore (UPDATED)
- **Export**: filters `deleted=0 AND is_duplicate=0`; replaces `rawSms` with SHA-256 hash; `dbVersion=17`
- **Restore**: validates field types, ranges, max record count; rejects files > 50 MB
- **After restore**: `Navigator.popUntil(isFirst)` triggers HomeScreen reload
- Audit events logged to `audit_log` table for export/restore/Drive upload/restore

### Budget Alerts (UPDATED)
- `checkBudgetAlerts()` only fires for the **current month** — past months never trigger notifications
- Budget alerts use `NotificationVisibility.secret` on lock screen
- `POST_NOTIFICATIONS` permission requested during `SplashScreen._initialize()`

### UserRulesService (in-memory cache)
Loaded once at `main()` via `await UserRulesService.initialize()`. Holds:
- `_rules`: merchant → {category, subcategory} overrides
- `_customCategories`: name → emoji
- `_knownAccounts`: Set of all seen `accountLast4` values
- `_accountTypeOverrides`: accountLast4 → 'bank'|'creditCard'|'loan'

### Category Classification Order (IMPORTANT)
Food Delivery + Groceries + **Transport** are checked **BEFORE** the P2P Transfer check.
Reason: UPI merchant VPAs like `olacabs@axisbank` would match bank-handle keywords.
**User merchant rules are skipped for credit/refund transactions** — refund/cashback/reversal keywords checked first so credits from known merchants are not booked as expenses.

### TransactionType Enum
```dart
enum TransactionType { expense, income, transfer }
```
- `transfer` = intra-account self-transfer (excluded from income/expense totals AND from `getMonthlyTotals()`)

---

## Packages Added (Phase 2 — 2026-03-17)
`table_calendar: ^3.1.0`, `xml: ^6.5.0`, `webview_flutter: ^4.8.0`, `cached_network_image: ^3.3.1`, `timeago: ^3.6.0`

## Packages Added (Phase 3 — 2026-03-17)
`firebase_core: ^4.5.0`, `firebase_ai: ^3.9.0` (renamed from `firebase_vertexai`)

## Packages Added (2026-03-19 — Firebase AI fix session)
`firebase_app_check: ^0.4.1+5`

---

## Key Files

| File | Purpose |
|---|---|
| `lib/models/transaction.dart` | Model + enum |
| `lib/services/db_service.dart` | All DB ops (v17); indexes; audit log; blocklist CRUD |
| `lib/services/sms_parser.dart` | SMS → Transaction; spam filter; blocklist check; no 'payment' in debitRegex |
| `lib/services/category_service.dart` | Keyword classification; user rules skip refund credits |
| `lib/services/auth_service.dart` | PBKDF2 hashing; rate limiting; secure storage session; resetPin() |
| `lib/services/app_lock_service.dart` | Biometric/PIN lock; default ON; secure storage for enabled flag |
| `lib/services/logo_service.dart` | Merchant logos; opt-in only (default OFF) |
| `lib/services/pdf_service.dart` | PDF report; transfer rows show ↔ not − |
| `lib/services/notification_service.dart` | Budget alerts; secret lock screen visibility; permission requested at splash |
| `lib/services/gdrive_service.dart` | Google Drive backup; separate GoogleSignIn; rawSms hashed in export |
| `lib/services/backup_service.dart` | Local JSON backup; rawSms hashed; validation; audit log |
| `lib/services/bug_report_service.dart` | Bug reports; SMS content anonymised on export |
| `lib/models/gyan_article.dart` | Finance Gyan article model |
| `lib/services/user_profile_service.dart` | Tier profiling: income + savings rate from last 3 months |
| `lib/services/gyan_service.dart` | RSS fetch (Moneycontrol, ET Wealth, Mint), parse, tag, DB cache |
| `lib/services/vertex_ai_service.dart` | Firebase AI via `FirebaseAI.googleAI()`, model `gemini-2.5-flash`; getAdvisorResponse + getSpendingInsights |
| `lib/screens/calendar_screen.dart` | Monthly calendar with expense/income/transfer dots per day |
| `lib/screens/finance_gyan_screen.dart` | Inshorts-style article feed with tag chip bar |
| `lib/screens/gyan_reader_screen.dart` | In-app WebView reader with reader-mode CSS, prev/next article nav |
| `lib/screens/advisor_screen.dart` | Finance Advisor chat; uses VertexAiService; animated thinking indicator; errors logged via debugPrint |
| `lib/screens/assets_screen.dart` | Net Worth view; auto-detects bank/CC/loan from transactions |
| `lib/firebase_options.dart` | Firebase config — project `finance-guru-4804b`, appId for `in.zentra.app` |
| `lib/main.dart` | App entry; Firebase + AppCheck (debug provider) + GoogleSignIn initialized |
| `lib/screens/home_screen.dart` | Dashboard; MonthlyBarChart gets ValueKey(_dataVersion) for forced refresh |
| `lib/screens/budget_screen.dart` | Budget planning; WidgetsBindingObserver refresh on resume; copy-to-months |
| `lib/screens/login_screen.dart` | Auth; friendly error messages; Forgot PIN? flow |
| `lib/screens/onboarding_screen.dart` | 5-page first-install onboarding; sets `onboarding_done` pref; routes to login/home at end |
| `lib/screens/paywall_sheet.dart` | Modal bottom sheet shown when free user tries to access months > 3 months old |
| `lib/services/subscription_service.dart` | Plan tier (free/pro); `canAccessMonth()`; `activatePro()`; reads `subscriptions` table |
| `lib/services/razorpay_service.dart` | Razorpay checkout wrapper; calls Firebase Function; activates Pro on success |
| `functions/index.js` | Firebase Cloud Functions: `createRazorpaySubscription` + `razorpayWebhook` |

---

## SMS Parser Filter Chain
1. Not a financial SMS → `null`
2. OTP / verification code → `null`
3. **Declined/failed transaction** (`_txnDeclinedRegex`) → `null` ← NEW
4. **ACH/NACH mandate** (`_achMandateRegex`) → `null` ← NEW
5. Contains 'spam' → `null`
6. Blocklist pattern match → `null`
7. Bill-due reminder (no confirmed payment keyword) → `null`
8. CC payment received confirmation → `null` (available-limit branch removed)
9. Wallet top-up credit → `null`
10. Extract amount (verb-context regex → fallback)
11. Determine debit/credit (`_debitRegex` no longer contains 'payment')
12. Extract merchant, source, accountLast4
13. Self-transfer detection
14. `CategoryService.classify(merchant, body, isCredit)` — user rules skipped for refund credits

---

## Audit Log
All destructive/export operations write to `audit_log`:
- `delete_transaction` (entity_id = transaction id)
- `export_backup` (details: 'local_json')
- `restore_backup` (details: 'local_json:N')
- `drive_upload`
- `drive_restore`

---

## App Version
`1.0.1+2` (2026-03-17)

## Firebase (UPDATED — 2026-03-19)
- Project: `finance-guru-4804b` (old project `key-autumn-490019-a3` was deleted)
- Package: `in.zentra.app`
- App ID (Android): `1:435114623131:android:0a73c5475ce86afa01463e`
- AI backend: `FirebaseAI.googleAI()` with model `gemini-2.5-flash`
- App Check: `kDebugMode ? AndroidProvider.debug : AndroidProvider.playIntegrity` — automatically switches; debug token still needed in Console for development devices
- `GoogleSignIn.instance.initialize()` called in `main.dart`
- Firebase + AppCheck initialized in `main.dart` before `runApp()`
- Vertex AI API must be enabled in Google Cloud Console for project `finance-guru-4804b`

## google_sign_in v7 API (BREAKING — migrated 2026-03-17)
| Old (v6) | New (v7) |
|---|---|
| `GoogleSignIn(scopes: [...])` | `GoogleSignIn.instance` (singleton; call `.initialize()` first) |
| `.signIn()` | `.authenticate({scopeHint: [...]})` — non-nullable, throws `GoogleSignInException` on cancel |
| `.signInSilently()` | `.attemptLightweightAuthentication()` — returns `Future<Account?>?` (nullable future!) |
| `.currentUser` | No direct getter; use `attemptLightweightAuthentication()` result |
| `.requestScopes([...])` | `account.authorizationClient.authorizeScopes([...])` |
| `account.authHeaders` | `account.authorizationClient.authorizationHeaders([scopes])` |
| `extension.authenticatedClient()` | Build `_GoogleAuthClient(headers)` manually using `http.BaseClient` |

`GDriveService` uses a local `_GoogleAuthClient extends http.BaseClient` that injects authorization headers.
`extension_google_sign_in_as_googleapis_auth` package removed from active use.

## flutter_local_notifications v21 API (BREAKING — migrated 2026-03-17)
- `_plugin.initialize(settings)` → `_plugin.initialize(settings: settings)` (named param)
- `_plugin.show(id, title, body, details)` → `_plugin.show(id: ..., title: ..., body: ..., notificationDetails: ...)` (all named)

## local_auth v3 API (BREAKING — migrated 2026-03-17)
- `AuthenticationOptions` class removed
- `authenticate(options: AuthenticationOptions(...))` → `authenticate(localizedReason: '...')` only

## Kotlin Version Pin
`settings.gradle.kts`: `id("org.jetbrains.kotlin.android") version "2.1.0"` — DO NOT upgrade to 2.2.x.
Kotlin 2.2.20 breaks `share_plus 12.0.1` (internal classes `ShareSuccessManager` / `SharePlusPendingIntent` become unresolved references within the same Kotlin module — compiler regression).
`share_plus: ^12.0.1` is fine; it compiles correctly on Kotlin 2.1.x.

## Monetization Architecture
- Free tier: last 3 months of history only (`SubscriptionService.freeMonthsLimit = 3`)
- Pro plans: ₹99/mo or ₹799/yr (shown in `PaywallSheet`)
- `SubscriptionService` (`lib/services/subscription_service.dart`) — in-memory `_isPro` flag, persisted in `subscriptions` table (v21)
- `PaywallSheet` (`lib/screens/paywall_sheet.dart`) — bottom sheet shown on month navigation lock
- HomeScreen `_prevMonth()` and date-picker gate-check `SubscriptionService.canAccessMonth()`
- Payment integration: see payment plan section below

## Payment Integration — Razorpay (IMPLEMENTED 2026-03-25)

### Architecture
- `functions/index.js` — Firebase Cloud Functions (gen 2, Node 20)
  - `createRazorpaySubscription` (callable): creates Razorpay subscription, returns `subscriptionId` + `keyId`
  - `razorpayWebhook` (HTTP): validates signature; logs events (Firestore sync is a TODO for Phase 2)
- `lib/services/razorpay_service.dart` — Flutter wrapper around `razorpay_flutter`
  - `initialize()` / `dispose()` — call in screen initState/dispose
  - `startSubscription(plan, userDisplayName, callback)` — full checkout flow
  - On success: calls `SubscriptionService.activatePro()` locally
- `lib/screens/paywall_sheet.dart` — now `StatefulWidget`
  - Tappable monthly/yearly plan chips with `AnimatedContainer`
  - Loading state during checkout
  - Calls `RazorpayService.startSubscription()` on upgrade tap
- `functions/.env.example` — template for env vars (copy to `.env`, never commit)
- `.gitignore` updated to exclude `functions/.env` and `functions/node_modules/`

### Setup required before testing (Razorpay)
1. Sign up at razorpay.com → get test API keys
2. Create two subscription plans in Razorpay Dashboard:
   - Monthly: ₹99/month, interval=monthly
   - Yearly: ₹799/year, interval=yearly
3. Copy `functions/.env.example` → `functions/.env`, fill in all values
4. Deploy functions (see setup steps below)

### Firebase Functions deploy steps (run in PowerShell)
```powershell
# Install Firebase CLI if not already installed
npm install -g firebase-tools

# In project root
firebase login
firebase init functions   # select existing project finance-guru-4804b; JavaScript; don't overwrite index.js

cd functions
npm install

# Set secrets (prompted for values)
firebase functions:secrets:set RAZORPAY_KEY_SECRET
firebase functions:secrets:set RAZORPAY_WEBHOOK_SECRET

# Set non-secret config (replace placeholder values)
# Add these to functions/.env file instead (for gen2 functions)

firebase deploy --only functions
```

### Webhook setup (after deploy)
1. Get webhook URL from Firebase Console → Functions → razorpayWebhook
2. Add URL in Razorpay Dashboard → Settings → Webhooks
3. Enable events: `subscription.activated`, `subscription.charged`, `subscription.cancelled`, `subscription.halted`
4. Copy webhook secret → `functions/.env` as `RAZORPAY_WEBHOOK_SECRET`

### Phase 2 — Google Play Billing (for Play Store release)
1. Add `in_app_purchase: ^3.2.0`
2. Set up subscription products in Play Console (monthly + yearly SKUs)
3. Replace RazorpayService with IAP flow
4. Google Play handles renewals automatically

## Known Limitations / Future Work
- Existing users with old SHA-256 PIN hash must re-register once after upgrade (PBKDF2 migration)
- iOS not supported (needs different SMS approach)
- SQLCipher (full DB encryption) not yet implemented — rawSms already hashed in backups; DB at rest on rooted device still readable
- Split bill / shared expense tracking not yet implemented
- Google "G" logo in LoginScreen is a custom painter — should be replaced with official asset before store submission
- App Check should be switched to `AndroidProvider.playIntegrity` before Play Store release
