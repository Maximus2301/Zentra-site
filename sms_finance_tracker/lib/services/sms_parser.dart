import '../models/recurring_payment.dart';
import '../models/transaction.dart';
import 'category_service.dart';

class SmsParser {
  static const List<String> _financialSenders = [
    'HDFCBK',
    'SBIINB',
    'ICICIB',
    'AXISBK',
    'KOTAKB',
    'PNBSMS',
    'BOIIND',
    'CANBNK',
    'INDBNK',
    'UCOBNK',
    'YESBNK',
    'RBLBNK',
    'FEDERL',
    'DCBBNK',
    'PAYTM',
    'PYTMBN',
    'GPAY',
    'PHONEPE',
    'CREDCL',
    'AMZPAY',
    'CASHFR',
    'RAZRPY',
  ];

  static final RegExp _amountRegex = RegExp(
    r'(?:Rs\.?|INR|₹)\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)',
    caseSensitive: false,
  );

  static final RegExp _debitRegex = RegExp(
    r'\b(?:debited|deducted|spent|paid|payment|used for|sent|purchase|withdrawn|withdrawal|charged|transfer out|dr)\b',
    caseSensitive: false,
  );

  static final RegExp _creditRegex = RegExp(
    r'\b(?:credited|received|cr|refund|cashback|cash back|added|deposited|salary|transfer to|reward)\b',
    caseSensitive: false,
  );

  static final RegExp _accountRegex = RegExp(
    r'(?:a\/c|account|acct|card)\s*(?:no\.?|number|#)?\s*[xX*]+(\d{4})',
    caseSensitive: false,
  );

  static final RegExp _merchantRegex = RegExp(
    r'(?:at|to|with|for)\s+([A-Za-z0-9][A-Za-z0-9\s\-&.]{1,30}?)(?:\s+on|\s+via|\s+using|\s+ref|\.|,|$)',
    caseSensitive: false,
  );

  static final RegExp _maskedSuffixRegex = RegExp(
    r'\b[xX*]{2,}(\d{4})\b',
    caseSensitive: false,
  );

  static final RegExp _selfTransferRegex = RegExp(
    r'\b(?:own\s+a(?:ccount|\/c)|self\s+(?:a(?:ccount|\/c)|transfer)|'
    r'between\s+(?:your\s+)?(?:own\s+)?accounts?|'
    r'to\s+(?:your\s+)?own\s+a(?:\/c|ccount)|'
    r'to\s+self\b|fund\s+transfer\s+to\s+self|'
    r'sweep\s+(?:in|out)|intrabank\s+transfer|'
    r'to\s+your\s+(?:savings|current)\s+a(?:\/c|ccount))\b',
    caseSensitive: false,
  );

  static final RegExp _fdNumberRegex = RegExp(
    r'fd\s*no\.?\s*[xX*]*([A-Za-z0-9]{4,})',
    caseSensitive: false,
  );

  static final RegExp _fdLiquidationRegex = RegExp(
    r'\b(?:pre\s*maturely|prematurely)?\s*liquidated\b',
    caseSensitive: false,
  );

  static final RegExp _epfBalanceRegex = RegExp(
    r'passbook balance against\s+([A-Za-z0-9]+)\s+is\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)',
    caseSensitive: false,
  );

  static final RegExp _epfContributionRegex = RegExp(
    r'contribution of\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)',
    caseSensitive: false,
  );

  static final RegExp _promoLoanRegex = RegExp(
    r'\b(?:easy emi loan|loan approval|pre[- ]approved loan|instant loan|personal loan|home loan|emi loan)\b',
    caseSensitive: false,
  );

  static final RegExp _promoCtaRegex = RegExp(
    r'\b(?:apply now|apply today|check eligibility|know more|limited period|offer ends|tap here|click here|ghar baithe|paayein|payein)\b',
    caseSensitive: false,
  );

  static final RegExp _promoMarketingRegex = RegExp(
    r'\b(?:offer|cashback|reward|approval|eligible)\b',
    caseSensitive: false,
  );

