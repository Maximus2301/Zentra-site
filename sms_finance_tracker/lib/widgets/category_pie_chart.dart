import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../theme/app_theme.dart';

class CategoryPieChart extends StatefulWidget {
  final Map<String, double> categoryTotals;

  const CategoryPieChart({super.key, required this.categoryTotals});

  @override
  State<CategoryPieChart> createState() => _CategoryPieChartState();
}

class _CategoryPieChartState extends State<CategoryPieChart> {
  int _touchedIndex = -1;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final sorted = widget.categoryTotals.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    final total = sorted.fold(0.0, (sum, e) => sum + e.value);
    if (total <= 0) return const SizedBox.shrink();

    final currencyFormat = NumberFormat('#,##,##0', 'en_IN');

    final sections = <PieChartSectionData>[];
    for (int i = 0; i < sorted.length; i++) {
      final entry = sorted[i];
      final color = AppTheme.categoryColors[i % AppTheme.categoryColors.length];
      final pct = (entry.value / total * 100);
      final isTouched = i == _touchedIndex;

      sections.add(
        PieChartSectionData(
          value: entry.value,
          color: color,
          radius: isTouched ? 64 : 56,
          title: isTouched ? '${pct.toStringAsFixed(1)}%' : '',
          titleStyle: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
          badgeWidget: null,
        ),
      );
    }

    return Column(
      children: [
        SizedBox(
          height: 180,
          child: Stack(
            alignment: Alignment.center,
            children: [
              PieChart(
                PieChartData(
                  sections: sections,
                  centerSpaceRadius: 44,
                  sectionsSpace: 2,
                  pieTouchData: PieTouchData(
                    touchCallback: (event, response) {
                      setState(() {
                        if (!event.isInterestedForInteractions ||
                            response == null ||
                            response.touchedSection == null) {
                          _touchedIndex = -1;
                          return;
                        }
                        _touchedIndex =
                            response.touchedSection!.touchedSectionIndex;
                      });
                    },
                  ),
                ),
              ),
              if (_touchedIndex >= 0 && _touchedIndex < sorted.length)
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '${(sorted[_touchedIndex].value / total * 100).toStringAsFixed(1)}%',
                      style: textTheme.titleMedium
                          ?.copyWith(fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          runSpacing: 6,
          children: [
            for (int i = 0; i < sorted.length; i++)
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      color: AppTheme
                          .categoryColors[i % AppTheme.categoryColors.length],
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${sorted[i].key}  ₹${currencyFormat.format(sorted[i].value)}',
                    style: textTheme.bodySmall,
                  ),
                ],
              ),
          ],
        ),
      ],
    );
  }
}
