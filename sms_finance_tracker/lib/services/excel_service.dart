import 'dart:io';
import 'package:excel/excel.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:intl/intl.dart';
import '../models/transaction.dart';

class ExcelService {
  static Future<String> generateAndShare(
      List<Transaction> transactions, String title) async {
    final excel = Excel.createExcel();

    // Remove default Sheet1
    if (excel.sheets.containsKey('Sheet1')) {
      excel.delete('Sheet1');
    }

    _buildTransactionsSheet(excel, transactions);
    _buildMonthlySummarySheet(excel, transactions);
    _buildCategorySummarySheet(excel, transactions);

    final monthStr =
        DateFormat('MMM_yyyy').format(DateTime.now());
    final fileName = 'FinanceReport_$monthStr.xlsx';

    final tempDir = await getTemporaryDirectory();
    final filePath = '${tempDir.path}/$fileName';
    final fileBytes = excel.encode();
    if (fileBytes == null) {
      throw Exception('Failed to encode Excel file');
    }
    final file = File(filePath);
    await file.writeAsBytes(fileBytes);

    await Share.shareXFiles(
      [XFile(filePath)],
      subject: title,
    );

    return filePath;
  }

  static void _buildTransactionsSheet(
      Excel excel, List<Transaction> transactions) {
    final sheet = excel['Transactions'];
    final headers = [
      'Date',
      'Type',
      'Amount (₹)',
      'Category',
      'Subcategory',
      'Merchant',
      'Source',
      'Account',
    ];

    final headerStyle = CellStyle(
      bold: true,
      backgroundColorHex: ExcelColor.fromHexString('#1565C0'),
      fontColorHex: ExcelColor.fromHexString('#FFFFFF'),
    );

    for (int col = 0; col < headers.length; col++) {
      final cell =
          sheet.cell(CellIndex.indexByColumnRow(columnIndex: col, rowIndex: 0));
      cell.value = TextCellValue(headers[col]);
      cell.cellStyle = headerStyle;
    }

    final dateFormat = DateFormat('dd MMM yyyy');
    final altRowStyle = CellStyle(
      backgroundColorHex: ExcelColor.fromHexString('#F5F5F5'),
    );

    for (int i = 0; i < transactions.length; i++) {
      final t = transactions[i];
      final rowIndex = i + 1;
      final isAlt = rowIndex % 2 == 0;
      final style = isAlt ? altRowStyle : null;

      final rowData = [
        TextCellValue(dateFormat.format(t.date)),
        TextCellValue(t.type.name),
        DoubleCellValue(t.amount),
        TextCellValue(t.category),
        TextCellValue(t.subcategory),
        TextCellValue(t.merchant),
        TextCellValue(t.source),
        TextCellValue(t.accountLast4 ?? ''),
      ];

      for (int col = 0; col < rowData.length; col++) {
        final cell = sheet.cell(
            CellIndex.indexByColumnRow(columnIndex: col, rowIndex: rowIndex));
        cell.value = rowData[col];
        if (style != null) cell.cellStyle = style;
      }
    }

    sheet.setColumnWidth(0, 15);
    sheet.setColumnWidth(1, 10);
    sheet.setColumnWidth(2, 14);
    sheet.setColumnWidth(3, 18);
    sheet.setColumnWidth(4, 18);
    sheet.setColumnWidth(5, 22);
    sheet.setColumnWidth(6, 16);
    sheet.setColumnWidth(7, 10);
  }

