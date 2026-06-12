import 'dart:async';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:intl/intl.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/real_bus_map.dart';
import 'driver_profile_screen.dart';

class DriverDashboardScreen extends StatefulWidget {
  const DriverDashboardScreen({super.key});

  @override
  State<DriverDashboardScreen> createState() => _DriverDashboardScreenState();
}

class _DriverDashboardScreenState extends State<DriverDashboardScreen> {
  int _tabIndex = 0;
  bool _isLoading = true;
  bool _isStarting = false;
  bool _isEnding = false;

  Map<String, dynamic>? _todayDuty;
  Map<String, dynamic>? _upcomingDuty;
  List<dynamic> _monthDuties = [];
  List<dynamic> _routes = [];
  List<dynamic> _activeBuses = [];
  Map<String, dynamic>? _summary;
  DateTime _selectedMonth = DateTime.now();
  Timer? _refreshTimer;

  StreamSubscription<Position>? _locationSubscription;
  Position? _lastPosition;
  double _distanceCoveredKm = 0;
  double _currentSpeedKmh = 0;
  DateTime? _lastLocationAt;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _loadLiveBuses(),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _locationSubscription?.cancel();
    super.dispose();
  }

  Future<void> _loadDashboard() async {
    setState(() => _isLoading = true);
    try {
      final results = await Future.wait([
        ApiService.get('/duty/today'),
        ApiService.get('/duty/upcoming'),
        ApiService.get(
          '/duty/monthly?month=${_selectedMonth.month}&year=${_selectedMonth.year}',
        ),
        ApiService.get('/routes'),
        ApiService.get('/gps/active-buses'),
      ]);

      final monthDuties = results[2]['duties'] as List? ?? <dynamic>[];
      final routeSummaries = results[3]['routes'] as List? ?? <dynamic>[];
      final detailedRoutes = await _loadDetailedRoutes(routeSummaries, [
        results[0]['duty'],
        results[1]['duty'],
        ...monthDuties,
      ]);

      if (!mounted) return;
      setState(() {
        _todayDuty = results[0]['duty'];
        _upcomingDuty = results[1]['duty'];
        _monthDuties = monthDuties;
        _summary = results[2]['summary'];
        _routes = detailedRoutes;
        _activeBuses = results[4]['buses'] ?? [];
        _isLoading = false;
      });

      if (_todayDuty != null && _todayDuty!['status'] == 'started') {
        await _startLocationSharing(_todayDuty!);
      }
    } catch (e) {
      debugPrint('Driver dashboard load error: $e');
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<List<dynamic>> _loadDetailedRoutes(
    List<dynamic> routeSummaries,
    List<dynamic> duties,
  ) async {
    final neededRouteIds = duties
        .whereType<Map>()
        .map((duty) => duty['routeId']?.toString())
        .whereType<String>()
        .where((routeId) => routeId.isNotEmpty)
        .toSet();

    if (neededRouteIds.isEmpty) return routeSummaries;

    final routes = <dynamic>[];
    for (final route in routeSummaries) {
      if (route is! Map) {
        routes.add(route);
        continue;
      }

      final routeId = route['routeId']?.toString();
      if (routeId == null || !neededRouteIds.contains(routeId)) {
        routes.add(route);
        continue;
      }

      try {
        final response = await ApiService.get('/routes/$routeId');
        routes.add(response['route'] ?? route);
      } catch (_) {
        routes.add(route);
      }
    }

    return routes;
  }

  Future<void> _loadLiveBuses() async {
    try {
      final response = await ApiService.get('/gps/active-buses');
      if (!mounted) return;
      setState(() => _activeBuses = response['buses'] as List? ?? []);
    } catch (e) {
      debugPrint('Live bus refresh error: $e');
    }
  }

  List<Map<String, dynamic>> get _todayDuties {
    final now = DateTime.now();
    return _monthDuties
        .whereType<Map>()
        .map((duty) => Map<String, dynamic>.from(duty))
        .where((duty) {
          final date = _parseDate(duty['scheduledDate']);
          return date != null &&
              date.year == now.year &&
              date.month == now.month &&
              date.day == now.day;
        })
        .toList();
  }

  Map<String, List<Map<String, dynamic>>> get _groupedSchedule {
    final groups = <String, List<Map<String, dynamic>>>{};
    for (final rawDuty in _monthDuties.whereType<Map>()) {
      final duty = Map<String, dynamic>.from(rawDuty);
      final date = _parseDate(duty['scheduledDate']);
      final key = date == null
          ? 'Unscheduled'
          : DateFormat('EEEE, MMM d, yyyy').format(date);
      groups.putIfAbsent(key, () => []).add(duty);
    }
    return groups;
  }

  Future<bool> _ensureLocationPermission() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return false;

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    return permission == LocationPermission.always ||
        permission == LocationPermission.whileInUse;
  }

  Future<void> _startLocationSharing(Map<String, dynamic> duty) async {
    if (_locationSubscription != null) return;

    final allowed = await _ensureLocationPermission();
    if (!allowed) return;

    try {
      final current = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
      await _publishPosition(current, duty);
    } catch (e) {
      debugPrint('Current location error: $e');
    }

    const settings = LocationSettings(
      accuracy: LocationAccuracy.high,
      distanceFilter: 25,
    );

    _locationSubscription = Geolocator.getPositionStream(
      locationSettings: settings,
    ).listen((position) => _publishPosition(position, duty));
  }

  Future<void> _stopLocationSharing() async {
    await _locationSubscription?.cancel();
    _locationSubscription = null;
    _lastPosition = null;
  }

  Future<void> _publishPosition(
    Position position,
    Map<String, dynamic> duty,
  ) async {
    final bus = duty['bus'] ?? {};
    final busId = bus['busId'] ?? bus['_id'];
    final routeId = duty['routeId'];

    if (busId == null || routeId == null) return;

    final speedKmh = position.speed.isFinite ? position.speed * 3.6 : 0.0;
    if (_lastPosition != null) {
      final meters = Geolocator.distanceBetween(
        _lastPosition!.latitude,
        _lastPosition!.longitude,
        position.latitude,
        position.longitude,
      );
      if (meters >= 5 && meters <= 500) {
        _distanceCoveredKm += meters / 1000;
      }
    }

    _lastPosition = position;
    _currentSpeedKmh = speedKmh < 0 ? 0 : speedKmh;
    _lastLocationAt = DateTime.now();
    if (mounted) setState(() {});

    try {
      await ApiService.post('/gps/update-location', {
        'busId': busId,
        'routeId': routeId,
        'dutyId': duty['dutyId'],
        'latitude': position.latitude,
        'longitude': position.longitude,
        'speed': _currentSpeedKmh,
      });
      await _loadLiveBuses();
    } catch (e) {
      debugPrint('Location publish error: $e');
    }
  }

  Future<void> _startDuty(Map<String, dynamic> duty) async {
    setState(() => _isStarting = true);
    try {
      final allowed = await _ensureLocationPermission();
      if (!mounted) return;
      if (!allowed) {
        setState(() => _isStarting = false);
        _showMessage('Turn on location permission to start duty', false);
        return;
      }

      final response = await ApiService.post('/duty/start', {
        'dutyId': duty['dutyId'],
      });

      if (response['success'] == true) {
        await _startLocationSharing(duty);
        await _loadDashboard();
        if (!mounted) return;
        _showMessage('Duty started. GPS sharing is live.', true);
      } else {
        _showMessage(response['message'] ?? 'Duty could not be started', false);
      }
    } catch (e) {
      debugPrint('Start duty error: $e');
      if (mounted) _showMessage('Duty could not be started', false);
    }
    if (mounted) setState(() => _isStarting = false);
  }

  Future<void> _completeDuty(Map<String, dynamic> duty) async {
    setState(() => _isEnding = true);
    try {
      final response = await ApiService.post('/duty/complete', {
        'dutyId': duty['dutyId'],
      });

      if (response['success'] == true) {
        await _stopLocationSharing();
        await _loadDashboard();
        if (!mounted) return;
        _showMessage('Duty completed successfully.', true);
      } else {
        _showMessage(
          response['message'] ?? 'Duty could not be completed',
          false,
        );
      }
    } catch (e) {
      debugPrint('Complete duty error: $e');
      if (mounted) _showMessage('Duty could not be completed', false);
    }
    if (mounted) setState(() => _isEnding = false);
  }

  Future<void> _changeMonth(int offset) async {
    setState(() {
      _selectedMonth = DateTime(
        _selectedMonth.year,
        _selectedMonth.month + offset,
      );
    });
    await _loadDashboard();
  }

  void _showMessage(String message, bool success) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: success ? AppTheme.primaryGreen : AppTheme.redStatus,
      ),
    );
  }

  DateTime? _parseDate(dynamic value) {
    if (value == null) return null;
    return DateTime.tryParse(value.toString())?.toLocal();
  }

  String? get _selectedRouteId {
    final currentRoute = _todayDuty?['routeId']?.toString();
    if (currentRoute != null && currentRoute.isNotEmpty) return currentRoute;

    final upcomingRoute = _upcomingDuty?['routeId']?.toString();
    return upcomingRoute?.isEmpty == true ? null : upcomingRoute;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(
              child: _isLoading
                  ? const Center(
                      child: CircularProgressIndicator(
                        color: AppTheme.primaryGreen,
                      ),
                    )
                  : IndexedStack(
                      index: _tabIndex,
                      children: [_buildTodayTab(), _buildScheduleTab()],
                    ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _buildBottomTabs(),
    );
  }

  Widget _buildHeader() {
    return Container(
      color: AppTheme.white,
      padding: const EdgeInsets.fromLTRB(18, 10, 18, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Row(
                  children: [
                    Icon(
                      Icons.location_on_outlined,
                      color: AppTheme.primaryGreen,
                      size: 19,
                    ),
                    SizedBox(width: 7),
                    Expanded(
                      child: Text(
                        'Electric Bus Tracking',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: AppTheme.primaryGreen,
                          fontWeight: FontWeight.w800,
                          fontSize: 16,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  _tabIndex == 0 ? 'Driver Dashboard' : 'Duty Schedule',
                  style: const TextStyle(
                    color: AppTheme.textDark,
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          IconButton.filled(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const DriverProfileScreen()),
            ).then((_) => _loadDashboard()),
            icon: const Icon(Icons.person_outline, size: 18),
            tooltip: 'Profile',
            style: IconButton.styleFrom(
              backgroundColor: AppTheme.primaryGreen,
              foregroundColor: AppTheme.white,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTodayTab() {
    final activeRoute = _selectedRouteId;

    return RefreshIndicator(
      onRefresh: _loadDashboard,
      color: AppTheme.primaryGreen,
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          SizedBox(
            height: 230,
            child: RealBusMap(
              routes: _routes,
              buses: _activeBuses,
              selectedRouteId: activeRoute,
              showEndpointMarkers: activeRoute != null,
              showStopMarkers: activeRoute != null,
              forcedZoom: activeRoute == null ? 10.2 : null,
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (_todayDuty == null)
                  _buildEmptyDutyCard()
                else
                  _buildFocusDutyCard(_todayDuty!, current: true),
                const SizedBox(height: 12),
                if (_upcomingDuty != null)
                  _buildFocusDutyCard(_upcomingDuty!, current: false),
                const SizedBox(height: 18),
                _buildTodayDutySections(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildScheduleTab() {
    final grouped = _groupedSchedule;

    return Column(
      children: [
        Container(
          color: AppTheme.white,
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
          child: Row(
            children: [
              IconButton(
                onPressed: () => _changeMonth(-1),
                icon: const Icon(Icons.chevron_left),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      DateFormat('MMMM yyyy').format(_selectedMonth),
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.textDark,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${_summary?['total'] ?? _monthDuties.length} total duties',
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppTheme.textGrey,
                      ),
                    ),
                  ],
                ),
              ),
              IconButton(
                onPressed: () => _changeMonth(1),
                icon: const Icon(Icons.chevron_right),
              ),
            ],
          ),
        ),
        Expanded(
          child: grouped.isEmpty
              ? const Center(
                  child: Text(
                    'No scheduled duties',
                    style: TextStyle(color: AppTheme.textGrey),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadDashboard,
                  color: AppTheme.primaryGreen,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: grouped.entries
                        .map(
                          (entry) =>
                              _buildScheduleGroup(entry.key, entry.value),
                        )
                        .toList(),
                  ),
                ),
        ),
      ],
    );
  }

  Widget _buildFocusDutyCard(
    Map<String, dynamic> duty, {
    required bool current,
  }) {
    final status = duty['status']?.toString() ?? '';
    final isStarted = status == 'started';
    final isAssigned = status == 'assigned' || status == 'scheduled';
    final bus = duty['bus'];

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(8),
        border: current
            ? Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.25))
            : Border.all(color: AppTheme.orangeStatus.withValues(alpha: 0.35)),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 6)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
            child: Row(
              children: [
                Icon(
                  current ? Icons.directions_bus_filled : Icons.schedule,
                  color: current
                      ? AppTheme.primaryGreen
                      : AppTheme.orangeStatus,
                  size: 16,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    current ? 'Current Duty' : 'Upcoming Duty',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textDark,
                    ),
                  ),
                ),
                _statusChip(
                  status,
                  current ? AppTheme.primaryGreen : AppTheme.orangeStatus,
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 6, 14, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  duty['route'] ?? 'Route N/A',
                  style: const TextStyle(
                    color: AppTheme.textDark,
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _miniInfo(
                      Icons.access_time,
                      duty['scheduledStartTime'] ?? '',
                    ),
                    const SizedBox(width: 14),
                    _miniInfo(
                      Icons.timer_outlined,
                      duty['scheduledEndTime'] ?? '',
                    ),
                    const Spacer(),
                    Text(
                      bus?['busNumber'] ?? 'Bus N/A',
                      style: const TextStyle(
                        color: AppTheme.textGrey,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                if (current && isStarted) ...[
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _metricBox(
                          Icons.speed,
                          '${_currentSpeedKmh.toStringAsFixed(1)} km/h',
                          'Speed',
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: _metricBox(
                          Icons.social_distance,
                          '${_distanceCoveredKm.toStringAsFixed(2)} km',
                          'Covered',
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: _metricBox(
                          Icons.gps_fixed,
                          _lastLocationAt == null ? 'Waiting' : 'Live',
                          'GPS',
                        ),
                      ),
                    ],
                  ),
                ],
                if (current && (isAssigned || isStarted)) ...[
                  const SizedBox(height: 12),
                  Align(
                    alignment: Alignment.centerRight,
                    child: ElevatedButton(
                      onPressed: isAssigned
                          ? (_isStarting ? null : () => _startDuty(duty))
                          : (_isEnding ? null : () => _completeDuty(duty)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: isStarted
                            ? AppTheme.redStatus
                            : AppTheme.primaryGreen,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 10,
                        ),
                        minimumSize: Size.zero,
                      ),
                      child: Text(isStarted ? 'End' : 'Start'),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTodayDutySections() {
    final duties = _todayDuties;
    if (duties.isEmpty) {
      return const SizedBox();
    }

    final done = duties.where((duty) => duty['status'] == 'completed').toList();
    final notDone = duties
        .where((duty) => duty['status'] != 'completed')
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (notDone.isNotEmpty)
          _buildDutySection('Not Done Duties', notDone, AppTheme.primaryGreen),
        if (done.isNotEmpty) ...[
          const SizedBox(height: 14),
          _buildDutySection('Done Duties', done, AppTheme.primaryGreen),
        ],
      ],
    );
  }

  Widget _buildDutySection(
    String title,
    List<Map<String, dynamic>> duties,
    Color color,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.check_circle_outline, color: color, size: 16),
            const SizedBox(width: 6),
            Text(
              title,
              style: const TextStyle(
                color: AppTheme.textDark,
                fontSize: 14,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(width: 8),
            _countBadge(duties.length),
          ],
        ),
        const SizedBox(height: 8),
        ...duties.map((duty) => _buildCompactDutyCard(duty)),
      ],
    );
  }

  Widget _buildScheduleGroup(
    String dateLabel,
    List<Map<String, dynamic>> duties,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(8),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 5)],
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
            decoration: const BoxDecoration(
              color: AppTheme.primaryGreen,
              borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.calendar_today,
                  color: AppTheme.white,
                  size: 15,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    dateLabel,
                    style: const TextStyle(
                      color: AppTheme.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.darkGreen,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '${duties.length} ${duties.length == 1 ? 'Duty' : 'Duties'}',
                    style: const TextStyle(
                      color: AppTheme.white,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(children: duties.map(_buildCompactDutyCard).toList()),
          ),
        ],
      ),
    );
  }

  Widget _buildCompactDutyCard(Map<String, dynamic> duty) {
    final bus = duty['bus'];
    final status = duty['status']?.toString() ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE9ECEF)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.location_on_outlined,
                color: AppTheme.primaryGreen,
                size: 16,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  duty['route'] ?? 'Route N/A',
                  style: const TextStyle(
                    color: AppTheme.textDark,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              _statusChip(status, _statusColor(status)),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _miniInfo(
                Icons.schedule,
                'Start: ${duty['scheduledStartTime'] ?? ''}',
              ),
              const SizedBox(width: 14),
              _miniInfo(
                Icons.timer_outlined,
                'End: ${duty['scheduledEndTime'] ?? ''}',
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Bus ${bus?['busNumber'] ?? 'N/A'}',
            style: const TextStyle(color: AppTheme.textGrey, fontSize: 11),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyDutyCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE9ECEF)),
      ),
      child: const Column(
        children: [
          Icon(
            Icons.assignment_late_outlined,
            color: AppTheme.textGrey,
            size: 34,
          ),
          SizedBox(height: 8),
          Text(
            'No current duty assigned',
            style: TextStyle(color: AppTheme.textGrey, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _statusChip(String status, Color color) {
    final label = status.isEmpty ? 'PENDING' : status.toUpperCase();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 9,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }

  Widget _miniInfo(IconData icon, String text) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: AppTheme.textGrey, size: 13),
        const SizedBox(width: 4),
        Text(
          text,
          style: const TextStyle(color: AppTheme.textGrey, fontSize: 11),
        ),
      ],
    );
  }

  Widget _metricBox(IconData icon, String value, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      decoration: BoxDecoration(
        color: AppTheme.lightGreen,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Icon(icon, color: AppTheme.primaryGreen, size: 16),
          const SizedBox(height: 4),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontSize: 11,
              fontWeight: FontWeight.w800,
            ),
          ),
          Text(
            label,
            style: const TextStyle(color: AppTheme.textGrey, fontSize: 9),
          ),
        ],
      ),
    );
  }

  Widget _countBadge(int count) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: AppTheme.lightGreen,
        borderRadius: BorderRadius.circular(5),
      ),
      child: Text(
        count.toString(),
        style: const TextStyle(
          color: AppTheme.primaryGreen,
          fontSize: 11,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'completed':
        return AppTheme.primaryGreen;
      case 'started':
        return AppTheme.orangeStatus;
      case 'skipped':
        return AppTheme.redStatus;
      default:
        return AppTheme.primaryGreen;
    }
  }

  Widget _buildBottomTabs() {
    return SafeArea(
      top: false,
      child: Container(
        height: 64,
        padding: const EdgeInsets.fromLTRB(12, 6, 12, 8),
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
        child: Row(
          children: [
            _tabButton(0, Icons.assignment_outlined, "Today's Duty"),
            const SizedBox(width: 8),
            _tabButton(1, Icons.calendar_month_outlined, 'Schedule'),
          ],
        ),
      ),
    );
  }

  Widget _tabButton(int index, IconData icon, String label) {
    final selected = _tabIndex == index;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _tabIndex = index),
        borderRadius: BorderRadius.circular(8),
        child: Container(
          decoration: BoxDecoration(
            color: selected ? AppTheme.primaryGreen : AppTheme.bgGrey,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: 18,
                color: selected ? AppTheme.white : AppTheme.textDark,
              ),
              const SizedBox(height: 3),
              Text(
                label,
                style: TextStyle(
                  color: selected ? AppTheme.white : AppTheme.textDark,
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
