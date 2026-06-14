import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../widgets/admin_bottom_nav.dart';
import 'add_duty_screen.dart';
import 'edit_duty_screen.dart';
import '../utils/admin_navigation.dart';

class ManageDutiesScreen extends StatefulWidget {
  const ManageDutiesScreen({super.key});

  @override
  State<ManageDutiesScreen> createState() => _ManageDutiesScreenState();
}

class _ManageDutiesScreenState extends State<ManageDutiesScreen> {
  final _searchController = TextEditingController();
  List<dynamic> _duties = [];
  List<dynamic> _filtered = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadDuties();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadDuties() async {
    setState(() => _isLoading = true);
    try {
      final res = await ApiService.get('/admin/duties');
      if (!mounted) return;
      setState(() {
        _duties = res['duties'] ?? [];
        _filtered = _duties;
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
      _filtered = _duties.where((raw) {
        final duty = Map<String, dynamic>.from(raw as Map);
        final driver = duty['driver'] as Map?;
        final bus = duty['bus'] as Map?;
        final values = [
          duty['route'],
          driver?['username'],
          driver?['profileInfo']?['fullName'],
          bus?['busNumber'],
          duty['scheduledStartTime'],
        ].map((value) => value?.toString().toLowerCase() ?? '');
        return values.any((value) => value.contains(term));
      }).toList();
    });
  }

  Future<void> _openAddDuty() async {
    final created = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const AddDutyScreen()),
    );
    if (created == true) _loadDuties();
  }

  Future<void> _openEditDuty(Map<String, dynamic> duty) async {
    final updated = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => EditDutyScreen(duty: duty)),
    );
    if (updated == true) _loadDuties();
  }

  Map<String, List<Map<String, dynamic>>> get _groupedDuties {
    final groups = <String, List<Map<String, dynamic>>>{};
    for (final rawDuty in _filtered) {
      final duty = Map<String, dynamic>.from(rawDuty as Map);
      final routeName = duty['route']?.toString() ?? 'Unassigned Route';
      groups.putIfAbsent(routeName, () => []).add(duty);
    }
    return groups;
  }

  @override
  Widget build(BuildContext context) {
    return AdminNavigation.dashboardBackScope(
      context: context,
      child: Scaffold(
        backgroundColor: AppTheme.bgGrey,
        appBar: AppBar(
          title: const Text('Manage Duties'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back_ios_new, size: 18),
            onPressed: () => AdminNavigation.goDashboard(context),
          ),
          actions: [
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: IconButton.filled(
                onPressed: _openAddDuty,
                icon: const Icon(Icons.add, size: 18),
                tooltip: 'Add duty',
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
                      onRefresh: _loadDuties,
                      child: _groupedDuties.isEmpty
                          ? const SingleChildScrollView(
                              physics: AlwaysScrollableScrollPhysics(),
                              child: SizedBox(
                                height: 420,
                                child: Center(
                                  child: Text(
                                    'No duties found',
                                    style: TextStyle(color: AppTheme.textGrey),
                                  ),
                                ),
                              ),
                            )
                          : ListView(
                              physics: const AlwaysScrollableScrollPhysics(),
                              padding: const EdgeInsets.fromLTRB(
                                12,
                                10,
                                12,
                                12,
                              ),
                              children: _groupedDuties.entries
                                  .map(_buildRouteGroup)
                                  .toList(),
                            ),
                    ),
            ),
          ],
        ),
        bottomNavigationBar: const AdminBottomNav(selectedIndex: 0),
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

  Widget _buildRouteGroup(MapEntry<String, List<Map<String, dynamic>>> group) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: AppTheme.primaryGreen,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            group.key.toUpperCase(),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: AppTheme.white,
              fontSize: 11,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
        ...group.value.map(_buildDutyCard),
        const SizedBox(height: 10),
      ],
    );
  }

  Widget _buildDutyCard(Map<String, dynamic> duty) {
    final driver = duty['driver'] as Map?;
    final bus = duty['bus'] as Map?;
    final profile = driver?['profileInfo'] as Map?;
    final name =
        profile?['fullName']?.toString() ??
        driver?['username']?.toString() ??
        'Driver';

    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(8),
        boxShadow: [
          BoxShadow(
            color: AppTheme.cardShadow,
            blurRadius: 7,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
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
                const SizedBox(height: 7),
                Text(
                  driver?['email']?.toString() ?? '',
                  style: const TextStyle(
                    color: AppTheme.textGrey,
                    fontSize: 10,
                    height: 1.2,
                  ),
                ),
                Text(
                  profile?['phone']?.toString() ?? '',
                  style: const TextStyle(
                    color: AppTheme.textGrey,
                    fontSize: 10,
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Bus:\n${bus?['busNumber'] ?? 'N/A'}',
                  style: const TextStyle(
                    color: AppTheme.textDark,
                    fontSize: 10,
                    height: 1.15,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              _IconAction(
                color: AppTheme.orangeStatus,
                icon: Icons.edit_outlined,
                onTap: () => _openEditDuty(duty),
              ),
              const SizedBox(height: 42),
              Text(
                _formatClock(duty['scheduledStartTime']),
                style: const TextStyle(
                  color: AppTheme.primaryGreen,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatClock(dynamic value) {
    final time = value?.toString() ?? '';
    final parts = time.split(':');
    if (parts.length < 2) return time;
    final hour = int.tryParse(parts[0]);
    final minute = int.tryParse(parts[1]);
    if (hour == null || minute == null) return time;
    return DateFormat.jm().format(DateTime(2026, 1, 1, hour, minute));
  }
}

class _IconAction extends StatelessWidget {
  final Color color;
  final IconData icon;
  final VoidCallback onTap;

  const _IconAction({
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
