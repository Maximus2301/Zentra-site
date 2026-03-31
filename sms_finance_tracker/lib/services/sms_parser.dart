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
    r'\b(?:debited|deducted|spent|paid|payment|used for|sent|purchase|withdrawn|charged|transfer out|dr)\b',
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

  static const Map<String, String> _sourceMap = {
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
    'hdfc': 'HDFC Bank',
    'sbi': 'SBI',
    'icici': 'ICICI Bank',
    'axis': 'Axis Bank',
    'kotak': 'Kotak Bank',
    'yes bank': 'Yes Bank',
    'pnb': 'PNB',
  };

  static bool isFinancialSms(String sender, String body) {
    final upperSender = sender.toUpperCase();
    for (final knownSender in _financialSenders) {
      if (upperSender.contains(knownSender)) return true;
    }
    final hasAmount = _amountRegex.hasMatch(body);
    final hasKeyword =
        _debitRegex.hasMatch(body) || _creditRegex.hasMatch(body);
    return hasAmount && hasKeyword;
  }

  static Transaction? parse(String sender, String body, DateTime date) {
    if (!isFinancialSms(sender, body)) return null;

    final amountMatch = _amountRegex.firstMatch(body);
    if (amountMatch == null) return null;

    final rawAmount = amountMatch.group(1)!.replaceAll(',', '');
    final amount = double.tryParse(rawAmount);
    if (amount == null || amount <= 0) return null;

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

    String source = '';
    final bodyLower = body.toLowerCase();
    for (final entry in _sourceMap.entries) {
      if (bodyLower.contains(entry.key)) {
        source = entry.value;
        break;
      }
    }

    String? accountLast4;
    final accountMatch = _accountRegex.firstMatch(body);
    if (accountMatch != null) {
      accountLast4 = accountMatch.group(1);
    }

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
}
