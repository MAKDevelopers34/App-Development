import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'features/tracking/screens/passenger_map_screen.dart';

void main() {
  runApp(const ElectricBusTrackerApp());
}

class ElectricBusTrackerApp extends StatelessWidget {
  const ElectricBusTrackerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Electric Bus Tracker',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: const PassengerMapScreen(),
    );
  }
}