  static final RegExp _claimWithdrawalRegex = RegExp(
    r'\b(?:proceed to withdraw|withdraw during available times|claim now|claim your reward|claim amount|happy visitor|dailycoverage|winner|winning|prize)\b',
    caseSensitive: false,
  );

  static final RegExp _cardBenefitPromoRegex = RegExp(
    r'\b(?:complimentary lounge access|could not be provided|unmet spends criteria|avail benefits|spending in \d+ months|for tnc|terms? and conditions|criteria)\b',
    caseSensitive: false,
  );

  static final RegExp _transactionContextRegex = RegExp(
    r'\b(?:txn|transaction|utr|ref(?: no)?|avl(?:\.| )?bal|available balance|a\/c|account|acct|card|upi|imps|neft|rtgs)\b',
    caseSensitive: false,
  );

  static final RegExp _billNotificationRegex = RegExp(
    r'\b(?:due\s+date|due\s+on|due\s+by|pay\s+by|pay\s+before|pay\s+now|please\s+pay|'
    r'last\s+date(?:\s+of\s+payment)?|bill\s+generated|statement\s+generated|'
    r'bill\s+is\s+due|bill\s+due|payment\s+due|is\s+due\s+for\s+payment|'
    r'due\s+for\s+payment|minimum\s+amount\s+due|total\s+amount\s+due|'
    r'outstanding\s+amount\s+due|amount\s+due|renewal\s+due|premium\s+due|emi\s+due)\b',
    caseSensitive: false,
  );

  static final RegExp _scheduledDebitReminderRegex = RegExp(
    r'\b(?:scheduled\s+for\s+debit|will\s+be\s+debited\s+on|'
    r'auto(?: |-)?debit|autopay|standing\s+instruction|ecs\s+debit|'
    r'nach\s+debit|maintain\s+sufficient\s+funds?)\b',
    caseSensitive: false,
  );

  static final RegExp _mandateSetupRegex = RegExp(
    r'\b(?:mandate\s+(?:registered|created|activated|setup|set up|approved|confirmed|successful)|'
    r'autopay\s+(?:registered|activated|enabled)|'
    r'standing\s+instruction\s+(?:registered|created|activated))\b',
    caseSensitive: false,
  );

  static final RegExp _paymentConfirmedRegex = RegExp(
    r'\b(?:debited|deducted|withdrawn|withdrawal|paid\s+successfully|payment\s+successful|'
    r'payment\s+done|transaction\s+successful|txn\s+successful|successfully\s+paid|'
    r'payment\s+received|received\s+towards|received\s+on\s+your|payment\s+processed|'
    r'upi\s+ref|txn\s+id|txn\s+no|ref(?:erence)?\s+no|transaction\s+id)\b',
    caseSensitive: false,
  );

  // "Payment of INR 5424.02 for Axis Bank Credit Card ... is due" — captures the
  // total bill amount before any "minimum amount due" phrase can interfere.
  static final RegExp _paymentIsDueRegex = RegExp(
    r'\bpayment\s+of\s+(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)\b',
    caseSensitive: false,
  );

  // (?<!minimum\s) blocks "minimum amount due" from matching the bare alternative.
  static final RegExp _totalAmountDueRegex = RegExp(
    r'\b(?:total\s+amount\s+due|outstanding\s+amount\s+due|(?<!minimum\s)amount\s+due|bill\s+amount)\b'
    r'.{0,24}?(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)',
    caseSensitive: false,
  );

  static final RegExp _billAmountRegex = RegExp(
    r'\b(?:bill|statement|emi|premium|subscription|renewal)\b'
    r'.{0,20}?(?:of|for|is|amount(?:ing)?\s+to)?\s*'
    r'(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)',
    caseSensitive: false,
  );

  static final RegExp _minimumAmountDueRegex = RegExp(
    r'\bminimum\s+amount\s+due\b.{0,20}?(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)',
    caseSensitive: false,
  );

  static final RegExp _plannerDueDayRegex = RegExp(
    r'\b(?:due\s+on|due\s+by|pay\s+by|pay\s+before|on\s+or\s+before|'
    r'scheduled\s+for\s+debit\s+on|will\s+be\s+debited\s+on|'
    r'autopay\s+on|auto(?: |-)?debit\s+on)\s*(\d{1,2})\b',
    caseSensitive: false,
  );

