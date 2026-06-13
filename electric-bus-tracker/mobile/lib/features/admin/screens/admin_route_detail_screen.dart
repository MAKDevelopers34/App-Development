import 'package:flutter/material.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/real_bus_map.dart';
import '../widgets/admin_bottom_nav.dart';
import 'admin_profile_screen.dart';

class AdminRouteDetailScreen extends StatefulWidget {
  final Map<String, dynamic> route;
  final List<dynamic> activeBuses;

  const AdminRouteDetailScreen({
    super.key,
    required this.route,
    this.activeBuses = const [],
  });

  @override
  State<AdminRouteDetailScreen> createState() => _AdminRouteDetailScreenState();
}

class _AdminRouteDetailScreenState extends State<AdminRouteDetailScreen> {
  late Map<String, dynamic> _route;
  List<dynamic> _activeBuses = [];
  List<dynamic> _allBuses = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _route = Map<String, dynamic>.from(widget.route);
    _activeBuses = widget.activeBuses;
    _loadRoute();
  }

  Future<void> _loadRoute() async {
    final routeId = _routeId;
    if (routeId == null) {
      setState(() => _isLoading = false);
      return;
    }

    try {
      final results = await Future.wait([
        ApiService.get('/routes/$routeId'),
        ApiService.get('/gps/active-buses'),
        ApiService.get('/admin/buses'),
      ]);

      if (!mounted) return;
      setState(() {
        _route = Map<String, dynamic>.from(results[0]['route'] ?? _route);
        _activeBuses = results[1]['buses'] ?? widget.activeBuses;
        _allBuses = results[2]['buses'] ?? [];
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  String? get _routeId => _route['routeId']?.toString();

  List<Map<String, dynamic>> get _routeActiveBuses {
    final routeId = _routeId;
    if (routeId == null) return [];

    return _activeBuses
        .whereType<Map>()
        .map((bus) => Map<String, dynamic>.from(bus))
        .where((bus) => bus['routeId']?.toString() == routeId)
        .toList();
  }

  List<Map<String, dynamic>> get _stops {
    final rawStops = (_route['stops'] as List? ?? [])
        .whereType<Map>()
        .map((stop) => Map<String, dynamic>.from(stop))
        .toList();

    rawStops.sort(
      (a, b) => _intFrom(a['order']).compareTo(_intFrom(b['order'])),
    );
    return rawStops;
  }

  List<Map<String, dynamic>> get _scheduledTrips {
    return (_route['schedule'] as List? ?? [])
        .whereType<Map>()
        .map((schedule) => Map<String, dynamic>.from(schedule))
        .take(4)
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final routeName = _route['routeName']?.toString() ?? 'Route';

    return Scaffold(
      backgroundColor: AppTheme.white,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(routeName),
            Expanded(
              child: RefreshIndicator(
                color: AppTheme.primaryGreen,
                onRefresh: _loadRoute,
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      SizedBox(
                        height: 230,
                        child: Stack(
                          children: [
                            RealBusMap(
                              routes: [_route],
                              buses: _routeActiveBuses,
                              selectedRouteId: _routeId,
                              showStopMarkers: true,
                              showEndpointMarkers: true,
                            ),
                            if (_isLoading)
                              Container(
                                color: AppTheme.white.withValues(alpha: 0.62),
                                child: const Center(
                                  child: CircularProgressIndicator(
                                    color: AppTheme.primaryGreen,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 10),
                      _buildBusSection(),
                      const SizedBox(height: 16),
                      TextButton(
                        onPressed: () => Navigator.maybePop(context),
                        child: const Text(
                          'Back to Dashboard',
                          style: TextStyle(
                            color: AppTheme.textGrey,
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: const AdminBottomNav(selectedIndex: 2),
    );
  }

  Widget _buildHeader(String routeName) {
    return Container(
      color: AppTheme.white,
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.location_on_outlined,
                color: AppTheme.primaryGreen,
                size: 20,
              ),
              const SizedBox(width: 6),
              const Expanded(
                child: Text(
                  'Electric Bus Tracking',
                  style: TextStyle(
                    color: AppTheme.primaryGreen,
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              GestureDetector(
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const AdminProfileScreen()),
                ),
                child: const CircleAvatar(
                  radius: 16,
                  backgroundColor: AppTheme.primaryGreen,
                  child: Icon(
                    Icons.person_outline,
                    color: AppTheme.white,
                    size: 18,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            _titleCase(routeName),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontSize: 16,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBusSection() {
    final activeBuses = _routeActiveBuses;
    if (activeBuses.isNotEmpty) {
      return Column(
        children: activeBuses
            .asMap()
            .entries
            .map((entry) => _buildActiveBusRow(entry.value, entry.key))
            .toList(),
      );
    }

    final schedules = _scheduledTrips;
    if (schedules.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppTheme.bgGrey,
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Text(
            'No buses scheduled on this route right now.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppTheme.textGrey, fontSize: 12),
          ),
        ),
      );
    }

    return Column(
      children: schedules
          .asMap()
          .entries
          .map((entry) => _buildScheduleBusRow(entry.value, entry.key))
          .toList(),
    );
  }

  Widget _buildActiveBusRow(Map<String, dynamic> bus, int index) {
    final stopName =
        bus['nextStop']?['name']?.toString() ??
        bus['currentStop']?['name']?.toString() ??
        _stopForIndex(index);
    final busNumber = bus['busNumber']?.toString() ?? 'EV${index + 1}';
    final speed = _intFrom(bus['speed']);

    return _buildVehicleRow(
      busNumber: busNumber,
      stopName: stopName,
      etaText: speed > 0 ? '$speed km/h currently' : 'Live location active',
    );
  }

  Widget _buildScheduleBusRow(Map<String, dynamic> schedule, int index) {
    final stop = _stopMapForIndex(index);
    final stopName = stop?['name']?.toString() ?? _stopForIndex(index);
    final busNumber = _busNumberFor(schedule['busId']);
    final totalTime = _intFrom(_route['estimatedTotalTime']);
    final stopTime = _intFrom(stop?['estimatedMinutesFromStart']);
    final remaining = totalTime > stopTime ? totalTime - stopTime : totalTime;

    return _buildVehicleRow(
      busNumber: busNumber,
      stopName: stopName,
      etaText: 'Estimated Time to Destination Stop : ${_formatEta(remaining)}',
    );
  }

  Widget _buildVehicleRow({
    required String busNumber,
    required String stopName,
    required String etaText,
  }) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 13, 16, 12),
      decoration: const BoxDecoration(
        color: AppTheme.white,
        border: Border(
          top: BorderSide(color: Color(0xFFE6E6E6)),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.directions_bus,
                color: AppTheme.primaryGreen,
                size: 16,
              ),
              const SizedBox(width: 8),
              Text(
                busNumber,
                style: const TextStyle(
                  color: AppTheme.textDark,
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(width: 14),
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.lightGreen,
                    borderRadius: BorderRadius.circular(5),
                  ),
                  child: Text(
                    stopName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppTheme.primaryGreen,
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const Icon(
                Icons.access_time,
                color: AppTheme.textGrey,
                size: 14,
              ),
              const SizedBox(width: 5),
              Expanded(
                child: Text(
                  etaText,
                  style: const TextStyle(
                    color: AppTheme.textGrey,
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Map<String, dynamic>? _stopMapForIndex(int index) {
    final stops = _stops;
    if (stops.isEmpty) return null;
    final mappedIndex = stops.length <= 2
        ? stops.length - 1
        : (1 + (index * 4)).clamp(1, stops.length - 1).toInt();
    return stops[mappedIndex];
  }

  String _stopForIndex(int index) {
    return _stopMapForIndex(index)?['name']?.toString() ??
        _route['endPoint']?['name']?.toString() ??
        'Destination';
  }

  String _busNumberFor(dynamic busId) {
    final id = busId?.toString();
    if (id == null || id.isEmpty) return 'EV';

    for (final rawBus in _allBuses.whereType<Map>()) {
      final bus = Map<String, dynamic>.from(rawBus);
      if (bus['busId']?.toString() == id) {
        return bus['busNumber']?.toString() ?? 'EV$id';
      }
    }

    return 'EV$id';
  }

  int _intFrom(dynamic value) {
    if (value is num) return value.round();
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  String _formatEta(int minutes) {
    if (minutes <= 0) return 'Arriving';
    if (minutes < 60) return '$minutes mins';

    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    return '$hours:${mins.toString().padLeft(2, '0')} hour';
  }

  String _titleCase(String value) {
    return value
        .split(' ')
        .where((part) => part.isNotEmpty)
        .map((part) {
          final lower = part.toLowerCase();
          return lower[0].toUpperCase() + lower.substring(1);
        })
        .join(' ');
  }
}
