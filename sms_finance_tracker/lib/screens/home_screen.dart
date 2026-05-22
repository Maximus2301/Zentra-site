import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/transaction.dart';
import '../services/db_service.dart';
import '../services/sms_service.dart';
import '../services/excel_service.dart';
import '../theme/app_theme.dart';
import '../widgets/summary_card.dart';
import '../widgets/monthly_bar_chart.dart';
import '../widgets/category_pie_chart.dart';
import '../widgets/transaction_tile.dart';
import 'payment_planner_screen.dart';
import 'transactions_screen.dart';
import 'export_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  DateTime _selectedMonth = DateTime(
      DateTime.now().year, DateTime.now().month);
  List<Transaction> _transactions = [];
  List<Transaction> _trackedAssets = [];
  bool _loading = false;
  bool _syncing = false;
  int _syncProgress = 0;
  String? _loadError;

  final NumberFormat _currencyFormat = NumberFormat('#,##,##0.00', 'en_IN');

  @override
  void initState() {
    super.initState();
    _loadTransactions();
  }

  Future<void> _loadTransactions() async {
    setState(() {
      _loading = true;
      _loadError = null;
    });
    try {
      final results = await Future.wait([
        DbService.getTransactionsByMonth(_selectedMonth.year, _selectedMonth.month),
        DbService.getLatestAssetRecords(),
      ]);
      if (mounted) {
        setState(() {
          _transactions = results[0] as List<Transaction>;
          _trackedAssets = results[1] as List<Transaction>;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _loadError = 'Could not load data. Pull down to retry.';
        });
      }
    }
  }

  Future<void> _sync() async {
    final granted = await SmsService.requestPermission();
    if (!granted) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('SMS permission denied')),
        );
      }
      return;
    }

    setState(() {
      _syncing = true;
      _syncProgress = 0;
    });

    final result = await SmsService.syncTransactions(
      onProgress: (processed, total) {
        if (mounted) {
          setState(() => _syncProgress =
              total > 0 ? (processed * 100 ~/ total) : 0);
        }
      },
    );

    if (mounted) {
      setState(() => _syncing = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result.success
                ? 'Synced: ${result.transactionsInserted} new transactions found (${result.totalScanned} SMS scanned)'
                : result.message,
          ),
        ),
      );
      _loadTransactions();
    }
  }

  double get _totalIncome => _transactions
      .where((t) => t.type == TransactionType.income)
      .fold(0.0, (sum, t) => sum + t.amount);

  double get _totalExpense => _transactions
      .where((t) => t.type == TransactionType.expense)
      .fold(0.0, (sum, t) => sum + t.amount);

  double get _trackedAssetsTotal => _trackedAssets
      .fold(0.0, (sum, asset) => sum + (asset.assetBalance ?? 0.0));

  double get _trackedInvestmentsTotal => _trackedAssets.fold(0.0, (sum, asset) {
        const investmentAssetTypes = {
          'epf',
          'fixedDeposit',
          'mutualFund',
          'equity',
          'nps',
          'ppf',
        };
        if (!investmentAssetTypes.contains(asset.assetType)) return sum;
        return sum + (asset.assetBalance ?? 0.0);
      });

  Map<String, double> get _categoryTotals {
    final Map<String, double> result = {};
    for (final t in _transactions) {
      if (t.type == TransactionType.expense) {
        result[t.category] = (result[t.category] ?? 0) + t.amount;
      }
    }
    return result;
  }

  void _prevMonth() {
    setState(() {
      _selectedMonth =
          DateTime(_selectedMonth.year, _selectedMonth.month - 1);
    });
    _loadTransactions();
  }

  void _nextMonth() {
    final now = DateTime.now();
    final next =
        DateTime(_selectedMonth.year, _selectedMonth.month + 1);
    if (next.isAfter(DateTime(now.year, now.month))) return;
    setState(() => _selectedMonth = next);
    _loadTransactions();
  }

  Future<void> _export() async {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const ExportScreen()),
    );
  }

  Future<void> _openPaymentPlanner() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const PaymentPlannerScreen()),
    );
    _loadTransactions();
  }

  Future<void> _openTransactions() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => TransactionsScreen(month: _selectedMonth),
      ),
    );
    _loadTransactions();
  }

  Widget _buildDrawer() {
    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          DrawerHeader(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(
                  'HYT MONEY',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Navigate core tools',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          ListTile(
            leading: const Icon(Icons.home_outlined),
            title: const Text('Dashboard'),
            onTap: () => Navigator.pop(context),
          ),
          ListTile(
            leading: const Icon(Icons.event_repeat_outlined),
            title: const Text('Payment Planner'),
            onTap: () {
              Navigator.pop(context);
              _openPaymentPlanner();
            },
          ),
          ListTile(
            leading: const Icon(Icons.receipt_long_outlined),
            title: const Text('Transactions'),
            onTap: () {
              Navigator.pop(context);
              _openTransactions();
            },
          ),
          ListTile(
            leading: const Icon(Icons.file_download_outlined),
            title: const Text('Export'),
            onTap: () {
              Navigator.pop(context);
              _export();
            },
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final monthLabel =
        DateFormat('MMMM yyyy').format(_selectedMonth);
    final net = _totalIncome - _totalExpense;
    final recentTransactions = _transactions.take(5).toList();

    return Scaffold(
      drawer: _buildDrawer(),
      appBar: AppBar(
        title: const Text(
          'HYT MONEY',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        actions: [
          if (_syncing)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  value: _syncProgress > 0 ? _syncProgress / 100 : null,
                ),
              ),
            )
          else
            IconButton(
              icon: const Icon(Icons.sync),
              tooltip: 'Sync SMS',
              onPressed: _sync,
            ),
          IconButton(
            icon: const Icon(Icons.file_download_outlined),
            tooltip: 'Export',
            onPressed: _export,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadTransactions,
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                    horizontal: 8, vertical: 4),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.chevron_left),
                      onPressed: _prevMonth,
                    ),
                    TextButton(
                      onPressed: () async {
                        final picked = await showDatePicker(
                          context: context,
                          initialDate: _selectedMonth,
                          firstDate: DateTime(2020),
                          lastDate: DateTime.now(),
                          initialDatePickerMode: DatePickerMode.year,
                        );
                        if (picked != null) {
                          setState(() => _selectedMonth =
                              DateTime(picked.year, picked.month));
                          _loadTransactions();
                        }
                      },
                      child: Text(
                        monthLabel,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.chevron_right),
                      onPressed: _nextMonth,
                    ),
                  ],
                ),
              ),
            ),
            if (_loading)
              const SliverToBoxAdapter(
                child: Center(
                  child: Padding(
                    padding: EdgeInsets.all(40),
                    child: CircularProgressIndicator(),
                  ),
                ),
              )
            else if (_loadError != null)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(40),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.error_outline,
                        size: 56,
                        color: Theme.of(context).colorScheme.error,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        _loadError!,
                        style: Theme.of(context).textTheme.bodyMedium,
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              )
            else if (_transactions.isEmpty && _trackedAssets.isEmpty)
              SliverToBoxAdapter(
                child: _buildEmptyState(),
              )
            else ...[
              SliverPadding(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 4),
                sliver: SliverToBoxAdapter(
                  child: Row(
                    children: [
                      Expanded(
                        child: SummaryCard(
                          title: 'Income',
                          amount: _totalIncome,
                          icon: Icons.arrow_downward_rounded,
                          color: AppTheme.incomeColor(context),
                          currencyFormat: _currencyFormat,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: SummaryCard(
                          title: 'Expenses',
                          amount: _totalExpense,
                          icon: Icons.arrow_upward_rounded,
                          color: AppTheme.expenseColor(context),
                          currencyFormat: _currencyFormat,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 4),
                sliver: SliverToBoxAdapter(
                  child: SummaryCard(
                    title: 'Net Cash Flow',
                    amount: net.abs(),
                    icon: net >= 0
                        ? Icons.account_balance_wallet
                        : Icons.warning_amber_rounded,
                    color: net >= 0
                        ? AppTheme.incomeColor(context)
                        : AppTheme.expenseColor(context),
                    currencyFormat: _currencyFormat,
                    isFullWidth: true,
                    prefix: net >= 0 ? '+₹' : '-₹',
                  ),
                ),
              ),
              if (_trackedAssets.isNotEmpty)
                SliverPadding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 4),
                  sliver: SliverToBoxAdapter(
                    child: Row(
                      children: [
                        Expanded(
                          child: SummaryCard(
                            title: 'Tracked Assets',
                            amount: _trackedAssetsTotal,
                            icon: Icons.account_balance,
                            color: theme.colorScheme.primary,
                            currencyFormat: _currencyFormat,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: SummaryCard(
                            title: 'Investments',
                            amount: _trackedInvestmentsTotal,
                            icon: Icons.trending_up,
                            color: theme.colorScheme.secondary,
                            currencyFormat: _currencyFormat,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              if (_trackedAssets.isNotEmpty)
                SliverPadding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 4),
                  sliver: SliverToBoxAdapter(
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Asset Balances',
                              style: theme.textTheme.titleSmall?.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 12),
                            ..._trackedAssets.take(5).map(_buildAssetRow),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              SliverPadding(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 4),
                sliver: SliverToBoxAdapter(
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '6-Month Overview',
                            style: theme.textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 12),
                          SizedBox(
                            height: 200,
                            child: MonthlyBarChart(
                                selectedMonth: _selectedMonth),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              if (_categoryTotals.isNotEmpty)
                SliverPadding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 4),
                  sliver: SliverToBoxAdapter(
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Expenses by Category',
                              style: theme.textTheme.titleSmall?.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 12),
                            SizedBox(
                              height: 220,
                              child: CategoryPieChart(
                                  categoryTotals: _categoryTotals),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              SliverPadding(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 4),
                sliver: SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 4, vertical: 8),
                    child: Row(
                      mainAxisAlignment:
                          MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Recent Transactions',
                          style: theme.textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        TextButton(
                          onPressed: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => TransactionsScreen(
                                    month: _selectedMonth),
                              ),
                            ).then((_) => _loadTransactions());
                          },
                          child: const Text('See All'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 0),
                sliver: SliverToBoxAdapter(
                  child: Card(
                    child: recentTransactions.isEmpty
                        ? const Padding(
                            padding: EdgeInsets.all(20),
                            child: Text('No transactions this month'),
                          )
                        : Column(
                            children: recentTransactions
                                .map(
                                  (t) => TransactionTile(
                                    transaction: t,
                                    currencyFormat: _currencyFormat,
                                  ),
                                )
                                .toList(),
                          ),
                  ),
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: 24)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Padding(
      padding: const EdgeInsets.all(40),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.account_balance_wallet_outlined,
            size: 80,
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
          const SizedBox(height: 16),
          Text(
            'No transactions',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Tap sync to import your bank SMS messages',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _syncing ? null : _sync,
            icon: const Icon(Icons.sync),
            label: const Text('Sync Now'),
          ),
        ],
      ),
    );
  }

  Widget _buildAssetRow(Transaction asset) {
    final balance = asset.assetBalance ?? 0.0;
    final label = switch (asset.assetType) {
      'epf' => 'EPF',
      'fixedDeposit' => 'Fixed Deposit',
      _ => asset.category,
    };
    final title =
        asset.assetId == null ? label : '$label • ${asset.assetId}';

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Text(
              title,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
          const SizedBox(width: 12),
          Text(
            '₹${_currencyFormat.format(balance)}',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}
