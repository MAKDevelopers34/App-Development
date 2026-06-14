import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../screens/manage_drivers_screen.dart';
import '../screens/manage_duties_screen.dart';
import '../screens/manage_buses_screen.dart';
import '../screens/manage_routes_screen.dart';

class AdminBottomNav extends StatelessWidget {
  final int selectedIndex;
  final bool allowSelectedTap;

  const AdminBottomNav({
    super.key,
    this.selectedIndex = -1,
    this.allowSelectedTap = false,
  });

  void _openSection(BuildContext context, int index) {
    if (!allowSelectedTap && index == selectedIndex) return;

    Widget screen;
    switch (index) {
      case 0:
        screen = const ManageDutiesScreen();
        break;
      case 1:
        screen = const ManageDriversScreen();
        break;
      case 2:
        screen = const ManageBusesScreen();
        break;
      default:
        screen = const ManageRoutesScreen();
    }

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => screen),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        color: AppTheme.white,
        padding: const EdgeInsets.fromLTRB(10, 6, 10, 8),
        child: Row(
          children: [
            _AdminNavButton(
              icon: Icons.assignment_outlined,
              label: 'Duty',
              selected: selectedIndex == 0,
              onTap: () => _openSection(context, 0),
            ),
            const SizedBox(width: 4),
            _AdminNavButton(
              icon: Icons.people_outline,
              label: 'Driver',
              selected: selectedIndex == 1,
              onTap: () => _openSection(context, 1),
            ),
            const SizedBox(width: 4),
            _AdminNavButton(
              icon: Icons.directions_bus_outlined,
              label: 'Bus',
              selected: selectedIndex == 2,
              onTap: () => _openSection(context, 2),
            ),
            const SizedBox(width: 4),
            _AdminNavButton(
              icon: Icons.route,
              label: 'Route',
              selected: selectedIndex == 3,
              onTap: () => _openSection(context, 3),
            ),
          ],
        ),
      ),
    );
  }
}

class _AdminNavButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _AdminNavButton({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          height: 50,
          decoration: BoxDecoration(
            color: selected ? AppTheme.primaryGreen : AppTheme.darkGreen,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: AppTheme.white, size: 17),
              const SizedBox(height: 3),
              Text(
                label,
                style: const TextStyle(
                  color: AppTheme.white,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
