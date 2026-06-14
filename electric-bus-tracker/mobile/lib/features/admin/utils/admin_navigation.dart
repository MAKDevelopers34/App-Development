import 'package:flutter/material.dart';

import '../screens/admin_dashboard_screen.dart';

class AdminNavigation {
  const AdminNavigation._();

  static void goDashboard(BuildContext context) {
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => const AdminDashboardScreen()),
      (route) => false,
    );
  }

  static Widget dashboardBackScope({
    required BuildContext context,
    required Widget child,
  }) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          goDashboard(context);
        }
      },
      child: child,
    );
  }
}
