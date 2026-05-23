import 'package:flutter/material.dart';
import '../services/db_service.dart';
import '../services/sms_service.dart';
import 'home_screen.dart';
import 'permission_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    // Wait for DB to be ready (it was already kicked off in main()).
    // Also enforce a minimum splash duration so the brand is visible.
    await Future.wait([
      DbService.database,
      Future.delayed(const Duration(milliseconds: 900)),
    ]);
    if (!mounted) return;

    final hasPermission = await SmsService.hasPermission();
    if (!mounted) return;

    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) =>
            hasPermission ? const HomeScreen() : const PermissionScreen(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 88,
              height: 88,
              decoration: BoxDecoration(
                color: theme.colorScheme.primary,
                borderRadius: BorderRadius.circular(22),
              ),
              child: Center(
                child: Text(
                  'H',
                  style: TextStyle(
                    fontSize: 54,
                    fontWeight: FontWeight.w900,
                    color: theme.colorScheme.onPrimary,
                    height: 1,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 28),
            Text(
              'HYT',
              style: theme.textTheme.headlineLarge?.copyWith(
                fontWeight: FontWeight.w900,
                letterSpacing: 5,
              ),
            ),
            Text(
              'MONEY',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w600,
                letterSpacing: 8,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Your financial companion',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 56),
            SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                color: theme.colorScheme.primary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
