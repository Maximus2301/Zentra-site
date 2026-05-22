enum TransactionType { expense, income, transfer }

class Transaction {
  final int? id;
  final String smsAddress;
  final double amount;
  final TransactionType type;
  final String category;
  final String subcategory;
  final String merchant;
  final String source;
  final String rawSms;
  final DateTime date;
  final String? accountLast4;
  final String recordKind;
  final String? assetType;
  final String? assetId;
  final double? assetBalance;
  final double? investmentDelta;

  Transaction({
    this.id,
    required this.smsAddress,
    required this.amount,
    required this.type,
    required this.category,
    required this.subcategory,
    required this.merchant,
    required this.source,
    required this.rawSms,
    required this.date,
    this.accountLast4,
    this.recordKind = 'cashflow',
    this.assetType,
    this.assetId,
    this.assetBalance,
    this.investmentDelta,
  });

  Map<String, dynamic> toMap() {
    return {
      if (id != null) 'id': id,
      'smsAddress': smsAddress,
      'amount': amount,
      'type': type.name,
      'category': category,
      'subcategory': subcategory,
      'merchant': merchant,
      'source': source,
      'rawSms': rawSms,
      'date': date.millisecondsSinceEpoch,
      'accountLast4': accountLast4,
      'recordKind': recordKind,
      'assetType': assetType,
      'assetId': assetId,
      'assetBalance': assetBalance,
      'investmentDelta': investmentDelta,
    };
  }

  factory Transaction.fromMap(Map<String, dynamic> map) {
    final typeValue = map['type'] as String?;
    return Transaction(
      id: map['id'] as int?,
      smsAddress: map['smsAddress'] as String? ?? '',
      amount: (map['amount'] as num?)?.toDouble() ?? 0.0,
      type: typeValue == 'income'
          ? TransactionType.income
          : typeValue == 'transfer'
              ? TransactionType.transfer
              : TransactionType.expense,
      category: map['category'] as String? ?? 'Others',
      subcategory: map['subcategory'] as String? ?? 'Others',
      merchant: map['merchant'] as String? ?? '',
      source: map['source'] as String? ?? '',
      rawSms: map['rawSms'] as String? ?? '',
      date: DateTime.fromMillisecondsSinceEpoch(map['date'] as int? ?? 0),
      accountLast4: map['accountLast4'] as String?,
      recordKind: map['recordKind'] as String? ?? 'cashflow',
      assetType: map['assetType'] as String?,
      assetId: map['assetId'] as String?,
      assetBalance: (map['assetBalance'] as num?)?.toDouble(),
      investmentDelta: (map['investmentDelta'] as num?)?.toDouble(),
    );
  }

  Transaction copyWith({
    int? id,
    String? smsAddress,
    double? amount,
    TransactionType? type,
    String? category,
    String? subcategory,
    String? merchant,
    String? source,
    String? rawSms,
    DateTime? date,
    String? accountLast4,
    String? recordKind,
    String? assetType,
    String? assetId,
    double? assetBalance,
    double? investmentDelta,
  }) {
    return Transaction(
      id: id ?? this.id,
      smsAddress: smsAddress ?? this.smsAddress,
      amount: amount ?? this.amount,
      type: type ?? this.type,
      category: category ?? this.category,
      subcategory: subcategory ?? this.subcategory,
      merchant: merchant ?? this.merchant,
      source: source ?? this.source,
      rawSms: rawSms ?? this.rawSms,
      date: date ?? this.date,
      accountLast4: accountLast4 ?? this.accountLast4,
      recordKind: recordKind ?? this.recordKind,
      assetType: assetType ?? this.assetType,
      assetId: assetId ?? this.assetId,
      assetBalance: assetBalance ?? this.assetBalance,
      investmentDelta: investmentDelta ?? this.investmentDelta,
    );
  }
}
