import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as p;
import '../models/transaction.dart';

class DbService {
  static Database? _db;

  static Future<Database> get database async {
    _db ??= await _initDb();
    return _db!;
  }

  static Future<Database> _initDb() async {
    final dbPath = await getDatabasesPath();
    final path = p.join(dbPath, 'finance_tracker.db');

    return openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            smsAddress TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            merchant TEXT NOT NULL,
            source TEXT NOT NULL,
            rawSms TEXT NOT NULL,
            date INTEGER NOT NULL,
            accountLast4 TEXT,
            UNIQUE(rawSms, date)
          )
        ''');
      },
    );
  }

  static Future<int> insertTransaction(Transaction t) async {
    final db = await database;
    try {
      final result = await db.insert(
        'transactions',
        t.toMap(),
        conflictAlgorithm: ConflictAlgorithm.ignore,
      );
      return result;
    } catch (_) {
      return 0;
    }
  }

  static Future<int> insertBatch(List<Transaction> transactions) async {
    if (transactions.isEmpty) return 0;
    final db = await database;
    final batch = db.batch();
    for (final t in transactions) {
      batch.insert(
        'transactions',
        t.toMap(),
        conflictAlgorithm: ConflictAlgorithm.ignore,
      );
    }
    final results = await batch.commit(noResult: false);
    int count = 0;
    for (final r in results) {
      if (r is int && r > 0) count++;
    }
    return count;
  }

  static Future<List<Transaction>> getAllTransactions() async {
    final db = await database;
    final maps = await db.query('transactions', orderBy: 'date DESC');
    return maps.map(Transaction.fromMap).toList();
  }

  static Future<List<Transaction>> getTransactionsByMonth(
      int year, int month) async {
    final from = DateTime(year, month, 1);
    final to = DateTime(year, month + 1, 1);
    return getTransactionsByDateRange(from, to);
  }

  static Future<List<Transaction>> getTransactionsByDateRange(
      DateTime from, DateTime to) async {
    final db = await database;
    final maps = await db.query(
      'transactions',
      where: 'date >= ? AND date < ?',
      whereArgs: [from.millisecondsSinceEpoch, to.millisecondsSinceEpoch],
      orderBy: 'date DESC',
    );
    return maps.map(Transaction.fromMap).toList();
  }

  static Future<Map<String, double>> getCategorySummary(
      int year, int month) async {
    final db = await database;
    final from = DateTime(year, month, 1);
    final to = DateTime(year, month + 1, 1);

    final result = await db.rawQuery('''
      SELECT category, SUM(amount) as total
      FROM transactions
      WHERE type = 'expense'
        AND date >= ?
        AND date < ?
      GROUP BY category
      ORDER BY total DESC
    ''', [from.millisecondsSinceEpoch, to.millisecondsSinceEpoch]);

    final Map<String, double> summary = {};
    for (final row in result) {
      final cat = row['category'] as String;
      final total = (row['total'] as num).toDouble();
      summary[cat] = total;
    }
    return summary;
  }

  static Future<List<Map<String, dynamic>>> getMonthlyTotals(int year) async {
    final db = await database;
    final from = DateTime(year, 1, 1);
    final to = DateTime(year + 1, 1, 1);

    final result = await db.rawQuery('''
      SELECT
        strftime('%m', datetime(date / 1000, 'unixepoch')) as month,
        type,
        SUM(amount) as total
      FROM transactions
      WHERE date >= ? AND date < ?
      GROUP BY month, type
      ORDER BY month ASC
    ''', [from.millisecondsSinceEpoch, to.millisecondsSinceEpoch]);

    return result;
  }

  static Future<void> deleteTransaction(int id) async {
    final db = await database;
    await db.delete('transactions', where: 'id = ?', whereArgs: [id]);
  }

  static Future<int> getCount() async {
    final db = await database;
    final result =
        await db.rawQuery('SELECT COUNT(*) as count FROM transactions');
    return (result.first['count'] as int?) ?? 0;
  }
}
