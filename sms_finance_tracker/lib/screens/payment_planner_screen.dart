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
  // Persistent paid IDs for the current calendar month (survives restarts).
  Set<int> _paidIds = {};
  // For monthly payments: how many of the last 3 months have a matching expense.
  Map<int, int> _consecutiveCounts = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Data loading
  // ─────────────────────────────────────────────────────────────────────────

  Future<void> _load() async {
    setState(() => _loading = true);
    final now = DateTime.now();

    // Fetch current month, prior 2 months (for consecutive check), and DB paid
    // IDs for the current month — all in parallel.
    final results = await Future.wait([
      DbService.getRecurringPayments(),
      DbService.getTransactionsByDateRange(
        DateTime(now.year, now.month, 1),
        DateTime(now.year, now.month + 1, 1),
      ),
      DbService.getTransactionsByDateRange(
        DateTime(now.year, now.month - 2, 1), // 3-month window start
        DateTime(now.year, now.month, 1),     // exclusive: up to current month
      ),
      DbService.getPaidPaymentIds(now.year, now.month),
    ]);

    if (!mounted) return;

    final payments = results[0] as List<RecurringPayment>;
    final currentTxns = results[1] as List<Transaction>;
    final histTxns = results[2] as List<Transaction>;
    final dbPaidIds = Set<int>.from(results[3] as Set<int>);

    // Auto-persist any transaction matches not yet in payment_history.
    // This converts ephemeral match results into durable "paid" records.
    final toAutoMark = <int, int?>{}; // paymentId → matched txn id
    for (final p in payments) {
      if (!p.isActive || p.id == null) continue;
      if (dbPaidIds.contains(p.id)) continue; // already recorded
      final matched = _matchInList(p, currentTxns);
      if (matched != null) {
        toAutoMark[p.id!] = matched.id;
      }
    }
    if (toAutoMark.isNotEmpty) {
      await Future.wait(toAutoMark.entries.map((e) => DbService.recordPaymentPaid(
            paymentId: e.key,
            year: now.year,
            month: now.month,
            isManual: false,
            matchedTxnId: e.value,
          )));
      if (!mounted) return;
      dbPaidIds.addAll(toAutoMark.keys);
    }

    // Compute 3-month consecutive match counts for monthly payments.
    // Non-monthly payments are always considered verified (count = 3).
    final counts = <int, int>{};
    final allTxns = [...currentTxns, ...histTxns];
    for (final p in payments) {
      if (p.id == null) continue;
      if (p.frequency != PaymentFrequency.monthly) {
        counts[p.id!] = 3;
        continue;
      }
      int hits = 0;
      for (var i = 0; i < 3; i++) {
        final mo = DateTime(now.year, now.month - i);
        final moTxns = allTxns
            .where((t) => t.date.year == mo.year && t.date.month == mo.month)
            .toList();
        // Current month: also count DB-persisted paid records (handles manual marks).
        if (i == 0 && dbPaidIds.contains(p.id)) {
          hits++;
        } else if (_matchInList(p, moTxns) != null) {
          hits++;
        }
      }
      counts[p.id!] = hits;
    }

    if (!mounted) return;
    setState(() {
      _payments = payments;
      _paidIds = dbPaidIds;
      _consecutiveCounts = counts;
      _loading = false;
    });
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Derived state helpers (all O(1) after _load)
  // ─────────────────────────────────────────────────────────────────────────

  bool _isPaid(RecurringPayment p) =>
      p.id != null && _paidIds.contains(p.id);

  // Monthly SMS-detected payments need 3 consecutive months of evidence.
  bool _isVerified(RecurringPayment p) {
    if (p.frequency != PaymentFrequency.monthly) return true;
    if (!p.isFromSms) return true; // manually added: trusted by default
    return (_consecutiveCounts[p.id] ?? 0) >= 3;
  }

  double get _monthlyPlannedTotal => _payments
      .where((p) => p.isActive)
      .fold(0.0, (sum, p) => sum + p.amount);

  int get _activeCount => _payments.where((p) => p.isActive).length;

  int get _paidCount => _payments
      .where((p) => p.isActive && _isPaid(p))
      .length;

  // ─────────────────────────────────────────────────────────────────────────
  // Static matching logic — used in _load and consecutive-count calculation.
  // Tolerances: keyword+amount and category+amount use ≤3%; bare amount ≤3%.
  // ─────────────────────────────────────────────────────────────────────────

  static Transaction? _matchInList(
      RecurringPayment payment, List<Transaction> txns) {
    final nameLower = payment.name.toLowerCase();
    final keywords = nameLower
        .split(RegExp(r'\s+'))
        .where((w) => w.length > 3)
        .toList();

    for (final t in txns) {
      if (t.type != TransactionType.expense) continue;
      final searchText =
          '${t.merchant.toLowerCase()} ${t.rawSms.toLowerCase()}';
      final diff = (t.amount - payment.amount).abs();
      final pct = payment.amount > 0 ? diff / payment.amount : 999.0;
      final tight = pct <= 0.03;
      final keywordHit =
          keywords.isNotEmpty && keywords.any(searchText.contains);
      final categoryHit = _txnToCategory(t) == payment.category;
      final nearDue = (t.date.day - payment.dueDayOfMonth).abs() <= 7;

      if (keywordHit && tight) return t;
      if (categoryHit && tight && nearDue) return t;
      if (tight && nearDue) return t;
    }
    return null;
  }

  static String _txnToCategory(Transaction t) {
    if (t.category == 'Essential' && t.subcategory == 'Utilities') {
      return 'Utilities';
    }
    if (t.category == 'Essential' && t.subcategory == 'Insurance') {
      return 'Insurance';
    }
    if (t.category == 'Essential' && t.subcategory == 'EMI/Loan') {
      return 'EMI/Loan';
    }
    if (t.category == 'Lifestyle' && t.subcategory == 'Subscriptions') {
      return 'Subscription';
    }
    return t.subcategory;
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Month-boundary-aware due-day offset.
  //
  // If the due day has passed but is within a 7-day grace window, we show it
  // as overdue (the payment was missed this month). If it's older than 7 days,
  // we project forward to the NEXT month's occurrence, treating it as upcoming.
  // This prevents a bill due on the 3rd from showing "Overdue" on the 25th.
  // ─────────────────────────────────────────────────────────────────────────

  static int _effectiveDaysUntil(int dueDay) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final thisMonthDue = DateTime(now.year, now.month, dueDay);
    final diff = thisMonthDue.difference(today).inDays;
    if (diff >= -7) return diff; // within grace window: could be overdue or future
    // Past the grace window → project to next month's occurrence
    final nextMonthDue = DateTime(now.year, now.month + 1, dueDay);
    return nextMonthDue.difference(today).inDays;
  }

  // Returns false when an SMS-derived monthly entry's reminder is too stale to
  // project forward. Prevents a March CC bill SMS from showing as "Due June 2".
  // Rule: once the current month's due date is past the grace window, only
  // project to next month if the SMS was received within the last 60 days
  // (≈ 2 billing cycles). Manually-added and non-monthly entries always project.
  static bool _shouldShowFutureEntry(RecurringPayment p) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final thisMonthDiff =
        DateTime(now.year, now.month, p.dueDayOfMonth).difference(today).inDays;
    // Still in the current month's window → no projection, always show.
    if (thisMonthDiff >= -7) return true;
    // Past grace and projected to next month.
    // Manually-added entries and non-monthly entries always project forward.
    if (!p.isFromSms || p.frequency != PaymentFrequency.monthly) return true;
    // SMS-derived monthly: suppress if the bill reminder is older than 60 days.
    final daysSince = now
        .difference(DateTime.fromMillisecondsSinceEpoch(p.lastSeenAt))
        .inDays;
    return daysSince <= 60;
  }

  // ─────────────────────────────────────────────────────────────────────────
  // CRUD actions
  // ─────────────────────────────────────────────────────────────────────────

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

  Future<void> _toggleActive(RecurringPayment p) async {
    await DbService.updateRecurringPayment(RecurringPayment(
      id: p.id,
      name: p.name,
      normalizedKey: p.normalizedKey,
      amount: p.amount,
      category: p.category,
      dueDayOfMonth: p.dueDayOfMonth,
      frequency: p.frequency,
      isActive: !p.isActive,
      isFromSms: p.isFromSms,
      sourceSender: p.sourceSender,
      sourceSnippet: p.sourceSnippet,
      accountLast4: p.accountLast4,
      confidence: p.confidence,
      createdAt: p.createdAt,
      lastSeenAt: p.lastSeenAt,
    ));
    _load();
  }

  Future<void> _togglePaid(RecurringPayment p) async {
    if (p.id == null) return;
    final now = DateTime.now();
    if (_isPaid(p)) {
      await DbService.removePaymentPaid(p.id!, now.year, now.month);
    } else {
      await DbService.recordPaymentPaid(
        paymentId: p.id!,
        year: now.year,
        month: now.month,
        isManual: true,
      );
    }
    _load();
  }

  Future<void> _delete(RecurringPayment p) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete payment?'),
        content: Text('Remove "${p.name}" from Payment Planner?'),
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
    if (confirmed == true && p.id != null) {
      await DbService.deleteRecurringPayment(p.id!);
      _load();
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Build
  // ─────────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final active = _payments.where((p) => p.isActive).toList();
    final paused = _payments.where((p) => !p.isActive).toList();

    // Partition active payments into four sections using pre-computed state.
    // All effective-days calculations happen once here, not inside tiles.
    final List<_TileData> overdueItems = [];
    final List<_TileData> dueSoonItems = [];
    final List<_TileData> upcomingItems = [];
    final List<_TileData> paidItems = [];

    for (final p in active) {
      final isPaid = _isPaid(p);
      final days = _effectiveDaysUntil(p.dueDayOfMonth);
      final data = _TileData(payment: p, isPaid: isPaid,
          isVerified: _isVerified(p), effectiveDaysUntil: days);
      if (isPaid) {
        paidItems.add(data);
      } else if (days < 0) {
        overdueItems.add(data);
      } else if (_shouldShowFutureEntry(p)) {
        if (days <= 5) {
          dueSoonItems.add(data);
        } else {
          upcomingItems.add(data);
        }
      }
      // else: stale SMS-derived entry whose current-month window has closed —
      // suppressed until a fresh bill reminder arrives or the user adds it manually.
    }

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
                    activeCount: _activeCount,
                    paidCount: _paidCount,
                    currencyFormat: _currencyFormat,
                  ),
                  const SizedBox(height: 16),
                  if (_payments.isEmpty)
                    _EmptyPlannerState(onAdd: () => _openForm())
                  else ...[
                    if (overdueItems.isNotEmpty)
                      _buildSection(
                        context,
                        title: 'Overdue',
                        titleColor: const Color(0xFFC62828),
                        items: overdueItems,
                      ),
                    if (dueSoonItems.isNotEmpty)
                      _buildSection(
                        context,
                        title: 'Due Soon',
                        titleColor: const Color(0xFFE65100),
                        items: dueSoonItems,
                      ),
                    if (upcomingItems.isNotEmpty)
                      _buildSection(context, title: 'Upcoming', items: upcomingItems),
                    if (paidItems.isNotEmpty)
                      _buildSection(
                        context,
                        title: 'Paid This Month',
                        titleColor: const Color(0xFF2E7D32),
                        items: paidItems,
                      ),
                    if (paused.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      const Divider(),
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        child: Text(
                          'Paused',
                          style: theme.textTheme.labelLarge?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      ...paused.map((p) => _tile(
                            _TileData(
                              payment: p,
                              isPaid: false,
                              isVerified: _isVerified(p),
                              effectiveDaysUntil:
                                  _effectiveDaysUntil(p.dueDayOfMonth),
                            ),
                          )),
                    ],
                  ],
                ],
              ),
            ),
    );
  }

  Widget _buildSection(
    BuildContext context, {
    required String title,
    required List<_TileData> items,
    Color? titleColor,
  }) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 8, top: 4),
          child: Text(
            title,
            style: theme.textTheme.labelLarge?.copyWith(
              color: titleColor ?? theme.colorScheme.onSurfaceVariant,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.5,
            ),
          ),
        ),
        ...items.map(_tile),
      ],
    );
  }

  Widget _tile(_TileData data) => _PaymentPlannerTile(
        data: data,
        currencyFormat: _currencyFormat,
        onEdit: () => _openForm(data.payment),
        onDelete: () => _delete(data.payment),
        onToggleActive: () => _toggleActive(data.payment),
        onTogglePaid: () => _togglePaid(data.payment),
      );
}

