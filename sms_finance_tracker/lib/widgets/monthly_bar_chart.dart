import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../services/db_service.dart';
import '../theme/app_theme.dart';

class MonthlyBarChart extends StatefulWidget {
  final DateTime selectedMonth;

  const MonthlyBarChart({super.key, required this.selectedMonth});

  @override
  State<MonthlyBarChart> createState() => _MonthlyBarChartState();
}

class _MonthlyBarChartState extends State<MonthlyBarChart> {
  bool _loading = true;
  final List<_MonthData> _monthData = [];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void didUpdateWidget(MonthlyBarChart oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.selectedMonth != widget.selectedMonth) {
      _loadData();
    }
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    try {
      final raw = await DbService.getMonthlyTotals(widget.selectedMonth.year);

      final Map<int, _MonthData> byMonth = {};
      for (final row in raw) {
        final monthNum = int.tryParse(row['month'] as String? ?? '0') ?? 0;
        byMonth[monthNum] ??= _MonthData(month: monthNum);
        if (row['type'] == 'income') {
          byMonth[monthNum]!.income = (row['total'] as num).toDouble();
        } else if (row['type'] == 'expense') {
          byMonth[monthNum]!.expense = (row['total'] as num).toDouble();
        }
      }

      final List<_MonthData> result = [];
      final endMonth = widget.selectedMonth.month;
      for (int i = 5; i >= 0; i--) {
        int m = endMonth - i;
        if (m <= 0) m += 12;
        result.add(byMonth[m] ?? _MonthData(month: m));
      }

      if (mounted) {
        setState(() {
          _monthData
            ..clear()
            ..addAll(result);
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    final incomeColor = AppTheme.incomeColor(context);
    final expenseColor = AppTheme.expenseColor(context);

    double maxVal = 1000;
    for (final d in _monthData) {
      if (d.income > maxVal) maxVal = d.income;
      if (d.expense > maxVal) maxVal = d.expense;
    }

    final groups = <BarChartGroupData>[];
    for (int i = 0; i < _monthData.length; i++) {
      final d = _monthData[i];
      groups.add(
        BarChartGroupData(
          x: i,
          barRods: [
            BarChartRodData(
              toY: d.income,
              color: incomeColor,
              width: 10,
              borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(4)),
            ),
            BarChartRodData(
              toY: d.expense,
              color: expenseColor,
              width: 10,
              borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(4)),
            ),
          ],
        ),
      );
    }

    final monthNames = _monthData
        .map((d) => DateFormat('MMM')
            .format(DateTime(widget.selectedMonth.year, d.month)))
        .toList();

    return BarChart(
      BarChartData(
        maxY: maxVal * 1.2,
        barGroups: groups,
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: maxVal / 4,
          getDrawingHorizontalLine: (value) => FlLine(
            color: Theme.of(context)
                .colorScheme
                .outlineVariant
                .withOpacity(0.5),
            strokeWidth: 1,
          ),
        ),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 44,
              getTitlesWidget: (value, meta) {
                if (value == 0) return const SizedBox.shrink();
                final k = value / 1000;
                return Text(
                  '${k.toStringAsFixed(k >= 100 ? 0 : (k >= 10 ? 1 : 1))}K',
                  style: TextStyle(
                    fontSize: 10,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                final idx = value.toInt();
                if (idx < 0 || idx >= monthNames.length) {
                  return const SizedBox.shrink();
                }
                return Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    monthNames[idx],
                    style: TextStyle(
                      fontSize: 10,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                );
              },
            ),
          ),
          topTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false)),
        ),
        barTouchData: BarTouchData(enabled: true),
      ),
    );
  }
}

class _MonthData {
  final int month;
  double income;
  double expense;

  _MonthData({required this.month, this.income = 0, this.expense = 0});
}
