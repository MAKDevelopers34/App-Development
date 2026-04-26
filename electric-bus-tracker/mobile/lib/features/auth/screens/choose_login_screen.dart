import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import 'login_screen.dart';
import '../../tracking/screens/passenger_map_screen.dart';

class ChooseLoginScreen extends StatelessWidget {
  const ChooseLoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const SizedBox(height: 40),

              // Header
              const Icon(
                Icons.directions_bus,
                size: 64,
                color: AppTheme.primaryGreen,
              ),
              const SizedBox(height: 16),
              const Text(
                'Electric Bus Tracker',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textDark,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Choose Login Type',
                style: TextStyle(fontSize: 15, color: AppTheme.textGrey),
              ),

              const SizedBox(height: 60),

              // Driver Login card
              _LoginTypeCard(
                icon: Icons.person,
                title: 'Driver Login',
                subtitle: 'For registered bus drivers',
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const LoginScreen(role: 'driver'),
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Admin Login card
              _LoginTypeCard(
                icon: Icons.admin_panel_settings,
                title: 'Admin Login',
                subtitle: 'For system administrators',
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const LoginScreen(role: 'admin'),
                  ),
                ),
              ),

              const Spacer(),

              // Passenger option
              TextButton.icon(
                onPressed: () => Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (_) => const PassengerMapScreen()),
                ),
                icon: const Icon(
                  Icons.map_outlined,
                  color: AppTheme.primaryGreen,
                  size: 18,
                ),
                label: const Text(
                  'Continue as Passenger',
                  style: TextStyle(color: AppTheme.primaryGreen, fontSize: 14),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LoginTypeCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _LoginTypeCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE8E8E8)),
          boxShadow: [
            BoxShadow(
              color: AppTheme.cardShadow,
              blurRadius: 8,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: AppTheme.lightGreen,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(icon, color: AppTheme.primaryGreen, size: 26),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textDark,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppTheme.textGrey,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.arrow_forward_ios,
              size: 16,
              color: AppTheme.textGrey,
            ),
          ],
        ),
      ),
    );
  }
}