  static void _buildMonthlySummarySheet(
      Excel excel, List<Transaction> transactions) {
    final sheet = excel['Monthly Summary'];
    final headers = [
      'Month',
      'Total Income (₹)',
      'Total Expenses (₹)',
      'Net (₹)',
    ];

    final headerStyle = CellStyle(
      bold: true,
      backgroundColorHex: ExcelColor.fromHexString('#1565C0'),
      fontColorHex: ExcelColor.fromHexString('#FFFFFF'),
    );

    for (int col = 0; col < headers.length; col++) {
      final cell =
          sheet.cell(CellIndex.indexByColumnRow(columnIndex: col, rowIndex: 0));
      cell.value = TextCellValue(headers[col]);
      cell.cellStyle = headerStyle;
    }

    final Map<String, Map<String, double>> monthMap = {};
    final monthKeyFormat = DateFormat('MMM yyyy');

    for (final t in transactions) {
      final key = monthKeyFormat.format(t.date);
      monthMap[key] ??= {'income': 0, 'expense': 0};
      if (t.type == TransactionType.income) {
        monthMap[key]!['income'] = (monthMap[key]!['income'] ?? 0) + t.amount;
      } else {
        monthMap[key]!['expense'] =
            (monthMap[key]!['expense'] ?? 0) + t.amount;
      }
    }

    final sortedKeys = monthMap.keys.toList()
      ..sort((a, b) {
        final dateA = DateFormat('MMM yyyy').parse(a);
        final dateB = DateFormat('MMM yyyy').parse(b);
        return dateA.compareTo(dateB);
      });

    for (int i = 0; i < sortedKeys.length; i++) {
      final key = sortedKeys[i];
      final income = monthMap[key]!['income'] ?? 0;
      final expense = monthMap[key]!['expense'] ?? 0;
      final net = income - expense;
      final rowIndex = i + 1;

      sheet
          .cell(CellIndex.indexByColumnRow(columnIndex: 0, rowIndex: rowIndex))
          .value = TextCellValue(key);
      sheet
          .cell(CellIndex.indexByColumnRow(columnIndex: 1, rowIndex: rowIndex))
          .value = DoubleCellValue(income);
      sheet
          .cell(CellIndex.indexByColumnRow(columnIndex: 2, rowIndex: rowIndex))
          .value = DoubleCellValue(expense);
      sheet
          .cell(CellIndex.indexByColumnRow(columnIndex: 3, rowIndex: rowIndex))
          .value = DoubleCellValue(net);
    }

    sheet.setColumnWidth(0, 14);
    sheet.setColumnWidth(1, 18);
    sheet.setColumnWidth(2, 20);
    sheet.setColumnWidth(3, 14);
  }

  static void _buildCategorySummarySheet(
      Excel excel, List<Transaction> transactions) {
    final sheet = excel['Category Summary'];
    final headers = ['Category', 'Subcategory', 'Total (₹)', 'Count'];

    final headerStyle = CellStyle(
      bold: true,
      backgroundColorHex: ExcelColor.fromHexString('#1565C0'),
      fontColorHex: ExcelColor.fromHexString('#FFFFFF'),
    );

    for (int col = 0; col < headers.length; col++) {
      final cell =
          sheet.cell(CellIndex.indexByColumnRow(columnIndex: col, rowIndex: 0));
      cell.value = TextCellValue(headers[col]);
      cell.cellStyle = headerStyle;
    }

    final expenses =
        transactions.where((t) => t.type == TransactionType.expense).toList();

    final Map<String, Map<String, dynamic>> grouped = {};
    for (final t in expenses) {
      final key = '${t.category}||${t.subcategory}';
      grouped[key] ??= {
        'category': t.category,
        'subcategory': t.subcategory,
        'total': 0.0,
        'count': 0,
      };
      grouped[key]!['total'] = (grouped[key]!['total'] as double) + t.amount;
      grouped[key]!['count'] = (grouped[key]!['count'] as int) + 1;
    }

    final sorted = grouped.values.toList()
      ..sort((a, b) =>
          (b['total'] as double).compareTo(a['total'] as double));

    for (int i = 0; i < sorted.length; i++) {
      final row = sorted[i];
      final rowIndex = i + 1;

      sheet
          .cell(CellIndex.indexByColumnRow(columnIndex: 0, rowIndex: rowIndex))
          .value = TextCellValue(row['category'] as String);
      sheet
          .cell(CellIndex.indexByColumnRow(columnIndex: 1, rowIndex: rowIndex))
          .value = TextCellValue(row['subcategory'] as String);
      sheet
          .cell(CellIndex.indexByColumnRow(columnIndex: 2, rowIndex: rowIndex))
          .value = DoubleCellValue(row['total'] as double);
      sheet
          .cell(CellIndex.indexByColumnRow(columnIndex: 3, rowIndex: rowIndex))
          .value = IntCellValue(row['count'] as int);
    }

    sheet.setColumnWidth(0, 18);
    sheet.setColumnWidth(1, 20);
    sheet.setColumnWidth(2, 14);
    sheet.setColumnWidth(3, 8);
  }
}
