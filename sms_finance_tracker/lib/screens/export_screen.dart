import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/db_service.dart';
import '../services/excel_service.dart';

class ExportScreen extends StatefulWidget {
  const ExportScreen({super.key});

  @override
  State<ExportScreen> createState() => _ExportScreenState();
}

class _ExportScreenState extends State<ExportScreen> {
  late DateTime _fromDate;
  late DateTime _toDate;
  bool _loading = false;
  int _previewCount = 0;
  bool _previewLoaded = false;

  final DateFormat _dateFormat = DateFormat('dd MMM yyyy');

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _fromDate = DateTime(now.year, now.month, 1);
    _toDate = now;
    _loadPreview();
  }

  Future<void> _loadPreview() async {
    final data = await DbService.getTransactionsByDateRange(
        _fromDate, _toDate.add(const Duration(days: 1)));
    if (mounted) {
      setState(() {
        _previewCount = data.length;
        _previewLoaded = true;
      });
    }
  }

  Future<void> _pickFromDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _fromDate,
      firstDate: DateTime(2020),
      lastDate: _toDate,
    );
    if (picked != null) {
      setState(() {
        _fromDate = picked;
        _previewLoaded = false;
      });
      _loadPreview();
    }
  }

  Future<void> _pickToDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _toDate,
      firstDate: _fromDate,
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() {
        _toDate = picked;
        _previewLoaded = false;
      });
      _loadPreview();
    }
  }

  Future<void> _export() async {
    if (_previewCount == 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No transactions found in this range')),
      );
      return;
    }

    setState(() => _loading = true);

    try {
      final data = await DbService.getTransactionsByDateRange(
          _fromDate, _toDate.add(const Duration(days: 1)));

      final title =
          'Finance Report ${_dateFormat.format(_fromDate)} – ${_dateFormat.format(_toDate)}';
      final path = await ExcelService.generateAndShare(data, title);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Exported ${data.length} transactions'),
            action: SnackBarAction(
              label: 'OK',
              onPressed: () {},
            ),
          ),
        );
      }

      debugPrint('Excel saved to: $path');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Export failed: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Export to Excel'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Select Date Range',
              style: theme.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 16),
            _buildDatePickerTile(
              context: context,
              label: 'From Date',
              value: _dateFormat.format(_fromDate),
              icon: Icons.calendar_today,
              onTap: _pickFromDate,
            ),
            const SizedBox(height: 12),
            _buildDatePickerTile(
              context: context,
              label: 'To Date',
              value: _dateFormat.format(_toDate),
              icon: Icons.calendar_month,
              onTap: _pickToDate,
            ),
            const SizedBox(height: 24),
            if (_previewLoaded) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Icon(
                        Icons.receipt_long,
                        color: theme.colorScheme.primary,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Preview',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                            ),
                            Text(
                              '$_previewCount transaction${_previewCount == 1 ? '' : 's'} will be exported',
                              style: theme.textTheme.bodyMedium
                                  ?.copyWith(fontWeight: FontWeight.w600),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ] else ...[
              const Center(child: CircularProgressIndicator()),
              const SizedBox(height: 24),
            ],
            Text(
              'The Excel file will contain:',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 8),
            for (final sheet in [
              'Transactions — full list with details',
              'Monthly Summary — income vs expenses by month',
              'Category Summary — expenses grouped by category',
            ])
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    Icon(
                      Icons.check_circle_outline,
                      size: 16,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                        child: Text(sheet,
                            style: theme.textTheme.bodySmall)),
                  ],
                ),
              ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                onPressed: _loading ? null : _export,
                icon: _loading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.file_download),
                label: Text(_loading ? 'Generating...' : 'Export & Share'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: theme.colorScheme.primary,
                  foregroundColor: theme.colorScheme.onPrimary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDatePickerTile({
    required BuildContext context,
    required String label,
    required String value,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          border: Border.all(color: theme.colorScheme.outlineVariant),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(icon, color: theme.colorScheme.primary, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  Text(
                    value,
                    style: theme.textTheme.bodyMedium
                        ?.copyWith(fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.arrow_drop_down,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ],
        ),
      ),
    );
  }
}
