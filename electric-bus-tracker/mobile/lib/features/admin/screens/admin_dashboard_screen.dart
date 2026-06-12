import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import 'admin_profile_screen.dart';
import 'manage_duties_screen.dart';
import 'manage_drivers_screen.dart';
import 'manage_routes_screen.dart';
import 'reports_screen.dart';

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  int _currentNavIndex = 0;
  Map<String, dynamic>? _stats;
  List<dynamic> _routes = [];
  List<dynamic> _activeBuses = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final results = await Future.wait([
        ApiService.get('/admin/dashboard'),
        ApiService.get('/routes'),
        ApiService.get('/gps/active-buses'),
      ]);

      setState(() {
        _stats = results[0]['stats'];
        _routes = results[1]['routes'] ?? [];
        _activeBuses = results[2]['buses'] ?? [];
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      body: SafeArea(
        child: Column(
          children: [
            _buildTopBar(),
            Expanded(
              child: _isLoading
                  ? const Center(
                      child: CircularProgressIndicator(
                        color: AppTheme.primaryGreen,
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _loadData,
                      color: AppTheme.primaryGreen,
                      child: SingleChildScrollView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Stats row
                            _buildStatsRow(),
                            const SizedBox(height: 20),

                            // Routes grid header
                            Row(
                              children: [
                                const Text(
                                  'Active Routes',
                                  style: TextStyle(
                                    fontSize: 15,
                                    fontWeight: FontWeight.w600,
                                    color: AppTheme.textDark,
                                  ),
                                ),
                                const Spacer(),
                                Text(
                                  '${_routes.length} routes',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: AppTheme.textGrey,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),

                            // Routes grid — matching design
                            GridView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              gridDelegate:
                                  const SliverGridDelegateWithFixedCrossAxisCount(
                                    crossAxisCount: 2,
                                    crossAxisSpacing: 10,
                                    mainAxisSpacing: 10,
                                    childAspectRatio: 1.4,
                                  ),
                              itemCount: _routes.length,
                              itemBuilder: (context, index) =>
                                  _buildRouteCard(_routes[index], index),
                            ),
                          ],
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _buildAdminBottomNav(),
    );
  }

  Widget _buildTopBar() {
    return Container(
      color: AppTheme.white,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
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
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: AppTheme.primaryGreen,
            ),
          ),
          const Spacer(),
          // Notification bell
          Stack(
            children: [
              const Icon(
                Icons.notifications_outlined,
                color: AppTheme.textGrey,
              ),
              if ((_stats?['activeBuses'] ?? 0) > 0)
                Positioned(
                  right: 0,
                  top: 0,
                  child: Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: AppTheme.redStatus,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(width: 12),
          // Close/logout quick button
          GestureDetector(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const AdminProfileScreen()),
            ),
            child: Container(
              width: 32,
              height: 32,
              decoration: const BoxDecoration(
                color: AppTheme.lightGreen,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.person,
                color: AppTheme.primaryGreen,
                size: 18,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsRow() {
    return Row(
      children: [
        _statBox(
          'Active\nBuses',
          '${_activeBuses.length}',
          AppTheme.primaryGreen,
          Icons.directions_bus,
        ),
        const SizedBox(width: 10),
        _statBox(
          'Total\nDrivers',
          '${_stats?['totalDrivers'] ?? 0}',
          AppTheme.orangeStatus,
          Icons.people,
        ),
        const SizedBox(width: 10),
        _statBox(
          'Today\nDuties',
          '${_stats?['todayDuties'] ?? 0}',
          Colors.blue,
          Icons.assignment,
        ),
        const SizedBox(width: 10),
        _statBox(
          'Completed',
          '${_stats?['completedDuties'] ?? 0}',
          AppTheme.darkGreen,
          Icons.check_circle,
        ),
      ],
    );
  }

  Widget _statBox(String label, String value, Color color, IconData icon) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: AppTheme.white,
          borderRadius: BorderRadius.circular(12),
          boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 4)],
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(height: 4),
            Text(
              value,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
            Text(
              label,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 9, color: AppTheme.textGrey),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRouteCard(Map<String, dynamic> route, int index) {
    // Check if any active bus is on this route
    final hasActiveBus = _activeBuses.any(
      (bus) => bus['routeId'] == route['routeId'],
    );

    final stops = route['stops'] as List? ?? [];

    return GestureDetector(
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const ManageRoutesScreen()),
      ),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppTheme.white,
          borderRadius: BorderRadius.circular(14),
          boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 6)],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Route name
            Text(
              route['routeName'] ?? '',
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: AppTheme.textDark,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const Spacer(),

            // Bus dots — show active buses
            Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: hasActiveBus
                        ? AppTheme.primaryGreen
                        : const Color(0xFFDDDDDD),
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 4),
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: hasActiveBus
                        ? AppTheme.primaryGreen.withValues(alpha: 0.5)
                        : const Color(0xFFDDDDDD),
                    shape: BoxShape.circle,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),

            // Bottom info
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${stops.length} stops',
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppTheme.textGrey,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: hasActiveBus
                        ? AppTheme.primaryGreen
                        : const Color(0xFFDDDDDD),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    hasActiveBus ? 'Active' : 'Idle',
                    style: TextStyle(
                      color: hasActiveBus ? AppTheme.white : AppTheme.textGrey,
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAdminBottomNav() {
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
          switch (index) {
            case 1:
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ManageDutiesScreen()),
              ).then((_) => setState(() => _currentNavIndex = 0));
              break;
            case 2:
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ManageDriversScreen()),
              ).then((_) => setState(() => _currentNavIndex = 0));
              break;
            case 3:
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ReportsScreen()),
              ).then((_) => setState(() => _currentNavIndex = 0));
              break;
            case 4:
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const AdminProfileScreen()),
              ).then((_) => setState(() => _currentNavIndex = 0));
              break;
          }
        },
        backgroundColor: AppTheme.white,
        selectedItemColor: AppTheme.primaryGreen,
        unselectedItemColor: AppTheme.textGrey,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        selectedFontSize: 10,
        unselectedFontSize: 10,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard_outlined),
            activeIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.assignment_outlined),
            activeIcon: Icon(Icons.assignment),
            label: 'Duties',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.people_outline),
            activeIcon: Icon(Icons.people),
            label: 'Drivers',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.bar_chart_outlined),
            activeIcon: Icon(Icons.bar_chart),
            label: 'Reports',
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