  static final List<RegExp> _plannedPaymentNameRegexes = [
    RegExp(
      r'\byour\s+([A-Za-z][A-Za-z0-9&.\- ]{2,30}?)\s+'
      r'(?:bill|statement|emi|premium|subscription|renewal)\b',
      caseSensitive: false,
    ),
    RegExp(
      r'\bfor\s+([A-Za-z][A-Za-z0-9&.\- ]{2,30}?)\s+'
      r'(?:bill|emi|premium|subscription|renewal)\b',
      caseSensitive: false,
    ),
    RegExp(
      r'\b(?:bill|statement|emi|premium|subscription|renewal)\s+for\s+'
      r'([A-Za-z][A-Za-z0-9&.\- ]{2,30})\b',
      caseSensitive: false,
    ),
  ];

  static const Map<String, String> _sourceMap = {
    // Bank names first — must resolve before generic payment-method labels so
    // "Axis Bank Credit Card" → "Axis Bank", not "Credit Card".
    'hdfc': 'HDFC Bank',
    'sbi': 'SBI',
    'icici': 'ICICI Bank',
    'axis': 'Axis Bank',
    'kotak': 'Kotak Bank',
    'yes bank': 'Yes Bank',
    'pnb': 'PNB',
    // Payment apps / methods
    'google pay': 'Google Pay',
    'gpay': 'Google Pay',
    'phonepe': 'PhonePe',
    'paytm': 'Paytm',
    'cred': 'CRED',
    'amazon pay': 'Amazon Pay',
    'bhim': 'BHIM UPI',
    'upi': 'UPI',
    'neft': 'NEFT',
    'imps': 'IMPS',
    'rtgs': 'RTGS',
    'credit card': 'Credit Card',
    'debit card': 'Debit Card',
  };

  static const Map<String, String> _plannedBillerMap = {
    'airtel': 'Airtel',
    'jio': 'Jio',
    'bsnl': 'BSNL',
    'act fiber': 'ACT Fiber',
    'tata power': 'Tata Power',
    'bescom': 'BESCOM',
    'adani electric': 'Adani Electricity',
    'mahanagar gas': 'Mahanagar Gas',
    'indraprastha gas': 'Indraprastha Gas',
    'lic': 'LIC',
    'hdfc life': 'HDFC Life',
    'star health': 'Star Health',
    'niva bupa': 'Niva Bupa',
    'netflix': 'Netflix',
    'spotify': 'Spotify',
    'youtube premium': 'YouTube Premium',
    'amazon prime': 'Amazon Prime',
    'disney': 'Disney+ Hotstar',
  };

  static bool isFinancialSms(String sender, String body) {
    if (_isPromotionalFinancialSms(body)) return false;
    if (_isAssetOrInvestmentSms(body)) return true;

    final upperSender = sender.toUpperCase();
    for (final knownSender in _financialSenders) {
      if (upperSender.contains(knownSender)) return true;
    }
    final hasAmount = _amountRegex.hasMatch(body);
    final hasKeyword =
        _debitRegex.hasMatch(body) || _creditRegex.hasMatch(body);
    return hasAmount && hasKeyword;
  }

  static bool isPlannedPaymentSms(String sender, String body) {
    if (_isPromotionalFinancialSms(body)) return false;
    if (_isAssetOrInvestmentSms(body)) return false;
    if (_mandateSetupRegex.hasMatch(body)) return false;
    if (_paymentConfirmedRegex.hasMatch(body)) return false;

    final hasAmount = _amountRegex.hasMatch(body);
    final hasPlannerContext = _billNotificationRegex.hasMatch(body) ||
        _scheduledDebitReminderRegex.hasMatch(body);
    return hasAmount && hasPlannerContext;
  }

