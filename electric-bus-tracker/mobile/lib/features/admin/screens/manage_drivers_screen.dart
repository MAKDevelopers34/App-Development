import 'package:flutter/material.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../widgets/admin_bottom_nav.dart';
import 'driver_registration_screen.dart';
import 'edit_driver_screen.dart';
import '../utils/admin_navigation.dart';

class ManageDriversScreen extends StatefulWidget {
  const ManageDriversScreen({super.key});

  @override
  State<ManageDriversScreen> createState() => _ManageDriversScreenState();
}

class _ManageDriversScreenState extends State<ManageDriversScreen> {
  final _searchController = TextEditingController();
  List<dynamic> _drivers = [];
  List<dynamic> _filtered = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadDrivers();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadDrivers() async {
    setState(() => _isLoading = true);
    try {
      final res = await ApiService.get('/admin/drivers');
      if (!mounted) return;
      setState(() {
        _drivers = res['drivers'] ?? [];
        _filtered = _drivers;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  void _search(String query) {
    final term = query.trim().toLowerCase();
    setState(() {
      _filtered = _drivers.where((raw) {
        final driver = Map<String, dynamic>.from(raw as Map);
        final profile = driver['profileInfo'] as Map?;
        final values = [
          profile?['fullName'],
          driver['username'],
          driver['userId'],
          driver['email'],
          profile?['phone'],
          profile?['licenseNo'],
        ].map((value) => value?.toString().toLowerCase() ?? '');
        return values.any((value) => value.contains(term));
      }).toList();
    });
  }

  Future<void> _openCreate() async {
    final created = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const DriverRegistrationScreen()),
    );
    if (created == true) _loadDrivers();
  }

  Future<void> _openEdit(Map<String, dynamic> driver) async {
    final updated = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => EditDriverScreen(driver: driver)),
    );
    if (updated == true) _loadDrivers();
  }

  Future<void> _removeDriver(Map<String, dynamic> driver) async {
    final profile = driver['profileInfo'] as Map?;
    final name =
        profile?['fullName']?.toString() ?? driver['username'] ?? 'driver';
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Remove Driver'),
        content: Text('Remove $name from the active driver list?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: AppTheme.redStatus),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      final id = driver['_id']?.toString() ?? driver['driverId']?.toString();
      if (id == null) return;
      final res = await ApiService.delete('/admin/drivers/$id');
      if (res['success'] != true) {
        await ApiService.post('/admin/drivers/$id/deactivate', {});
      }
      _loadDrivers();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not remove driver'),
          backgroundColor: AppTheme.redStatus,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return AdminNavigation.dashboardBackScope(
      context: context,
      child: Scaffold(
        backgroundColor: AppTheme.bgGrey,
        appBar: AppBar(
          title: const Text('Manage Drivers'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back_ios_new, size: 18),
            onPressed: () => AdminNavigation.goDashboard(context),
          ),
          actions: [
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: IconButton.filled(
                onPressed: _openCreate,
                icon: const Icon(Icons.person_add_alt_1_outlined, size: 18),
                tooltip: 'Register driver',
              ),
            ),
          ],
        ),
        body: Column(
          children: [
            _buildSearch(),
            Expanded(
              child: _isLoading
                  ? const Center(
                      child: CircularProgressIndicator(
                        color: AppTheme.primaryGreen,
                      ),
                    )
                  : RefreshIndicator(
                      color: AppTheme.primaryGreen,
                      onRefresh: _loadDrivers,
                      child: _filtered.isEmpty
                          ? const SingleChildScrollView(
                              physics: AlwaysScrollableScrollPhysics(),
                              child: SizedBox(
                                height: 420,
                                child: Center(
                                  child: Text(
                                    'No drivers found',
                                    style: TextStyle(color: AppTheme.textGrey),
                                  ),
                                ),
                              ),
                            )
                          : ListView.builder(
                              physics: const AlwaysScrollableScrollPhysics(),
                              padding: const EdgeInsets.fromLTRB(
                                12,
                                10,
                                12,
                                12,
                              ),
                              itemCount: _filtered.length,
                              itemBuilder: (context, index) {
                                return _buildDriverCard(
                                  Map<String, dynamic>.from(
                                    _filtered[index] as Map,
                                  ),
                                );
                              },
                            ),
                    ),
            ),
          ],
        ),
        bottomNavigationBar: const AdminBottomNav(selectedIndex: 1),
      ),
    );
  }

  Widget _buildSearch() {
    return Container(
      color: AppTheme.white,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: AppTheme.white,
          borderRadius: BorderRadius.circular(8),
          boxShadow: [
            BoxShadow(
              color: AppTheme.cardShadow,
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: TextField(
          controller: _searchController,
          onChanged: _search,
          style: const TextStyle(fontSize: 12),
          decoration: InputDecoration(
            hintText: 'Search by route or driver...',
            hintStyle: const TextStyle(fontSize: 12, color: AppTheme.textGrey),
            isDense: true,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 12,
              vertical: 10,
            ),
            suffixIcon: _searchController.text.isEmpty
                ? null
                : IconButton(
                    icon: const Icon(Icons.close, size: 16),
                    onPressed: () {
                      _searchController.clear();
                      _search('');
                    },
                  ),
          ),
        ),
      ),
    );
  }

  Widget _buildDriverCard(Map<String, dynamic> driver) {
    final profile = driver['profileInfo'] as Map?;
    final status = driver['status']?.toString() ?? 'Available';
    final isActive = driver['isActive'] == true && status != 'On-Leave';
    final badgeText = status == 'On-Leave'
        ? 'On Leave'
        : isActive
        ? 'Active'
        : 'Inactive';
    final name =
        profile?['fullName']?.toString() ??
        driver['username']?.toString() ??
        'Driver';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(8),
        boxShadow: [
          BoxShadow(
            color: AppTheme.cardShadow,
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppTheme.textDark,
                        fontSize: 12,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 8),
                    _smallLine(driver['email']),
                    _smallLine(profile?['phone']),
                    _smallLine('License: ${profile?['licenseNo'] ?? 'N/A'}'),
                  ],
                ),
              ),
              _StatusBadge(text: badgeText, active: isActive),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _SquareAction(
                color: AppTheme.orangeStatus,
                icon: Icons.edit_outlined,
                onTap: () => _openEdit(driver),
              ),
              const Spacer(),
              _SquareAction(
                color: AppTheme.redStatus,
                icon: Icons.close,
                onTap: () => _removeDriver(driver),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _smallLine(dynamic value) {
    return Text(
      value?.toString() ?? '',
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: const TextStyle(
        color: AppTheme.textDark,
        fontSize: 10,
        height: 1.25,
        fontWeight: FontWeight.w400,
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String text;
  final bool active;

  const _StatusBadge({required this.text, required this.active});

  @override
  Widget build(BuildContext context) {
    final bg = active ? AppTheme.lightGreen : const Color(0xFFFFE8E8);
    final fg = active ? AppTheme.primaryGreen : AppTheme.redStatus;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        text,
        style: TextStyle(color: fg, fontSize: 10, fontWeight: FontWeight.w800),
      ),
    );
  }
}

class _SquareAction extends StatelessWidget {
  final Color color;
  final IconData icon;
  final VoidCallback onTap;

  const _SquareAction({
    required this.color,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(7),
      child: Container(
        width: 28,
        height: 28,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(7),
        ),
        child: Icon(icon, color: AppTheme.white, size: 17),
      ),
    );
  }
}
