import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/transaction.dart';
import '../theme/app_theme.dart';

class TransactionTile extends StatelessWidget {
  final Transaction transaction;
  final NumberFormat currencyFormat;
  final VoidCallback? onDelete;

  const TransactionTile({
    super.key,
    required this.transaction,
    required this.currencyFormat,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final t = transaction;
    final isIncome = t.type == TransactionType.income;
    final isTransfer = t.type == TransactionType.transfer;
    final amountColor = isIncome
        ? AppTheme.incomeColor(context)
        : isTransfer
            ? Theme.of(context).colorScheme.primary
            : AppTheme.expenseColor(context);
    final emoji =
        AppTheme.categoryEmojis[t.category] ?? '📦';
    final dateStr = DateFormat('dd MMM').format(t.date);
    final subtitleParts = <String>[
      t.subcategory,
      dateStr,
      if (t.source.isNotEmpty) t.source,
      if (t.assetBalance != null)
        'Balance ₹${currencyFormat.format(t.assetBalance)}',
    ];
    final subtitle = subtitleParts.join(' • ');
    final amountPrefix = isIncome
        ? '+'
        : isTransfer
            ? ''
            : '-';

    final tile = ListTile(
      leading: CircleAvatar(
        backgroundColor:
            Theme.of(context).colorScheme.surfaceContainerHighest,
        child: Text(emoji, style: const TextStyle(fontSize: 18)),
      ),
      title: Text(
        t.merchant.isNotEmpty ? t.merchant : t.category,
        style: const TextStyle(fontWeight: FontWeight.w600),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        subtitle,
        style: TextStyle(
          fontSize: 12,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      trailing: Text(
        '$amountPrefix₹${currencyFormat.format(t.amount)}',
        style: TextStyle(
          color: amountColor,
          fontWeight: FontWeight.w700,
          fontSize: 14,
        ),
      ),
    );

    if (onDelete != null) {
      return Dismissible(
        key: Key('txn_${t.id}_${t.date.millisecondsSinceEpoch}'),
        direction: DismissDirection.endToStart,
        background: Container(
          alignment: Alignment.centerRight,
          padding: const EdgeInsets.only(right: 20),
          color: Theme.of(context).colorScheme.errorContainer,
          child: Icon(
            Icons.delete_outline,
            color: Theme.of(context).colorScheme.onErrorContainer,
          ),
        ),
        confirmDismiss: (_) async {
          return await showDialog<bool>(
            context: context,
            builder: (ctx) => AlertDialog(
              title: const Text('Delete Transaction'),
              content:
                  const Text('Are you sure you want to delete this transaction?'),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx, false),
                  child: const Text('Cancel'),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(ctx, true),
                  child: const Text('Delete'),
                ),
              ],
            ),
          );
        },
        onDismissed: (_) => onDelete!(),
        child: tile,
      );
    }

    return tile;
  }
}