  static Transaction? parse(String sender, String body, DateTime date) {
    if (!isFinancialSms(sender, body)) return null;

    final assetOrInvestmentRecord =
        _parseAssetOrInvestmentRecord(sender, body, date);
    if (assetOrInvestmentRecord != null) return assetOrInvestmentRecord;

    if (_isReminderSmsWithoutConfirmedPayment(body)) return null;

    final amountMatch = _amountRegex.firstMatch(body);
    if (amountMatch == null) return null;

    final amount = _parseAmount(amountMatch.group(1)!);
    if (amount == null || amount <= 0) return null;

    // Self-transfer between own accounts → mark as transfer, not expense/income
    if (_selfTransferRegex.hasMatch(body)) {
      final accountLast4st = _extractAccountLast4(body);
      return Transaction(
        smsAddress: sender,
        amount: amount,
        type: TransactionType.transfer,
        category: 'Self Transfer',
        subcategory: 'Between Accounts',
        merchant: _extractSource('$sender $body').isNotEmpty
            ? _extractSource('$sender $body')
            : sender,
        source: _extractSource('$sender $body'),
        rawSms: body,
        date: date,
        accountLast4: accountLast4st,
      );
    }

    // CC payment confirmation from the credit card company side — skip it
    // BEFORE the debit/credit determination. These SMSes often start with the
    // word "Payment" which wins position over "received", making isCredit=false
    // and defeating any isCredit-gated check. The content test alone is
    // sufficient and safe: the bank-side debit SMS never says "received towards
    // your credit card".
    if (_isCcPaymentReceivedSms(body)) {
      return null;
    }

    final debitMatch = _debitRegex.firstMatch(body);
    final creditMatch = _creditRegex.firstMatch(body);

    bool isCredit;
    if (debitMatch != null && creditMatch != null) {
      isCredit = creditMatch.start < debitMatch.start;
    } else if (creditMatch != null) {
      isCredit = true;
    } else {
      isCredit = false;
    }

    String merchant = '';
    final merchantMatch = _merchantRegex.firstMatch(body);
    if (merchantMatch != null) {
      merchant = merchantMatch.group(1)?.trim() ?? '';
    }

    if (merchant.isEmpty) {
      final bodyLower = body.toLowerCase();
      const knownMerchants = [
        'swiggy', 'zomato', 'amazon', 'flipkart', 'uber', 'ola',
        'netflix', 'spotify', 'dmart', 'bigbasket', 'phonepe',
        'paytm', 'gpay', 'groww', 'zerodha', 'irctc', 'myntra',
      ];
      for (final m in knownMerchants) {
        if (bodyLower.contains(m)) {
          merchant = m[0].toUpperCase() + m.substring(1);
          break;
        }
      }
    }

    final source = _extractSource('$sender $body');

    final accountLast4 = _extractAccountLast4(body);

    final categoryResult =
        CategoryService.classify(merchant, body, isCredit);

    return Transaction(
      smsAddress: sender,
      amount: amount,
      type: isCredit ? TransactionType.income : TransactionType.expense,
      category: categoryResult.category,
      subcategory: categoryResult.subcategory,
      merchant: merchant.isEmpty ? sender : merchant,
      source: source,
      rawSms: body,
      date: date,
      accountLast4: accountLast4,
    );
  }

  static RecurringPayment? parsePlannedPayment(
      String sender, String body, DateTime date) {
    if (!isPlannedPaymentSms(sender, body)) return null;

    final amount = _extractPlannedPaymentAmount(body);
    if (amount == null || amount <= 0) return null;

    final accountLast4 = _extractAccountLast4(body);
    final category = _classifyPlannedPaymentCategory(body);
    final dueDay = _extractPlannedPaymentDueDay(body, date);
    final name =
        _extractPlannedPaymentName(sender, body, category, accountLast4);
    final normalizedKey =
        _buildPlannedPaymentKey(name, category, accountLast4);
    final confidence =
        _computePlannedPaymentConfidence(body, name, accountLast4);
    final snippet =
        body.length > 280 ? '${body.substring(0, 280)}...' : body;

    return RecurringPayment(
      name: name,
      normalizedKey: normalizedKey,
      amount: amount,
      category: category,
      dueDayOfMonth: dueDay,
      frequency: _extractPlannedPaymentFrequency(body),
      isFromSms: true,
      sourceSender: sender,
      sourceSnippet: snippet,
      accountLast4: accountLast4,
      confidence: confidence,
      createdAt: date.millisecondsSinceEpoch,
      lastSeenAt: date.millisecondsSinceEpoch,
    );
  }

