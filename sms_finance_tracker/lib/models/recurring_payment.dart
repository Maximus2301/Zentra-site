enum PaymentFrequency { monthly, quarterly, yearly, weekly, oneTime }

class RecurringPayment {
  final int? id;
  final String name;
  final String normalizedKey;
  final double amount;
  final String category;
  final int dueDayOfMonth;
  final PaymentFrequency frequency;
  final bool isActive;
  final bool isFromSms;
  final String sourceSender;
  final String sourceSnippet;
  final String? accountLast4;
  final double confidence;
  final int createdAt;
  final int lastSeenAt;

  const RecurringPayment({
    this.id,
    required this.name,
    required this.normalizedKey,
    required this.amount,
    required this.category,
    required this.dueDayOfMonth,
    required this.frequency,
    this.isActive = true,
    this.isFromSms = false,
    this.sourceSender = '',
    this.sourceSnippet = '',
    this.accountLast4,
    this.confidence = 0,
    required this.createdAt,
    required this.lastSeenAt,
  });

  Map<String, dynamic> toMap() {
    return {
      if (id != null) 'id': id,
      'name': name,
      'normalizedKey': normalizedKey,
      'amount': amount,
      'category': category,
      'dueDay': dueDayOfMonth,
      'frequency': frequency.name,
      'isActive': isActive ? 1 : 0,
      'isFromSms': isFromSms ? 1 : 0,
      'sourceSender': sourceSender,
      'sourceSnippet': sourceSnippet,
      'accountLast4': accountLast4,
      'confidence': confidence,
      'createdAt': createdAt,
      'lastSeenAt': lastSeenAt,
    };
  }

  factory RecurringPayment.fromMap(Map<String, dynamic> map) {
    return RecurringPayment(
      id: map['id'] as int?,
      name: map['name'] as String? ?? '',
      normalizedKey: map['normalizedKey'] as String? ?? '',
      amount: (map['amount'] as num?)?.toDouble() ?? 0,
      category: map['category'] as String? ?? 'Bill Payment',
      dueDayOfMonth: map['dueDay'] as int? ?? 1,
      frequency: _frequencyFromString(map['frequency'] as String?),
      isActive: (map['isActive'] as int? ?? 1) == 1,
      isFromSms: (map['isFromSms'] as int? ?? 0) == 1,
      sourceSender: map['sourceSender'] as String? ?? '',
      sourceSnippet: map['sourceSnippet'] as String? ?? '',
      accountLast4: map['accountLast4'] as String?,
      confidence: (map['confidence'] as num?)?.toDouble() ?? 0,
      createdAt: map['createdAt'] as int? ?? 0,
      lastSeenAt: map['lastSeenAt'] as int? ?? 0,
    );
  }

  static PaymentFrequency _frequencyFromString(String? raw) {
    switch (raw) {
      case 'weekly':
        return PaymentFrequency.weekly;
      case 'quarterly':
        return PaymentFrequency.quarterly;
      case 'yearly':
        return PaymentFrequency.yearly;
      case 'oneTime':
        return PaymentFrequency.oneTime;
      default:
        return PaymentFrequency.monthly;
    }
  }
}
