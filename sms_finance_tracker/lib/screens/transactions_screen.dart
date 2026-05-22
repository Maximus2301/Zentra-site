import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/transaction.dart';
import '../services/db_service.dart';
import '../theme/app_theme.dart';
import '../widgets/transaction_tile.dart';

class TransactionsScreen extends StatefulWidget {
  final DateTime month;

  const TransactionsScreen({super.key, required this.month});

  @override
  State<TransactionsScreen> createState() => _TransactionsScreenState();
}

class _TransactionsScreenState extends State<TransactionsScreen> {
  List<Transaction> _transactions = [];
  List<Transaction> _filtered = [];
  bool _loading = true;
  bool _searchActive = false;
  String _searchQuery = '';
  String _selectedCategory = 'All';
  String _selectedType = 'all';

  final NumberFormat _currencyFormat = NumberFormat('#,##,##0.00', 'en_IN');
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadTransactions();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadTransactions() async {
    setState(() => _loading = true);
    final data = await DbService.getTransactionsByMonth(
        widget.month.year, widget.month.month);
    if (mounted) {
      setState(() {
        _transactions = data;
        _loading = false;
      });
      _applyFilters();
    }
  }

  void _applyFilters() {
    List<Transaction> result = List.from(_transactions);

    if (_selectedType == 'expense') {
      result =
          result.where((t) => t.type == TransactionType.expense).toList();
    } else if (_selectedType == 'income') {
      result =
          result.where((t) => t.type == TransactionType.income).toList();
    } else if (_selectedType == 'transfer') {
      result =
          result.where((t) => t.type == TransactionType.transfer).toList();
    }

    if (_selectedCategory != 'All') {
      result = result
          .where((t) => t.category == _selectedCategory)
          .toList();
    }

    if (_searchQuery.isNotEmpty) {
      final q = _searchQuery.toLowerCase();
      result = result.where((t) {
        return t.merchant.toLowerCase().contains(q) ||
            t.category.toLowerCase().contains(q) ||
            t.subcategory.toLowerCase().contains(q) ||
            t.source.toLowerCase().contains(q);
      }).toList();
    }

    setState(() => _filtered = result);
  }

  Future<void> _deleteTransaction(Transaction t) async {
    if (t.id == null) return;
    await DbService.deleteTransaction(t.id!);
    await _loadTransactions();
  }

  List<String> get _categories {
    final cats = _transactions.map((t) => t.category).toSet().toList()..sort();
    return ['All', ...cats];
  }

  double get _filteredTotal {
    if (_selectedType == 'transfer') {
      return _filtered.fold(0.0, (sum, t) => sum + t.amount);
    }
    if (_selectedType == 'income' || _selectedType == 'expense') {
      return _filtered.fold(0.0, (sum, t) => sum + t.amount);
    }
    return _filtered.fold(0.0, (sum, t) {
      if (t.type == TransactionType.income) return sum + t.amount;
      if (t.type == TransactionType.expense) return sum - t.amount;
      return sum;
    });
  }

  String get _filteredTotalLabel {
    if (_selectedType == 'transfer') return 'Tracked Value';
    if (_selectedType == 'all') return 'Net Cash Flow';
    return 'Total';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final monthLabel =
        DateFormat('MMM yyyy').format(widget.month);

    return Scaffold(
      appBar: AppBar(
        title: _searchActive
            ? TextField(
                controller: _searchController,
                autofocus: true,
                decoration: const InputDecoration(
                  hintText: 'Search transactions...',
                  border: InputBorder.none,
                ),
                onChanged: (value) {
                  setState(() => _searchQuery = value);
                  _applyFilters();
                },
              )
            : Text('Transactions - $monthLabel'),
        actions: [
          IconButton(
            icon: Icon(_searchActive ? Icons.close : Icons.search),
            onPressed: () {
              setState(() {
                _searchActive = !_searchActive;
                if (!_searchActive) {
                  _searchQuery = '';
                  _searchController.clear();
                  _applyFilters();
                }
              });
            },
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                _buildTypeSelector(theme),
                _buildCategoryFilter(theme),
                _buildSummaryHeader(theme),
                Expanded(
                  child: _filtered.isEmpty
                      ? _buildEmptyState(theme)
                      : ListView.builder(
                          itemCount: _filtered.length,
                          itemBuilder: (context, index) {
                            final t = _filtered[index];
                            return TransactionTile(
                              transaction: t,
                              currencyFormat: _currencyFormat,
                              onDelete: () => _deleteTransaction(t),
                            );
                          },
                        ),
                ),
              ],
            ),
    );
  }

  Widget _buildTypeSelector(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          for (final type in ['all', 'expense', 'income', 'transfer'])
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text(
                  type == 'all'
                      ? 'All'
                      : type == 'expense'
                          ? 'Expenses'
                          : type == 'income'
                              ? 'Income'
                              : 'Investments',
                ),
                selected: _selectedType == type,
                onSelected: (_) {
                  setState(() => _selectedType = type);
                  _applyFilters();
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildCategoryFilter(ThemeData theme) {
    return SizedBox(
      height: 44,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        itemCount: _categories.length,
        itemBuilder: (context, index) {
          final cat = _categories[index];
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilterChip(
              label: Text(cat),
              selected: _selectedCategory == cat,
              onSelected: (_) {
                setState(() => _selectedCategory = cat);
                _applyFilters();
              },
            ),
          );
        },
      ),
    );
  }

  Widget _buildSummaryHeader(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            '${_filtered.length} transaction${_filtered.length == 1 ? '' : 's'}',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          Text(
            '$_filteredTotalLabel: ₹${_currencyFormat.format(_filteredTotal)}',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.receipt_long_outlined,
            size: 64,
            color: theme.colorScheme.outlineVariant,
          ),
          const SizedBox(height: 12),
          Text(
            'No transactions match',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 4),
          Text(
            'Try adjusting your filters',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}
