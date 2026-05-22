import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/recurring_payment.dart';
import '../models/transaction.dart';
import '../services/db_service.dart';

class PaymentPlannerScreen extends StatefulWidget {
  const PaymentPlannerScreen({super.key});

  @override
  State<PaymentPlannerScreen> createState() => _PaymentPlannerScreenState();
}

class _PaymentPlannerScreenState extends State<PaymentPlannerScreen> {
  static const List<String> _categoryOptions = [
    'Bill Payment',
    'Credit Card',
    'Utilities',
    'EMI/Loan',
    'Insurance',
    'Subscription',
  ];

  final NumberFormat _currencyFormat = NumberFormat('#,##,##0.00', 'en_IN');

  List<RecurringPayment> _payments = [];
  List<Transaction> _currentMonthTransactions = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final now = DateTime.now();
    final results = await Future.wait([
      DbService.getRecurringPayments(),
      DbService.getTransactionsByDateRange(
        DateTime(now.year, now.month, 1),
        DateTime(now.year, now.month + 1, 1),
      ),
    ]);

    if (!mounted) return;
    setState(() {
      _payments = results[0] as List<RecurringPayment>;
      _currentMonthTransactions = results[1] as List<Transaction>;
      _loading = false;
    });
  }

  double get _monthlyPlannedTotal => _payments
      .where((payment) => payment.isActive)
      .fold(0.0, (sum, payment) => sum + payment.amount);

  int get _matchedCount => _payments
      .where((payment) => payment.isActive)
      .where((payment) => _findMatchedTransaction(payment) != null)
      .length;

  Future<void> _openForm([RecurringPayment? existing]) async {
    final payment = await showModalBottomSheet<RecurringPayment>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _PaymentFormSheet(
        existing: existing,
        categoryOptions: _categoryOptions,
      ),
    );
    if (payment == null) return;

    if (existing == null) {
      await DbService.insertRecurringPayment(payment);
    } else {
      await DbService.updateRecurringPayment(payment);
    }
    _load();
  }

  Future<void> _toggleActive(RecurringPayment payment) async {
    await DbService.updateRecurringPayment(
      RecurringPayment(
        id: payment.id,
        name: payment.name,
        normalizedKey: payment.normalizedKey,
        amount: payment.amount,
        category: payment.category,
        dueDayOfMonth: payment.dueDayOfMonth,
        frequency: payment.frequency,
        isActive: !payment.isActive,
        isFromSms: payment.isFromSms,
        sourceSender: payment.sourceSender,
        sourceSnippet: payment.sourceSnippet,
        accountLast4: payment.accountLast4,
        confidence: payment.confidence,
        createdAt: payment.createdAt,
        lastSeenAt: payment.lastSeenAt,
      ),
    );
    _load();
  }

  Future<void> _delete(RecurringPayment payment) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete payment?'),
        content: Text('Remove "${payment.name}" from Payment Planner?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true && payment.id != null) {
      await DbService.deleteRecurringPayment(payment.id!);
      _load();
    }
  }

  Transaction? _findMatchedTransaction(RecurringPayment payment) {
    final nameLower = payment.name.toLowerCase();
    final keywords = nameLower
        .split(RegExp(r'\s+'))
        .where((word) => word.length > 3)
        .toList();

    for (final transaction in _currentMonthTransactions) {
      if (transaction.type != TransactionType.expense) continue;

      final searchText =
          '${transaction.merchant.toLowerCase()} ${transaction.rawSms.toLowerCase()}';
      final amountDiff = (transaction.amount - payment.amount).abs();
      final amountPct =
          payment.amount > 0 ? amountDiff / payment.amount : 999.0;
      final looseAmountMatch = amountPct <= 0.20;
      final tightAmountMatch = amountPct <= 0.03;
      final keywordMatch =
          keywords.isNotEmpty && keywords.any(searchText.contains);
      final categoryMatch =
          _mapTransactionToPlannerCategory(transaction) == payment.category;
      final nearDueDay =
          (transaction.date.day - payment.dueDayOfMonth).abs() <= 7;

      if (keywordMatch && looseAmountMatch) return transaction;
      if (categoryMatch && looseAmountMatch && nearDueDay) return transaction;
      if (tightAmountMatch) return transaction;
    }

    return null;
  }

  String _mapTransactionToPlannerCategory(Transaction transaction) {
    if (transaction.category == 'Essential' &&
        transaction.subcategory == 'Utilities') {
      return 'Utilities';
    }
    if (transaction.category == 'Essential' &&
        transaction.subcategory == 'Insurance') {
      return 'Insurance';
    }
    if (transaction.category == 'Essential' &&
        transaction.subcategory == 'EMI/Loan') {
      return 'EMI/Loan';
    }
    if (transaction.category == 'Lifestyle' &&
        transaction.subcategory == 'Subscriptions') {
      return 'Subscription';
    }
    return transaction.subcategory;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final activePayments = _payments.where((payment) => payment.isActive).toList();
    final pausedPayments =
        _payments.where((payment) => !payment.isActive).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Payment Planner'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'Add payment',
            onPressed: () => _openForm(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openForm(),
        icon: const Icon(Icons.add),
        label: const Text('Add Payment'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
                children: [
                  _PlannerSummaryCard(
                    plannedTotal: _monthlyPlannedTotal,
                    activeCount: activePayments.length,
                    matchedCount: _matchedCount,
                    currencyFormat: _currencyFormat,
                  ),
                  const SizedBox(height: 16),
                  if (_payments.isEmpty)
                    _EmptyPlannerState(onAdd: () => _openForm())
                  else ...[
                    if (activePayments.isNotEmpty) ...[
                      Text(
                        'Active',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 8),
                      ...activePayments.map(
                        (payment) => _PaymentPlannerTile(
                          payment: payment,
                          matchedTransaction: _findMatchedTransaction(payment),
                          currencyFormat: _currencyFormat,
                          onEdit: () => _openForm(payment),
                          onDelete: () => _delete(payment),
                          onToggleActive: () => _toggleActive(payment),
                        ),
                      ),
                    ],
                    if (pausedPayments.isNotEmpty) ...[
                      const SizedBox(height: 16),
                      Text(
                        'Paused',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 8),
                      ...pausedPayments.map(
                        (payment) => _PaymentPlannerTile(
                          payment: payment,
                          matchedTransaction: null,
                          currencyFormat: _currencyFormat,
                          onEdit: () => _openForm(payment),
                          onDelete: () => _delete(payment),
                          onToggleActive: () => _toggleActive(payment),
                        ),
                      ),
                    ],
                  ],
                ],
              ),
            ),
    );
  }
}