  static bool _isPromotionalFinancialSms(String body) {
    final hasAmount = _amountRegex.hasMatch(body);
    final hasLoanOffer = _promoLoanRegex.hasMatch(body);
    final hasCallToAction =
        _promoCtaRegex.hasMatch(body) || body.contains('http');
    final hasMarketingTerms = _promoMarketingRegex.hasMatch(body);
    final hasClaimWithdrawal = _claimWithdrawalRegex.hasMatch(body);
    final hasCardBenefitPromo = _cardBenefitPromoRegex.hasMatch(body);
    final hasTransactionContext = _transactionContextRegex.hasMatch(body);

    final isCardBenefitPromo =
        hasCardBenefitPromo && hasAmount && body.contains('http');
    if (isCardBenefitPromo) return true;

    if (hasTransactionContext) return false;

    final isLoanPromotion =
        hasLoanOffer && hasMarketingTerms && hasCallToAction;
    final isWithdrawalClaimScam =
        hasAmount && hasClaimWithdrawal && body.contains('http');

    return isLoanPromotion || isWithdrawalClaimScam;
  }

  static bool _isReminderSmsWithoutConfirmedPayment(String body) {
    if (_mandateSetupRegex.hasMatch(body)) return true;
    final reminderContext = _billNotificationRegex.hasMatch(body) ||
        _scheduledDebitReminderRegex.hasMatch(body);
    return reminderContext && !_paymentConfirmedRegex.hasMatch(body);
  }

  static bool _isAssetOrInvestmentSms(String body) {
    return (_fdNumberRegex.hasMatch(body) && _fdLiquidationRegex.hasMatch(body)) ||
        _epfBalanceRegex.hasMatch(body);
  }

  static Transaction? _parseAssetOrInvestmentRecord(
      String sender, String body, DateTime date) {
    final fdLiquidation = _parseFixedDepositLiquidation(sender, body, date);
    if (fdLiquidation != null) return fdLiquidation;

    return _parseEpfSnapshot(sender, body, date);
  }

  static Transaction? _parseFixedDepositLiquidation(
      String sender, String body, DateTime date) {
    if (!_fdNumberRegex.hasMatch(body) || !_fdLiquidationRegex.hasMatch(body)) {
      return null;
    }

    final amountMatch = _amountRegex.firstMatch(body);
    final fdMatch = _fdNumberRegex.firstMatch(body);
    if (amountMatch == null || fdMatch == null) return null;

    final amount = _parseAmount(amountMatch.group(1)!);
    if (amount == null || amount <= 0) return null;

    final fdId = fdMatch.group(1);
    return Transaction(
      smsAddress: sender,
      amount: amount,
      type: TransactionType.transfer,
      category: 'Investment',
      subcategory: 'FD Liquidation',
      merchant: 'Fixed Deposit',
      source: _extractSource('$sender $body'),
      rawSms: body,
      date: date,
      recordKind: 'investmentEvent',
      assetType: 'fixedDeposit',
      assetId: fdId,
      assetBalance: 0,
      investmentDelta: -amount,
    );
  }

  static Transaction? _parseEpfSnapshot(
      String sender, String body, DateTime date) {
    final balanceMatch = _epfBalanceRegex.firstMatch(body);
    if (balanceMatch == null) return null;

    final assetId = balanceMatch.group(1);
    final balance = _parseAmount(balanceMatch.group(2)!);
    if (assetId == null || balance == null) return null;

    final contributionMatch = _epfContributionRegex.firstMatch(body);
    final contribution = contributionMatch == null
        ? null
        : _parseAmount(contributionMatch.group(1)!);

    return Transaction(
      smsAddress: sender,
      amount: contribution ?? balance,
      type: TransactionType.transfer,
      category: 'Investment',
      subcategory: contribution != null ? 'EPF Contribution' : 'EPF Balance',
      merchant: 'EPF',
      source: _extractSource('$sender $body'),
      rawSms: body,
      date: date,
      recordKind: 'assetSnapshot',
      assetType: 'epf',
      assetId: assetId,
      assetBalance: balance,
      investmentDelta: contribution,
    );
  }

