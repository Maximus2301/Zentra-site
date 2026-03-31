import 'package:flutter_sms_inbox/flutter_sms_inbox.dart';
import 'package:permission_handler/permission_handler.dart';
import '../models/transaction.dart';
import 'sms_parser.dart';
import 'db_service.dart';

class SyncResult {
  final bool success;
  final String message;
  final int totalScanned;
  final int transactionsFound;
  final int transactionsInserted;

  SyncResult({
    required this.success,
    required this.message,
    this.totalScanned = 0,
    this.transactionsFound = 0,
    this.transactionsInserted = 0,
  });
}

class SmsService {
  static final SmsQuery _query = SmsQuery();

  static Future<bool> requestPermission() async {
    final status = await Permission.sms.request();
    return status.isGranted;
  }

  static Future<bool> hasPermission() async {
    return await Permission.sms.isGranted;
  }

  static Future<SyncResult> syncTransactions({
    DateTime? from,
    void Function(int processed, int total)? onProgress,
  }) async {
    if (!await hasPermission()) {
      return SyncResult(success: false, message: 'SMS permission not granted');
    }

    final messages = await _query.querySms(
      kinds: [SmsQueryKind.inbox],
      count: 5000,
    );

    final fromDate = from ?? DateTime.now().subtract(const Duration(days: 365));
    final filtered = messages.where((m) {
      if (m.dateSent == null) return false;
      return m.dateSent!.isAfter(fromDate);
    }).toList();

    int processed = 0;
    final List<Transaction> parsed = [];

    for (final msg in filtered) {
      final sender = msg.address ?? '';
      final body = msg.body ?? '';
      final date = msg.dateSent ?? DateTime.now();

      final transaction = SmsParser.parse(sender, body, date);
      if (transaction != null) parsed.add(transaction);

      processed++;
      if (processed % 50 == 0) {
        onProgress?.call(processed, filtered.length);
      }
    }

    final inserted = await DbService.insertBatch(parsed);

    return SyncResult(
      success: true,
      totalScanned: filtered.length,
      transactionsFound: parsed.length,
      transactionsInserted: inserted,
      message: 'Sync complete',
    );
  }
}