class _PlannerSummaryCard extends StatelessWidget {
  final double plannedTotal;
  final int activeCount;
  final int matchedCount;
  final NumberFormat currencyFormat;

  const _PlannerSummaryCard({
    required this.plannedTotal,
    required this.activeCount,
    required this.matchedCount,
    required this.currencyFormat,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'This Month',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              '₹${currencyFormat.format(plannedTotal)} planned',
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '$activeCount active payments • $matchedCount matched this month',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyPlannerState extends StatelessWidget {
  final VoidCallback onAdd;

  const _EmptyPlannerState({required this.onAdd});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
        child: Column(
          children: [
            Icon(
              Icons.event_repeat_outlined,
              size: 64,
              color: theme.colorScheme.onSurfaceVariant.withOpacity(0.45),
            ),
            const SizedBox(height: 16),
            Text(
              'No planned payments yet',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Bill reminders and scheduled debit SMS will appear here after sync. You can also add one manually.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onAdd,
              icon: const Icon(Icons.add),
              label: const Text('Add Payment'),
            ),
          ],
        ),
      ),
    );
  }
}

class _PaymentPlannerTile extends StatelessWidget {
  final RecurringPayment payment;
  final Transaction? matchedTransaction;
  final NumberFormat currencyFormat;
  final VoidCallback onEdit;
  final VoidCallback onDelete;
  final VoidCallback onToggleActive;