  static double? _extractPlannedPaymentAmount(String body) {
    final matchers = [
      _paymentIsDueRegex,
      _totalAmountDueRegex,
      _billAmountRegex,
      _minimumAmountDueRegex,
      _amountRegex,
    ];
    for (final regex in matchers) {
      final match = regex.firstMatch(body);
      if (match == null) continue;
      final amount = _parseAmount(match.group(1)!);
      if (amount != null && amount > 0) return amount;
    }
    return null;
  }

  static int _extractPlannedPaymentDueDay(String body, DateTime fallbackDate) {
    final match = _plannerDueDayRegex.firstMatch(body);
    final rawDay = int.tryParse(match?.group(1) ?? '');
    if (rawDay == null) return _normalizeDueDay(fallbackDate.day);
    return _normalizeDueDay(rawDay);
  }

  static int _normalizeDueDay(int day) {
    if (day < 1) return 1;
    if (day > 28) return 28;
    return day;
  }

  static String _classifyPlannedPaymentCategory(String body) {
    final lower = body.toLowerCase();
    if (lower.contains('credit card') ||
        lower.contains('minimum amount due') ||
        lower.contains('total amount due') ||
        lower.contains('statement generated')) {
      return 'Credit Card';
    }
    if (lower.contains('emi') ||
        lower.contains('loan repayment') ||
        lower.contains('installment') ||
        lower.contains('instalment')) {
      return 'EMI/Loan';
    }
    if (lower.contains('insurance') ||
        lower.contains('premium') ||
        lower.contains('policy')) {
      return 'Insurance';
    }
    if (lower.contains('subscription') ||
        lower.contains('renewal') ||
        lower.contains('netflix') ||
        lower.contains('spotify') ||
        lower.contains('youtube premium') ||
        lower.contains('disney')) {
      return 'Subscription';
    }

    final categoryResult = CategoryService.classify('', body, false);
    if (categoryResult.subcategory == 'Utilities') return 'Utilities';
    if (categoryResult.subcategory == 'Insurance') return 'Insurance';
    if (categoryResult.subcategory == 'Subscriptions') return 'Subscription';
    if (categoryResult.subcategory == 'EMI/Loan') return 'EMI/Loan';
    return categoryResult.category == 'Others'
        ? 'Bill Payment'
        : categoryResult.subcategory;
  }

  static PaymentFrequency _extractPlannedPaymentFrequency(String body) {
    final lower = body.toLowerCase();
    if (lower.contains('weekly')) return PaymentFrequency.weekly;
    if (lower.contains('quarterly') || lower.contains('quarter')) {
      return PaymentFrequency.quarterly;
    }
    if (lower.contains('annual') ||
        lower.contains('yearly') ||
        lower.contains('annual premium') ||
        lower.contains('renewal')) {
      return PaymentFrequency.yearly;
    }
    return PaymentFrequency.monthly;
  }

  static String _extractPlannedPaymentName(
      String sender, String body, String category, String? accountLast4) {
    if (category == 'Credit Card') {
      final issuer = _extractSource('$sender $body');
      final bankName =
          issuer.isNotEmpty ? issuer : _sanitizeSenderName(sender);
      if (accountLast4 != null) return '$bankName Card $accountLast4';
      return bankName.isEmpty ? 'Credit Card' : '$bankName Credit Card';
    }

    final lower = body.toLowerCase();
    for (final entry in _plannedBillerMap.entries) {
      if (lower.contains(entry.key)) return entry.value;
    }

    for (final regex in _plannedPaymentNameRegexes) {
      final match = regex.firstMatch(body);
      if (match == null) continue;
      final cleaned = _cleanPlannedPaymentName(match.group(1) ?? '');
      if (cleaned.isNotEmpty) return cleaned;
    }

    final source = _extractSource('$sender $body');
    if (source.isNotEmpty && category != 'Bill Payment') return source;

    final senderName = _sanitizeSenderName(sender);
    if (senderName.isNotEmpty) return senderName;

    return category;
  }

