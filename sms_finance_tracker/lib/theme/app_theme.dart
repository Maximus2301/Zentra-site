import 'package:flutter/material.dart';

class AppTheme {
  static const Color _primaryBlue = Color(0xFF1565C0);

  static ThemeData light() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: _primaryBlue,
        brightness: Brightness.light,
      ),
      cardTheme: CardTheme(
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
      ),
      appBarTheme: const AppBarTheme(
        elevation: 0,
        scrolledUnderElevation: 0,
      ),
    );
  }

  static ThemeData dark() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: _primaryBlue,
        brightness: Brightness.dark,
      ),
      cardTheme: CardTheme(
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
      ),
      appBarTheme: const AppBarTheme(
        elevation: 0,
        scrolledUnderElevation: 0,
      ),
    );
  }

  static Color incomeColor(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return brightness == Brightness.dark
        ? const Color(0xFF66BB6A)
        : const Color(0xFF2E7D32);
  }

  static Color expenseColor(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return brightness == Brightness.dark
        ? const Color(0xFFEF5350)
        : const Color(0xFFC62828);
  }

  static const List<Color> categoryColors = [
    Color(0xFF1565C0), // Essential - blue
    Color(0xFFE65100), // Food Delivery - orange
    Color(0xFF6A1B9A), // Lifestyle - purple
    Color(0xFF2E7D32), // Rent & Housing - green
    Color(0xFF00695C), // Transport - teal
    Color(0xFF827717), // Education - lime
    Color(0xFF4527A0), // Investment - deep purple
    Color(0xFF1B5E20), // Income - dark green
    Color(0xFF37474F), // Others - blue grey
  ];

  static const Map<String, String> categoryEmojis = {
    'Essential': '🏠',
    'Food Delivery': '🛵',
    'Lifestyle': '🎭',
    'Rent & Housing': '🏡',
    'Transport': '🚗',
    'Education': '📚',
    'Investment': '📈',
    'Income': '💰',
    'Others': '📦',
  };
}
