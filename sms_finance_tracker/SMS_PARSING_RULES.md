# HYT MONEY SMS Parsing Rules

This app currently routes incoming SMS into one of three outcomes:

1. `Transaction`
2. `RecurringPayment`
3. Ignored

## 1. Financial SMS detection

`SmsParser.isFinancialSms(sender, body)` returns `true` when any of these is true:

- The sender matches a known bank/payment sender such as `HDFCBK`, `AXISBK`, `SBIINB`, `PAYTM`, `GPAY`, `PHONEPE`, `CREDCL`, or `AMZPAY`.
- The SMS is recognized as an asset/investment record:
  - EPF passbook balance SMS
  - Fixed deposit liquidation SMS
- The SMS contains both:
  - a money amount like `Rs.`, `INR`, or `₹`
  - a debit or credit keyword

It is rejected before that if it matches promotional or scam patterns.

## 2. Ignored promotional / scam messages

`SmsParser._isPromotionalFinancialSms(body)` rejects these cases:

- Loan promotions:
  - phrases like `easy emi loan`, `personal loan`, `pre-approved loan`
  - plus marketing words like `offer`, `cashback`, `eligible`
  - plus CTA/link patterns like `apply now`, `check eligibility`, or `http`
- Fake withdrawal/claim scams:
  - amount present
  - phrases like `proceed to withdraw`, `claim now`, `winner`, `prize`
  - link present
- Card-benefit marketing:
  - spends-criteria / lounge-access style copy
  - amount present
  - link present

If a message contains real transaction context such as `txn`, `utr`, `ref no`, `upi`, `neft`, `imps`, `rtgs`, `account`, or `card`, it is not treated as promotional by that filter.

## 3. Transaction parsing rule

`SmsParser.parse(sender, body, date)` creates a `Transaction` only if all of these hold:

- `isFinancialSms(...)` is `true`
- It is not an asset/investment SMS handled by a dedicated parser
- It is not a reminder-only SMS

Reminder-only SMS are ignored when they contain bill-due or scheduled-debit context without a payment confirmation keyword.

### Debit keywords

Examples currently matched:

- `debited`
- `deducted`
- `spent`
- `paid`
- `payment`
- `used for`
- `sent`
- `purchase`
- `withdrawn`
- `charged`
- `transfer out`
- `dr`

### Credit keywords

Examples currently matched:

- `credited`
- `received`
- `cr`
- `refund`
- `cashback`
- `cash back`
- `added`
- `deposited`
- `salary`
- `transfer to`
- `reward`

### Extracted transaction fields

When a transaction is created, the parser extracts:

- `amount` from the first `Rs./INR/₹` amount
- `type` from debit-vs-credit keyword order
- `merchant` from `at|to|with|for <merchant>`
- `source` from payment/bank names such as `UPI`, `Google Pay`, `PhonePe`, `Paytm`, `HDFC Bank`
- `accountLast4` from masked account/card patterns

## 4. Planned payment parsing rule

`SmsParser.parsePlannedPayment(sender, body, date)` creates a `RecurringPayment` only if:

- the SMS is not promotional
- the SMS is not an asset/investment message
- the SMS is not a mandate-setup message
- the SMS is not already a confirmed payment message
- the SMS has an amount
- the SMS has bill/reminder context

### Reminder context

Examples currently matched:

- `due date`
- `due on`
- `pay by`
- `pay before`
- `bill generated`
- `statement generated`
- `minimum amount due`
- `total amount due`
- `premium due`
- `emi due`
- `scheduled for debit`
- `will be debited on`
- `auto debit`
- `autopay`
- `standing instruction`
- `ecs debit`
- `nach debit`
- `maintain sufficient funds`

### Excluded planner messages

These are intentionally not converted into planner entries:

- mandate registration/setup confirmations
- autopay activation messages
- standing instruction creation messages
- already-paid or payment-success messages with `txn id`, `ref no`, `payment successful`, `payment received`, and similar confirmation language

### Planner fields extracted

The parser derives:

- `amount`
- `dueDayOfMonth`, normalized into `1..28`
- `category`, such as `Credit Card`, `Utilities`, `Insurance`, `Subscription`, `EMI/Loan`, or fallback `Bill Payment`
- `name`, using credit-card issuer + last4, known billers like `Airtel`/`LIC`, or sender/source fallback
- `frequency`, defaulting to `monthly`, with support for `weekly`, `quarterly`, and `yearly`
- `confidence`, scored from `0.55` to `1.0`

## 5. Asset / investment parsing rule

These messages do not become income/expense transactions. They become `TransactionType.transfer` records with special metadata.

### EPF snapshot

Pattern:

- `passbook balance against <assetId> is Rs <balance>`
- optional `Contribution of Rs <amount>`

Result:

- `recordKind = assetSnapshot`
- `assetType = epf`
- `assetBalance = latest EPF balance`
- `investmentDelta = contribution`, if present

### Fixed deposit liquidation

Pattern:

- `FD No ... liquidated`
- amount present

Result:

- `recordKind = investmentEvent`
- `assetType = fixedDeposit`
- `assetBalance = 0`
- `investmentDelta = -amount`

## 6. SMS sync flow

`SmsService.syncTransactions()` currently processes each SMS in this order:

1. Try `SmsParser.parse(...)`
2. If that returns `null`, try `SmsParser.parsePlannedPayment(...)`
3. Insert transactions into `transactions`
4. Upsert planned payments into `recurring_payments`

This means reminder SMS are intentionally separated from actual cashflow.