// ───────────────────────────────────────────────────────────────────────────
// Immutable bundle passed to each tile — computed once in build(), never
// recomputed inside the tile itself.
// ───────────────────────────────────────────────────────────────────────────

class _TileData {
  final RecurringPayment payment;
  final bool isPaid;
  final bool isVerified;
  final int effectiveDaysUntil;

  const _TileData({
    required this.payment,
    required this.isPaid,
    required this.isVerified,
    required this.effectiveDaysUntil,
  });
}

// ───────────────────────────────────────────────────────────────────────────
// Summary card
// ───────────────────────────────────────────────────────────────────────────

class _PlannerSummaryCard extends StatelessWidget {
  final double plannedTotal;
  final int activeCount;
  final int paidCount;
  final NumberFormat currencyFormat;

  const _PlannerSummaryCard({
    required this.plannedTotal,
    required this.activeCount,
    required this.paidCount,
    required this.currencyFormat,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final allPaid = activeCount > 0 && paidCount == activeCount;
    final progress = activeCount > 0 ? paidCount / activeCount : 0.0;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Bills This Month',
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                  decoration: BoxDecoration(
                    color: allPaid
                        ? const Color(0xFF2E7D32).withOpacity(0.12)
                        : theme.colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '$paidCount / $activeCount paid',
                    style: theme.textTheme.labelMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: allPaid
                          ? const Color(0xFF2E7D32)
                          : theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              '₹${currencyFormat.format(plannedTotal)}',
              style: theme.textTheme.headlineSmall
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
            Text(
              '$activeCount active bill${activeCount == 1 ? '' : 's'} planned',
              style: theme.textTheme.bodySmall
                  ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
            if (activeCount > 0) ...[
              const SizedBox(height: 14),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: progress,
                  minHeight: 6,
                  backgroundColor: theme.colorScheme.surfaceContainerHighest,
                  valueColor: AlwaysStoppedAnimation(
                    allPaid
                        ? const Color(0xFF2E7D32)
                        : theme.colorScheme.primary,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ───────────────────────────────────────────────────────────────────────────
// Empty state
// ───────────────────────────────────────────────────────────────────────────

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
              style:
                  theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            Text(
              'Bill reminders detected from SMS will appear here after sync. You can also add one manually.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant),
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

// ───────────────────────────────────────────────────────────────────────────
// Payment tile — receives pre-computed _TileData, never recomputes matching.
// All actions live in the ⋮ menu; no inline action buttons keep partial-
// payment scenarios from cluttering the tile face.
// ───────────────────────────────────────────────────────────────────────────

class _PaymentPlannerTile extends StatelessWidget {
  final _TileData data;
  final NumberFormat currencyFormat;
  final VoidCallback onEdit;
  final VoidCallback onDelete;
  final VoidCallback onToggleActive;
  final VoidCallback onTogglePaid;

  const _PaymentPlannerTile({
    required this.data,
    required this.currencyFormat,
    required this.onEdit,
    required this.onDelete,
    required this.onToggleActive,
    required this.onTogglePaid,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final p = data.payment;

    // Determine status badge
    final String statusLabel;
    final Color statusColor;

    if (!p.isActive) {
      statusLabel = 'Paused';
      statusColor = theme.colorScheme.onSurfaceVariant;
    } else if (data.isPaid) {
      statusLabel = '✓ Paid';
      statusColor = const Color(0xFF2E7D32);
    } else {
      final d = data.effectiveDaysUntil;
      if (d < 0) {
        statusLabel = 'Overdue';
        statusColor = const Color(0xFFC62828);
      } else if (d == 0) {
        statusLabel = 'Due today';
        statusColor = const Color(0xFFE65100);
      } else if (d <= 3) {
        statusLabel = 'Due in ${d}d';
        statusColor = const Color(0xFFE65100);
      } else {
        statusLabel = 'Due ${_ordinal(p.dueDayOfMonth)}';
        statusColor = theme.colorScheme.onSurfaceVariant;
      }
    }

    final IconData icon = switch (p.category) {
      'Credit Card' => Icons.credit_card_outlined,
      'Utilities' => Icons.bolt_outlined,
      'EMI/Loan' => Icons.account_balance_outlined,
      'Insurance' => Icons.shield_outlined,
      'Subscription' => Icons.subscriptions_outlined,
      _ => Icons.receipt_outlined,
    };

    // Subtitle: category · frequency [· Unverified warning]
    final subtitleParts = [
      p.category,
      _frequencyShort(p.frequency),
    ];
    if (!data.isVerified) subtitleParts.add('⚠ Unverified');

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      elevation: 1,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onEdit,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          child: Row(
            children: [
              // Category icon container
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  icon,
                  color: statusColor.withOpacity(data.isPaid ? 0.85 : 0.65),
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              // Name + subtitle
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      p.name,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                        decoration: !p.isActive ? TextDecoration.lineThrough : null,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitleParts.join(' · '),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: !data.isVerified
                            ? const Color(0xFFE65100)
                            : theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              // Amount + status badge
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '₹${currencyFormat.format(p.amount)}',
                    style: theme.textTheme.titleSmall
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.10),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      statusLabel,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: statusColor,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              // ⋮ menu — all actions live here, no inline buttons
              PopupMenuButton<String>(
                icon: Icon(
                  Icons.more_vert,
                  color: theme.colorScheme.onSurfaceVariant,
                  size: 18,
                ),
                onSelected: (value) {
                  switch (value) {
                    case 'edit':
                      onEdit();
                    case 'paid':
                      onTogglePaid();
                    case 'toggle':
                      onToggleActive();
                    case 'delete':
                      onDelete();
                  }
                },
                itemBuilder: (context) => [
                  const PopupMenuItem(value: 'edit', child: Text('Edit')),
                  PopupMenuItem(
                    value: 'paid',
                    child: Text(data.isPaid ? 'Mark as Unpaid' : 'Mark as Paid'),
                  ),
                  PopupMenuItem(
                    value: 'toggle',
                    child: Text(p.isActive ? 'Pause' : 'Activate'),
                  ),
                  const PopupMenuItem(
                    value: 'delete',
                    child: Text('Delete'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  static String _ordinal(int day) {
    if (day >= 11 && day <= 13) return '${day}th';
    return switch (day % 10) {
      1 => '${day}st',
      2 => '${day}nd',
      3 => '${day}rd',
      _ => '${day}th',
    };
  }

  static String _frequencyShort(PaymentFrequency f) => switch (f) {
        PaymentFrequency.weekly => 'Weekly',
        PaymentFrequency.quarterly => 'Quarterly',
        PaymentFrequency.yearly => 'Yearly',
        PaymentFrequency.oneTime => 'Once',
        PaymentFrequency.monthly => 'Monthly',
      };
}

// ───────────────────────────────────────────────────────────────────────────
// Add / Edit form sheet
// ───────────────────────────────────────────────────────────────────────────

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
    final e = widget.existing;
    _nameController = TextEditingController(text: e?.name ?? '');
    _amountController = TextEditingController(
        text: e == null ? '' : e.amount.toStringAsFixed(2));
    _dueDayController =
        TextEditingController(text: (e?.dueDayOfMonth ?? 1).toString());
    _category = e?.category ?? widget.categoryOptions.first;
    _frequency = e?.frequency ?? PaymentFrequency.monthly;
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
    final e = widget.existing;
    final dueDay = int.parse(_dueDayController.text.trim()).clamp(1, 28);
    final raw =
        '${_category}_${_nameController.text.trim()}_${e?.accountLast4 ?? ''}'
            .toLowerCase()
            .replaceAll(RegExp(r'[^a-z0-9]+'), '_')
            .replaceAll(RegExp(r'^_+|_+$'), '');
    final now = DateTime.now().millisecondsSinceEpoch;

    Navigator.pop(
      context,
      RecurringPayment(
        id: e?.id,
        name: _nameController.text.trim(),
        normalizedKey: raw,
        amount: double.parse(_amountController.text.trim()),
        category: _category,
        dueDayOfMonth: dueDay,
        frequency: _frequency,
        isActive: e?.isActive ?? true,
        isFromSms: e?.isFromSms ?? false,
        sourceSender: e?.sourceSender ?? '',
        sourceSnippet: e?.sourceSnippet ?? '',
        accountLast4: e?.accountLast4,
        confidence: e?.confidence ?? 0,
        createdAt: e?.createdAt ?? now,
        lastSeenAt: e?.lastSeenAt ?? now,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final insets = MediaQuery.of(context).viewInsets;

    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, insets.bottom + 16),
      child: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.existing == null ? 'Add Payment' : 'Edit Payment',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                    labelText: 'Name', border: OutlineInputBorder()),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Enter a name' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _amountController,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                    labelText: 'Amount', border: OutlineInputBorder()),
                validator: (v) {
                  final a = double.tryParse(v?.trim() ?? '');
                  return (a == null || a <= 0) ? 'Enter a valid amount' : null;
                },
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _category,
                      decoration: const InputDecoration(
                          labelText: 'Category', border: OutlineInputBorder()),
                      items: widget.categoryOptions
                          .map((c) =>
                              DropdownMenuItem(value: c, child: Text(c)))
                          .toList(),
                      onChanged: (v) {
                        if (v != null) setState(() => _category = v);
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _dueDayController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                          labelText: 'Due day (1–28)',
                          border: OutlineInputBorder()),
                      validator: (v) {
                        final d = int.tryParse(v?.trim() ?? '');
                        return (d == null || d < 1 || d > 28) ? '1–28' : null;
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<PaymentFrequency>(
                value: _frequency,
                decoration: const InputDecoration(
                    labelText: 'Frequency', border: OutlineInputBorder()),
                items: PaymentFrequency.values
                    .map((f) => DropdownMenuItem(
                        value: f, child: Text(_freqLabel(f))))
                    .toList(),
                onChanged: (v) {
                  if (v != null) setState(() => _frequency = v);
                },
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _submit,
                  child: Text(
                      widget.existing == null ? 'Add Payment' : 'Save'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static String _freqLabel(PaymentFrequency f) => switch (f) {
        PaymentFrequency.monthly => 'Monthly',
        PaymentFrequency.quarterly => 'Quarterly',
        PaymentFrequency.yearly => 'Yearly',
        PaymentFrequency.weekly => 'Weekly',
        PaymentFrequency.oneTime => 'One time',
      };
}
