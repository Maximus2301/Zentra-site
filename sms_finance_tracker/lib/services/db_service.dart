import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as p;
import '../models/recurring_payment.dart';
import '../models/transaction.dart';

class DbService {
  static Database? _db;
  static const int _dbVersion = 41;
  static const String _createTransactionsTableSql = '''
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
      recordKind TEXT NOT NULL DEFAULT 'cashflow',
      assetType TEXT,
      assetId TEXT,
      assetBalance REAL,
      investmentDelta REAL,
      UNIQUE(rawSms, date)
    )
  ''';
  static const String _createRecurringPaymentsTableSql = '''
    CREATE TABLE IF NOT EXISTS recurring_payments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      normalizedKey TEXT NOT NULL UNIQUE,
      amount REAL NOT NULL,
      category TEXT NOT NULL,
      dueDay INTEGER NOT NULL DEFAULT 1,
      frequency TEXT NOT NULL DEFAULT 'monthly',
      isActive INTEGER NOT NULL DEFAULT 1,
      isFromSms INTEGER NOT NULL DEFAULT 0,
      sourceSender TEXT NOT NULL DEFAULT '',
      sourceSnippet TEXT NOT NULL DEFAULT '',
      accountLast4 TEXT,
      confidence REAL NOT NULL DEFAULT 0,
      createdAt INTEGER NOT NULL,
      lastSeenAt INTEGER NOT NULL
    )
  ''';

  static Future<Database> get database async {
    _db ??= await _initDb();
    return _db!;
  }

  static Future<Database> _initDb() async {
    final dbPath = await getDatabasesPath();
    final path = p.join(dbPath, 'finance_tracker.db');

    return openDatabase(
      path,
      version: _dbVersion,
      onCreate: (db, version) async {
        await db.execute(_createTransactionsTableSql);
        await db.execute(_createRecurringPaymentsTableSql);
      },
      onUpgrade: (db, oldVersion, newVersion) async {
        if (oldVersion < 40) {
          await _migrateToV40(db);
        }
        if (oldVersion < 41) {
          await _migrateToV41(db);
        }
      },
    );
  }

  // v40 adds asset/investment state to transaction rows so account snapshots
  // and liquidation events can participate in tracked-assets calculations.
  static Future<void> _migrateToV40(Database db) async {
    await _addTransactionsColumnIfMissing(
      db,
      'recordKind',
      "TEXT NOT NULL DEFAULT 'cashflow'",
    );
    await _addTransactionsColumnIfMissing(db, 'assetType', 'TEXT');
    await _addTransactionsColumnIfMissing(db, 'assetId', 'TEXT');
    await _addTransactionsColumnIfMissing(db, 'assetBalance', 'REAL');
    await _addTransactionsColumnIfMissing(db, 'investmentDelta', 'REAL');
  }

  // v41 adds planner storage so bill-due/autopay reminder SMS can be tracked
  // without polluting cashflow transactions.
  static Future<void> _migrateToV41(Database db) async {
    await db.execute(_createRecurringPaymentsTableSql);
  }

  static Future<void> _addTransactionsColumnIfMissing(
    Database db,
    String columnName,
    String columnSql,
  ) async {
    final columns = await db.rawQuery("PRAGMA table_info('transactions')");
    final exists = columns.any((column) => column['name'] == columnName);
    if (exists) return;
    await db.execute(
      'ALTER TABLE transactions ADD COLUMN $columnName $columnSql',
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

  static Future<List<Transaction>> getLatestAssetRecords() async {
    final db = await database;
    final maps = await db.rawQuery('''
      SELECT t.*
      FROM transactions t
      INNER JOIN (
        SELECT assetType, assetId, MAX(date) AS maxDate
        FROM transactions
        WHERE assetType IS NOT NULL
          AND assetId IS NOT NULL
          AND assetBalance IS NOT NULL
        GROUP BY assetType, assetId
      ) latest
        ON t.assetType = latest.assetType
       AND t.assetId = latest.assetId
       AND t.date = latest.maxDate
      WHERE t.assetBalance IS NOT NULL
      ORDER BY t.assetBalance DESC, t.date DESC
    ''');
    return maps.map(Transaction.fromMap).toList();
  }

  static Future<double> getTrackedAssetTotal() async {
    final assets = await getLatestAssetRecords();
    return assets.fold(0.0, (sum, asset) => sum + (asset.assetBalance ?? 0.0));
  }

  static Future<double> getInvestmentAssetTotal() async {
    const investmentAssetTypes = {
      'epf',
      'fixedDeposit',
      'mutualFund',
      'equity',
      'nps',
      'ppf',
    };
    final assets = await getLatestAssetRecords();
    return assets.fold(0.0, (sum, asset) {
      if (!investmentAssetTypes.contains(asset.assetType)) return sum;
      return sum + (asset.assetBalance ?? 0.0);
    });
  }

  static Future<List<RecurringPayment>> getRecurringPayments() async {
    final db = await database;
    final maps = await db.query(
      'recurring_payments',
      orderBy: 'isActive DESC, dueDay ASC, amount DESC, name ASC',
    );
    return maps.map(RecurringPayment.fromMap).toList();
  }

  static Future<int> insertRecurringPayment(RecurringPayment payment) async {
    final db = await database;
    return db.insert(
      'recurring_payments',
      payment.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  static Future<int> updateRecurringPayment(RecurringPayment payment) async {
    final db = await database;
    return db.update(
      'recurring_payments',
      payment.toMap(),
      where: 'id = ?',
      whereArgs: [payment.id],
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  static Future<void> deleteRecurringPayment(int id) async {
    final db = await database;
    await db.delete('recurring_payments', where: 'id = ?', whereArgs: [id]);
  }

  static Future<void> upsertRecurringPayment(RecurringPayment payment) async {
    final db = await database;
    final rows = await db.query(
      'recurring_payments',
      columns: ['id', 'createdAt'],
      where: 'normalizedKey = ?',
      whereArgs: [payment.normalizedKey],
      limit: 1,
    );
    if (rows.isEmpty) {
      await db.insert('recurring_payments', payment.toMap());
      return;
    }

    final existingId = rows.first['id'];
    final existingCreatedAt = rows.first['createdAt'] as int? ?? payment.createdAt;
    await db.update(
      'recurring_payments',
      {
        ...payment.toMap(),
        'createdAt': existingCreatedAt,
        'isActive': 1,
      },
      where: 'id = ?',
      whereArgs: [existingId],
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  static Future<void> deactivateSmsRecurringPaymentsExcept(
      Set<String> activeKeys) async {
    final db = await database;
    if (activeKeys.isEmpty) {
      await db.update(
        'recurring_payments',
        {'isActive': 0},
        where: 'isFromSms = 1 AND isActive = 1',
      );
      return;
    }

    final placeholders = List.filled(activeKeys.length, '?').join(',');
    await db.rawUpdate(
      'UPDATE recurring_payments SET isActive = 0 '
      'WHERE isFromSms = 1 AND isActive = 1 '
      'AND normalizedKey NOT IN ($placeholders)',
      activeKeys.toList(),
    );
  }

  static Future<List<RecurringPayment>> getActiveRecurringPayments() async {
    final db = await database;
    final maps = await db.query(
      'recurring_payments',
      where: 'isActive = 1',
      orderBy: 'dueDay ASC, amount DESC, name ASC',
    );
    return maps.map(RecurringPayment.fromMap).toList();
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
