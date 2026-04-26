import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/theme/app_theme.dart';
import 'choose_login_screen.dart';
import '../../tracking/screens/passenger_map_screen.dart';
import '../../driver/screens/driver_dashboard_screen.dart';
import '../../admin/screens/admin_dashboard_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnim;
  late Animation<double> _scaleAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _fadeAnim = Tween<double>(
      begin: 0,
      end: 1,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeIn));
    _scaleAnim = Tween<double>(
      begin: 0.85,
      end: 1,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));
    _controller.forward();
    _navigateAfterDelay();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _navigateAfterDelay() async {
    await Future.delayed(const Duration(seconds: 3));
    if (!mounted) return;

    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('token');
    final role = prefs.getString('role');

    if (token == null) {
      _goTo(const ChooseLoginScreen());
    } else if (role == 'driver') {
      _goTo(const DriverDashboardScreen());
    } else if (role == 'admin') {
      _goTo(const AdminDashboardScreen());
    } else {
      _goTo(const PassengerMapScreen());
    }
  }

  void _goTo(Widget screen) {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => screen),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.primaryGreen,
      body: FadeTransition(
        opacity: _fadeAnim,
        child: ScaleTransition(
          scale: _scaleAnim,
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Bus icon
                Container(
                  width: 120,
                  height: 120,
                  decoration: BoxDecoration(
                    color: AppTheme.white,
                    borderRadius: BorderRadius.circular(30),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.15),
                        blurRadius: 20,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.directions_bus,
                    size: 64,
                    color: AppTheme.primaryGreen,
                  ),
                ),
                const SizedBox(height: 28),
                const Text(
                  'Electric Bus Tracker',
                  style: TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.white,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Mianwali District — Pakistan',
                  style: TextStyle(
                    fontSize: 14,
                    color: AppTheme.white.withValues(alpha: 0.85),
                    letterSpacing: 0.3,
                  ),
                ),
                const SizedBox(height: 60),
                SizedBox(
                  width: 32,
                  height: 32,
                  child: CircularProgressIndicator(
                    color: AppTheme.white.withValues(alpha: 0.7),
                    strokeWidth: 2.5,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
