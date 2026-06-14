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
  late DateTime _selectedDate;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _selectedDate = _dateOnly(DateTime.now());
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
        _applyFilters();
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  void _applyFilters() {
    final term = _searchController.text.trim().toLowerCase();
    _filtered = _duties.where((raw) {
      final duty = Map<String, dynamic>.from(raw as Map);
      final scheduledDate = _parseDate(duty['scheduledDate']);
      if (scheduledDate == null || !_sameDay(scheduledDate, _selectedDate)) {
        return false;
      }

      if (term.isEmpty) return true;

      final driver = duty['driver'] as Map?;
      final bus = duty['bus'] as Map?;
      final values = [
        duty['route'],
        driver?['username'],
        driver?['email'],
        driver?['profileInfo']?['fullName'],
        driver?['profileInfo']?['phone'],
        bus?['busNumber'],
        duty['scheduledStartTime'],
      ].map((value) => value?.toString().toLowerCase() ?? '');
      return values.any((value) => value.contains(term));
    }).toList();
  }

  void _search(String query) {
    setState(_applyFilters);
  }

  Future<void> _pickDate() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2020),
      lastDate: DateTime(2035),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: Theme.of(context).colorScheme.copyWith(
              primary: AppTheme.primaryGreen,
            ),
          ),
          child: child!,
        );
      },
    );

    if (date == null) return;
    setState(() {
      _selectedDate = _dateOnly(date);
      _applyFilters();
    });
  }

  void _moveDate(int days) {
    setState(() {
      _selectedDate = _dateOnly(_selectedDate.add(Duration(days: days)));
      _applyFilters();
    });
  }

  void _jumpToday() {
    setState(() {
      _selectedDate = _dateOnly(DateTime.now());
      _applyFilters();
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
      child: Column(
        children: [
          Container(
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
                hintStyle: const TextStyle(
                  fontSize: 12,
                  color: AppTheme.textGrey,
                ),
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
          const SizedBox(height: 8),
          Row(
            children: [
              _DateNavButton(
                icon: Icons.chevron_left,
                onTap: () => _moveDate(-1),
              ),
              Expanded(
                child: InkWell(
                  onTap: _pickDate,
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    height: 42,
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    decoration: BoxDecoration(
                      color: AppTheme.lightGreen,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: AppTheme.primaryGreen.withValues(alpha: 0.18),
                      ),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.calendar_month_outlined,
                          color: AppTheme.primaryGreen,
                          size: 17,
                        ),
                        const SizedBox(width: 7),
                        Flexible(
                          child: Text(
                            _selectedDateLabel,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: AppTheme.primaryGreen,
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              _DateNavButton(
                icon: Icons.chevron_right,
                onTap: () => _moveDate(1),
              ),
              const SizedBox(width: 6),
              InkWell(
                onTap: _jumpToday,
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  height: 42,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryGreen,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  alignment: Alignment.center,
                  child: const Text(
                    'Today',
                    style: TextStyle(
                      color: AppTheme.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
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
    final status = duty['status']?.toString().toLowerCase() ?? 'scheduled';
    final canEdit = status == 'scheduled';

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
              _DutyStatusBadge(status: status),
              const SizedBox(height: 8),
              if (canEdit)
                _IconAction(
                  color: AppTheme.orangeStatus,
                  icon: Icons.edit_outlined,
                  onTap: () => _openEditDuty(duty),
                )
              else
                const SizedBox(width: 28, height: 28),
              const SizedBox(height: 6),
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

  String _statusLabel(String status) {
    switch (status) {
      case 'completed':
        return 'Complete';
      case 'started':
      case 'in-progress':
        return 'Started';
      case 'skipped':
      case 'not completed':
        return 'Not Done';
      default:
        return 'Scheduled';
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'completed':
        return AppTheme.primaryGreen;
      case 'started':
      case 'in-progress':
        return const Color(0xFF2563EB);
      case 'skipped':
      case 'not completed':
        return AppTheme.redStatus;
      default:
        return AppTheme.orangeStatus;
    }
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

  String get _selectedDateLabel {
    final today = _dateOnly(DateTime.now());
    if (_sameDay(_selectedDate, today)) {
      return 'Today, ${DateFormat('MMM d, yyyy').format(_selectedDate)}';
    }
    return DateFormat('EEE, MMM d, yyyy').format(_selectedDate);
  }

  DateTime _dateOnly(DateTime value) {
    return DateTime(value.year, value.month, value.day);
  }

  DateTime? _parseDate(dynamic value) {
    final text = value?.toString() ?? '';
    if (text.isEmpty) return null;
    final parsed = DateTime.tryParse(text);
    if (parsed != null) return _dateOnly(parsed);
    try {
      return _dateOnly(DateFormat('yyyy-MM-dd').parseStrict(text));
    } catch (_) {
      return null;
    }
  }

  bool _sameDay(DateTime a, DateTime b) {
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }
}

class _DutyStatusBadge extends StatelessWidget {
  final String status;

  const _DutyStatusBadge({required this.status});

  @override
  Widget build(BuildContext context) {
    final state = context.findAncestorStateOfType<_ManageDutiesScreenState>();
    final color = state?._statusColor(status) ?? AppTheme.orangeStatus;
    final label = state?._statusLabel(status) ?? 'Scheduled';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: color,
          fontSize: 9,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _DateNavButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _DateNavButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          width: 38,
          height: 42,
          decoration: BoxDecoration(
            color: AppTheme.white,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFFE1E5EA)),
          ),
          child: Icon(icon, color: AppTheme.textDark, size: 20),
        ),
      ),
    );
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
