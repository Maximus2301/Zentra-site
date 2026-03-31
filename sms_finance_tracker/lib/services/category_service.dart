class CategoryResult {
  final String category;
  final String subcategory;

  const CategoryResult({required this.category, required this.subcategory});
}

class CategoryService {
  static CategoryResult classify(
      String merchant, String rawSms, bool isCredit) {
    if (isCredit) {
      return _classifyIncome(merchant, rawSms);
    } else {
      return _classifyExpense(merchant, rawSms);
    }
  }

  static CategoryResult _classifyIncome(String merchant, String rawSms) {
    final text = '${merchant.toLowerCase()} ${rawSms.toLowerCase()}';

    if (_matches(text, ['salary', 'payroll', 'sal credit', 'monthly salary'])) {
      return const CategoryResult(
          category: 'Income', subcategory: 'Salary');
    }
    if (_matches(text, ['refund', 'reversal', 'reversed', 'refunded'])) {
      return const CategoryResult(
          category: 'Income', subcategory: 'Refund');
    }
    if (_matches(text, ['cashback', 'cash back', 'rewards redeemed'])) {
      return const CategoryResult(
          category: 'Income', subcategory: 'Cashback');
    }
    if (_matches(text, ['interest', 'dividend', 'fd interest', 'rd interest'])) {
      return const CategoryResult(
          category: 'Income', subcategory: 'Interest');
    }
    return const CategoryResult(
        category: 'Income', subcategory: 'Transfer Received');
  }

  static CategoryResult _classifyExpense(String merchant, String rawSms) {
    final text = '${merchant.toLowerCase()} ${rawSms.toLowerCase()}';

    // Food Delivery
    if (_matches(
        text, ['swiggy', 'zomato', 'dunzo', 'blinkit', 'zepto', 'bigbasket quick'])) {
      return const CategoryResult(
          category: 'Food Delivery', subcategory: 'Food Delivery');
    }

    // Groceries
    if (_matches(text, [
      'dmart',
      'bigbasket',
      'reliance fresh',
      'more retail',
      'spencer',
      'grofers',
      'jiomart',
      'supermarket',
      'grocery',
    ])) {
      return const CategoryResult(
          category: 'Essential', subcategory: 'Groceries');
    }

    // Utilities
    if (_matches(text, [
      'bescom',
      'tata power',
      'adani electric',
      'msedcl',
      'bses',
      'tneb',
      'electricity',
      'water board',
      'mahanagar gas',
      'indraprastha gas',
      'broadband',
      'jio fiber',
      'airtel xstream',
      'act fiber',
      'postpaid',
      'mobile bill',
      'bsnl',
      'vodafone',
    ])) {
      return const CategoryResult(
          category: 'Essential', subcategory: 'Utilities');
    }

    // Healthcare
    if (_matches(text, [
      'apollo',
      '1mg',
      'medplus',
      'netmeds',
      'practo',
      'hospital',
      'clinic',
      'pharmacy',
      'medical',
      'diagnostic',
      'thyrocare',
      'lal path',
    ])) {
      return const CategoryResult(
          category: 'Essential', subcategory: 'Healthcare');
    }

    // Insurance
    if (_matches(text, [
      'lic',
      'life insurance',
      'health insurance',
      'motor insurance',
      'hdfc life',
      'icici prudential',
      'max life',
      'bajaj allianz',
      'star health',
      'niva bupa',
    ])) {
      return const CategoryResult(
          category: 'Essential', subcategory: 'Insurance');
    }

    // EMI / Loan
    if (_matches(text, [
      'emi',
      'loan repayment',
      'home loan',
      'equated monthly',
    ])) {
      return const CategoryResult(
          category: 'Essential', subcategory: 'EMI/Loan');
    }

    // Rent & Housing
    if (_matches(text, [
      'rent',
      'society maintenance',
      'maintenance charges',
    ])) {
      return const CategoryResult(
          category: 'Rent & Housing', subcategory: 'Rent');
    }

    // Transport - Fuel
    if (_matches(text, [
      'petrol',
      'diesel',
      'bpcl',
      'hpcl',
      'indian oil',
      'bharat petrol',
      'shell',
      'fuel',
      'cng',
    ])) {
      return const CategoryResult(
          category: 'Transport', subcategory: 'Fuel');
    }

    // Transport - Cab
    if (_matches(text, ['uber', 'ola', 'rapido', 'meru', 'taxi', 'cab'])) {
      return const CategoryResult(category: 'Transport', subcategory: 'Cab');
    }

    // Transport - Public
    if (_matches(text, [
      'metro',
      'irctc',
      'indian railways',
      'redbus',
      'ksrtc',
      'msrtc',
      'bmtc',
    ])) {
      return const CategoryResult(
          category: 'Transport', subcategory: 'Public Transport');
    }

    // Dining
    if (_matches(text, [
      'restaurant',
      'cafe',
      'coffee',
      'starbucks',
      'ccd',
      'mcdonald',
      'kfc',
      'dominos',
      'pizza hut',
      'subway',
      'burger king',
      'haldiram',
      'barbeque',
      'dhaba',
    ])) {
      return const CategoryResult(
          category: 'Lifestyle', subcategory: 'Dining');
    }

    // Entertainment
    if (_matches(text, [
      'pvr',
      'inox',
      'cinepolis',
      'bookmyshow',
      'movie',
      'cinema',
      'gaming',
    ])) {
      return const CategoryResult(
          category: 'Lifestyle', subcategory: 'Entertainment');
    }

    // Subscriptions
    if (_matches(text, [
      'netflix',
      'hotstar',
      'disney',
      'amazon prime',
      'spotify',
      'youtube premium',
      'zee5',
      'sonyliv',
      'apple music',
    ])) {
      return const CategoryResult(
          category: 'Lifestyle', subcategory: 'Subscriptions');
    }

    // Shopping
    if (_matches(text, [
      'amazon',
      'flipkart',
      'myntra',
      'ajio',
      'nykaa',
      'meesho',
      'tata cliq',
      'croma',
      'reliance digital',
      'vijay sales',
    ])) {
      return const CategoryResult(
          category: 'Lifestyle', subcategory: 'Shopping');
    }

    // Travel
    if (_matches(text, [
      'makemytrip',
      'goibibo',
      'cleartrip',
      'easemytrip',
      'air india',
      'indigo',
      'spicejet',
      'vistara',
      'airline',
      'flight',
      'oyo',
    ])) {
      return const CategoryResult(
          category: 'Lifestyle', subcategory: 'Travel');
    }

    // Education
    if (_matches(text, [
      'byju',
      'unacademy',
      'vedantu',
      'coursera',
      'udemy',
      'upgrad',
      'school fee',
      'college fee',
      'tuition',
    ])) {
      return const CategoryResult(
          category: 'Education', subcategory: 'Online Learning');
    }

    // Investment
    if (_matches(text, [
      'mutual fund',
      'sip',
      'zerodha',
      'groww',
      'upstox',
      'angel broking',
      'kuvera',
      'nps',
      'ppf',
      'fixed deposit',
    ])) {
      return const CategoryResult(
          category: 'Investment', subcategory: 'Investment');
    }

    return const CategoryResult(category: 'Others', subcategory: 'Others');
  }

  static List<String> get allCategories => const [
        'Essential',
        'Food Delivery',
        'Lifestyle',
        'Rent & Housing',
        'Transport',
        'Education',
        'Investment',
        'Income',
        'Others',
      ];

  static bool _matches(String text, List<String> keywords) {
    for (final keyword in keywords) {
      if (text.contains(keyword)) return true;
    }
    return false;
  }
}