  static String _buildPlannedPaymentKey(
      String name, String category, String? accountLast4) {
    final suffix = accountLast4 ?? '';
    final raw = '${category}_${name}_$suffix'.toLowerCase();
    return raw
        .replaceAll(RegExp(r'[^a-z0-9]+'), '_')
        .replaceAll(RegExp(r'^_+|_+$'), '');
  }

  static double _computePlannedPaymentConfidence(
      String body, String name, String? accountLast4) {
    double score = 0.55;
    if (_totalAmountDueRegex.hasMatch(body) || _billAmountRegex.hasMatch(body)) {
      score += 0.15;
    }
    if (_plannerDueDayRegex.hasMatch(body)) score += 0.10;
    if (accountLast4 != null) score += 0.10;
    if (name.isNotEmpty && name != 'Bill Payment') score += 0.10;
    return score > 1 ? 1 : score;
  }

  static String? _extractAccountLast4(String body) {
    final accountMatch = _accountRegex.firstMatch(body);
    if (accountMatch != null) return accountMatch.group(1);

    final maskedMatch = _maskedSuffixRegex.firstMatch(body);
    return maskedMatch?.group(1);
  }

  static String _cleanPlannedPaymentName(String raw) {
    var cleaned = raw.trim().replaceAll(RegExp(r'\s+'), ' ');
    cleaned = cleaned.replaceFirst(
      RegExp(r'^(?:your|my|our|the)\s+', caseSensitive: false),
      '',
    );
    cleaned = cleaned.replaceFirst(
      RegExp(
        r'\s+(?:bill|statement|emi|premium|subscription|renewal).*$',
        caseSensitive: false,
      ),
      '',
    );
    if (cleaned.isEmpty || RegExp(r'^\d+$').hasMatch(cleaned)) return '';
    return _titleCaseWords(cleaned);
  }

  static String _sanitizeSenderName(String sender) {
    var cleaned = sender.replaceFirst(
      RegExp(r'^[A-Za-z]{2}-'),
      '',
    );
    cleaned = cleaned.replaceAll(RegExp(r'[^A-Za-z0-9 ]+'), ' ').trim();
    if (cleaned.isEmpty) return '';
    if (cleaned == cleaned.toUpperCase() && !cleaned.contains(' ')) {
      return cleaned;
    }
    return _titleCaseWords(cleaned);
  }

  static String _titleCaseWords(String text) {
    return text
        .split(RegExp(r'\s+'))
        .where((part) => part.isNotEmpty)
        .map((part) {
      if (part.length <= 2 && part == part.toUpperCase()) return part;
      final lower = part.toLowerCase();
      return lower[0].toUpperCase() + lower.substring(1);
    }).join(' ');
  }

  static String _extractSource(String text) {
    final lower = text.toLowerCase();
    for (final entry in _sourceMap.entries) {
      if (lower.contains(entry.key)) {
        return entry.value;
      }
    }
    return '';
  }

  static bool _isCcPaymentReceivedSms(String body) {
    final lower = body.toLowerCase();
    // Must mention "credit card" (or "creditcard")
    if (!lower.contains('credit card') && !lower.contains('creditcard')) {
      return false;
    }
    // Cashback / rewards credited to CC are real value — keep them
    if (lower.contains('cashback') || lower.contains('cash back') ||
        lower.contains('reward') || lower.contains('bonus')) {
      return false;
    }
    // Payment confirmation patterns from CC company
    return lower.contains('payment received') ||
        lower.contains('payment accepted') ||
        lower.contains('payment processed') ||
        lower.contains('payment acknowledged') ||
        lower.contains('received towards') ||
        lower.contains('received against') ||
        lower.contains('received for your') ||
        lower.contains('received on your') ||
        lower.contains('credited against') ||
        lower.contains('credited towards');
  }

  static double? _parseAmount(String rawAmount) {
    final normalized = rawAmount.replaceAll(',', '').replaceAll('/-', '').trim();
    return double.tryParse(normalized);
  }
}
