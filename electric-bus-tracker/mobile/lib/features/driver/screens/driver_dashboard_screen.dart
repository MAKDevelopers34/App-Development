import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../../core/widgets/schematic_bus_map.dart';
import 'driver_profile_screen.dart';
import 'today_duty_screen.dart';
import 'monthly_schedule_screen.dart';
import '../../auth/screens/choose_login_screen.dart';

class DriverDashboardScreen extends StatefulWidget {
  const DriverDashboardScreen({super.key});

  @override
  State<DriverDashboardScreen> createState() => _DriverDashboardScreenState();
}

class _DriverDashboardScreenState extends State<DriverDashboardScreen> {
  int _currentNavIndex = 0;
  Map<String, dynamic>? _todayDuty;
  List<dynamic> _activeBuses = [];
  String _username = '';

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() => _username = prefs.getString('username') ?? '');

    try {
      final dutyRes = await ApiService.get('/duty/today');
      final busRes = await ApiService.get('/gps/active-buses');

      setState(() {
        _todayDuty = dutyRes['duty'];
        _activeBuses = busRes['buses'] as List? ?? [];
      });
    } catch (e) {
      debugPrint('Load error: $e');
    }
  }

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    if (!mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => const ChooseLoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      body: SafeArea(
        child: Stack(
          children: [
            SchematicBusMap(buses: _activeBuses),
            Positioned(top: 0, left: 0, right: 0, child: _buildTopBar()),
            Positioned(
              top: 86,
              left: 12,
              right: 12,
              child: _buildLiveSummary(),
            ),
            if (_todayDuty != null)
              Positioned(
                bottom: 80,
                left: 12,
                right: 12,
                child: _buildDutyCard(),
              ),
          ],
        ),
      ),
      bottomNavigationBar: _buildDriverBottomNav(),
    );
  }

  Widget _buildTopBar() {
    return Container(
      margin: const EdgeInsets.all(12),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 8)],
      ),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: const BoxDecoration(
              color: AppTheme.primaryGreen,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          const Text(
            'Electric Bus Tracking',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: AppTheme.primaryGreen,
            ),
          ),
          const Spacer(),
          Text(
            'Hi, $_username',
            style: const TextStyle(fontSize: 12, color: AppTheme.textGrey),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: _logout,
            child: const Icon(
              Icons.logout,
              color: AppTheme.textGrey,
              size: 18,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLiveSummary() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 6)],
      ),
      child: Row(
        children: [
          const Icon(
            Icons.sensors,
            color: AppTheme.primaryGreen,
            size: 18,
          ),
          const SizedBox(width: 8),
          Text(
            '${_activeBuses.length} live buses',
            style: const TextStyle(
              color: AppTheme.textDark,
              fontWeight: FontWeight.w600,
              fontSize: 13,
            ),
          ),
          const Spacer(),
          GestureDetector(
            onTap: _loadData,
            child: const Icon(
              Icons.refresh,
              color: AppTheme.primaryGreen,
              size: 18,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDutyCard() {
    if (_todayDuty == null) return const SizedBox();
    final bus = _todayDuty!['bus'];
    final status = _todayDuty!['status'];

    Color statusColor;
    if (status == 'started') {
      statusColor = AppTheme.primaryGreen;
    } else if (status == 'completed') {
      statusColor = AppTheme.textGrey;
    } else {
      statusColor = AppTheme.orangeStatus;
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 10)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                'Today\'s Duty',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textDark,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  status.toString().toUpperCase(),
                  style: TextStyle(
                    color: statusColor,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const Icon(
                Icons.directions_bus,
                color: AppTheme.primaryGreen,
                size: 16,
              ),
              const SizedBox(width: 6),
              Text(
                'Bus: ${bus?['busNumber'] ?? 'N/A'}',
                style: const TextStyle(fontSize: 13, color: AppTheme.textDark),
              ),
              const SizedBox(width: 16),
              const Icon(Icons.route, color: AppTheme.primaryGreen, size: 16),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  'Route: ${_todayDuty!['route']}',
                  style: const TextStyle(
                    fontSize: 13,
                    color: AppTheme.textDark,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const Icon(Icons.access_time, color: AppTheme.textGrey, size: 14),
              const SizedBox(width: 4),
              Text(
                '${_todayDuty!['scheduledStartTime']} - '
                '${_todayDuty!['scheduledEndTime']}',
                style: const TextStyle(fontSize: 12, color: AppTheme.textGrey),
              ),
              const Spacer(),
              GestureDetector(
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const TodayDutyScreen()),
                ).then((_) => _loadData()),
                child: const Text(
                  'Show Duty',
                  style: TextStyle(
                    color: AppTheme.primaryGreen,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildDriverBottomNav() {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        boxShadow: [
          BoxShadow(
            color: AppTheme.cardShadow,
            blurRadius: 10,
            offset: const Offset(0, -3),
          ),
        ],
      ),
      child: BottomNavigationBar(
        currentIndex: _currentNavIndex,
        onTap: (index) {
          setState(() => _currentNavIndex = index);
          if (index == 1) {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const TodayDutyScreen()),
            ).then((_) => _loadData());
          } else if (index == 2) {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const MonthlyScheduleScreen()),
            );
          } else if (index == 3) {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const DriverProfileScreen()),
            );
          }
        },
        backgroundColor: AppTheme.white,
        selectedItemColor: AppTheme.primaryGreen,
        unselectedItemColor: AppTheme.textGrey,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.map_outlined),
            activeIcon: Icon(Icons.map),
            label: 'Dashboard',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.assignment_outlined),
            activeIcon: Icon(Icons.assignment),
            label: 'Duty',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.calendar_month_outlined),
            activeIcon: Icon(Icons.calendar_month),
            label: 'Schedule',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person_outline),
            activeIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