  const _PaymentPlannerTile({
    required this.payment,
    required this.matchedTransaction,
    required this.currencyFormat,
    required this.onEdit,
    required this.onDelete,
    required this.onToggleActive,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final chips = <Widget>[
      _InfoChip(label: payment.category),
      _InfoChip(label: 'Due ${payment.dueDayOfMonth}'),
      _InfoChip(label: payment.isFromSms ? 'SMS' : 'Manual'),
      _InfoChip(label: _frequencyLabel(payment.frequency)),
      if (payment.accountLast4 != null)
        _InfoChip(label: 'xx${payment.accountLast4}'),
      if (matchedTransaction != null)
        const _InfoChip(label: 'Matched this month', positive: true),
      if (payment.confidence > 0)
        _InfoChip(label: 'Conf ${(payment.confidence * 100).round()}%'),
    ];

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        payment.name,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '₹${currencyFormat.format(payment.amount)}',
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ),
                PopupMenuButton<String>(
                  onSelected: (value) {
                    switch (value) {
                      case 'edit':
                        onEdit();
                        break;
                      case 'toggle':
                        onToggleActive();
                        break;
                      case 'delete':
                        onDelete();
                        break;
                    }
                  },
                  itemBuilder: (context) => [
                    const PopupMenuItem(value: 'edit', child: Text('Edit')),
                    PopupMenuItem(
                      value: 'toggle',
                      child: Text(payment.isActive ? 'Pause' : 'Activate'),
                    ),
                    const PopupMenuItem(value: 'delete', child: Text('Delete')),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: chips,
            ),
            if (payment.sourceSnippet.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                payment.sourceSnippet,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  static String _frequencyLabel(PaymentFrequency frequency) {
    switch (frequency) {
      case PaymentFrequency.weekly:
        return 'Weekly';
      case PaymentFrequency.quarterly:
        return 'Quarterly';
      case PaymentFrequency.yearly:
        return 'Yearly';
      case PaymentFrequency.oneTime:
        return 'One time';
      case PaymentFrequency.monthly:
        return 'Monthly';
    }
  }
}

class _InfoChip extends StatelessWidget {
  final String label;
  final bool positive;

  const _InfoChip({required this.label, this.positive = false});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final Color background = positive
        ? theme.colorScheme.primary.withOpacity(0.12)
        : theme.colorScheme.surfaceContainerHighest;
    final Color foreground = positive
        ? theme.colorScheme.primary
        : theme.colorScheme.onSurfaceVariant;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: theme.textTheme.labelMedium?.copyWith(
          color: foreground,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _PaymentFormSheet extends StatefulWidget {
  final RecurringPayment? existing;
  final List<String> categoryOptions;

  const _PaymentFormSheet({
    required this.existing,
    required this.categoryOptions,
  });

  @override
  State<_PaymentFormSheet> createState() => _PaymentFormSheetState();
}

class _PaymentFormSheetState extends State<_PaymentFormSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _amountController;
  late final TextEditingController _dueDayController;
  late String _category;
  late PaymentFrequency _frequency;

  @override
  void initState() {
    super.initState();
    final existing = widget.existing;
    _nameController = TextEditingController(text: existing?.name ?? '');
    _amountController = TextEditingController(
      text: existing == null ? '' : existing.amount.toStringAsFixed(2),
    );
    _dueDayController = TextEditingController(
      text: (existing?.dueDayOfMonth ?? 1).toString(),
    );
    _category = existing?.category ?? widget.categoryOptions.first;
    _frequency = existing?.frequency ?? PaymentFrequency.monthly;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _amountController.dispose();
    _dueDayController.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    final existing = widget.existing;
    final dueDay = int.parse(_dueDayController.text.trim()).clamp(1, 28);
    final normalizedKey = _normalizedKey(
      _nameController.text.trim(),
      _category,
      existing?.accountLast4,
    );
    final now = DateTime.now().millisecondsSinceEpoch;

    Navigator.pop(
      context,
      RecurringPayment(
        id: existing?.id,
        name: _nameController.text.trim(),
        normalizedKey: normalizedKey,
        amount: double.parse(_amountController.text.trim()),
        category: _category,
        dueDayOfMonth: dueDay,
        frequency: _frequency,
        isActive: existing?.isActive ?? true,
        isFromSms: existing?.isFromSms ?? false,
        sourceSender: existing?.sourceSender ?? '',
        sourceSnippet: existing?.sourceSnippet ?? '',
        accountLast4: existing?.accountLast4,
        confidence: existing?.confidence ?? 0,
        createdAt: existing?.createdAt ?? now,
        lastSeenAt: existing?.lastSeenAt ?? now,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final viewInsets = MediaQuery.of(context).viewInsets;

    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, viewInsets.bottom + 16),
      child: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.existing == null ? 'Add Payment' : 'Edit Payment',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'Name',
                  border: OutlineInputBorder(),
                ),
                validator: (value) =>
                    (value == null || value.trim().isEmpty) ? 'Enter a name' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _amountController,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  labelText: 'Amount',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  final amount = double.tryParse(value?.trim() ?? '');
                  if (amount == null || amount <= 0) {
                    return 'Enter a valid amount';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _category,
                      decoration: const InputDecoration(
                        labelText: 'Category',
                        border: OutlineInputBorder(),
                      ),
                      items: widget.categoryOptions
                          .map(
                            (category) => DropdownMenuItem(
                              value: category,
                              child: Text(category),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        if (value != null) setState(() => _category = value);
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _dueDayController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Due day',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) {
                        final day = int.tryParse(value?.trim() ?? '');
                        if (day == null || day < 1 || day > 28) {
                          return '1-28';
                        }
                        return null;
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<PaymentFrequency>(
                value: _frequency,
                decoration: const InputDecoration(
                  labelText: 'Frequency',
                  border: OutlineInputBorder(),
                ),
                items: PaymentFrequency.values
                    .map(
                      (frequency) => DropdownMenuItem(
                        value: frequency,
                        child: Text(_frequencyText(frequency)),
                      ),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value != null) setState(() => _frequency = value);
                },
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _submit,
                  child: Text(widget.existing == null ? 'Add Payment' : 'Save'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static String _frequencyText(PaymentFrequency frequency) {
    switch (frequency) {
      case PaymentFrequency.monthly:
        return 'Monthly';
      case PaymentFrequency.quarterly:
        return 'Quarterly';
      case PaymentFrequency.yearly:
        return 'Yearly';
      case PaymentFrequency.weekly:
        return 'Weekly';
      case PaymentFrequency.oneTime:
        return 'One time';
    }
  }

  static String _normalizedKey(
      String name, String category, String? accountLast4) {
    final raw = '${category}_${name}_${accountLast4 ?? ''}'.toLowerCase();
    return raw
        .replaceAll(RegExp(r'[^a-z0-9]+'), '_')
        .replaceAll(RegExp(r'^_+|_+$'), '');
  }
}
