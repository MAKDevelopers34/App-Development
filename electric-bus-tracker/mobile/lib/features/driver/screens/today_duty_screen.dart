import 'dart:async';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';

class TodayDutyScreen extends StatefulWidget {
  const TodayDutyScreen({super.key});

  @override
  State<TodayDutyScreen> createState() => _TodayDutyScreenState();
}

class _TodayDutyScreenState extends State<TodayDutyScreen> {
  Map<String, dynamic>? _duty;
  Map<String, dynamic>? _upcomingDuty;
  bool _isLoading = true;
  bool _isStarting = false;
  bool _isEnding = false;
  StreamSubscription<Position>? _locationSubscription;
  Position? _lastPosition;
  double _distanceCoveredKm = 0;
  double _currentSpeedKmh = 0;
  DateTime? _lastLocationAt;

  @override
  void initState() {
    super.initState();
    _loadDuty();
  }

  @override
  void dispose() {
    _locationSubscription?.cancel();
    super.dispose();
  }

  Future<void> _loadDuty() async {
    try {
      final todayRes = await ApiService.get('/duty/today');
      final upcomingRes = await ApiService.get('/duty/upcoming');
      final duty = todayRes['duty'];
      setState(() {
        _duty = duty;
        _upcomingDuty = upcomingRes['duty'];
        _isLoading = false;
      });

      if (duty != null && duty['status'] == 'started') {
        await _startLocationSharing(duty);
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
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
    } catch (e) {
      debugPrint('Location publish error: $e');
    }
  }

  Future<void> _startDuty() async {
    if (_duty == null) return;
    setState(() => _isStarting = true);

    try {
      final allowed = await _ensureLocationPermission();
      if (!mounted) return;
      if (!allowed) {
        setState(() => _isStarting = false);
        return;
      }

      final response = await ApiService.post('/duty/start', {
        'dutyId': _duty!['dutyId'],
      });

      if (response['success'] == true) {
        await _startLocationSharing(_duty!);
        if (!mounted) return;
        _loadDuty();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Duty started! GPS sharing active.'),
            backgroundColor: AppTheme.primaryGreen,
          ),
        );
      }
    } catch (e) {
      debugPrint('Start duty error: $e');
    }
    if (!mounted) return;
    setState(() => _isStarting = false);
  }

  Future<void> _completeDuty() async {
    if (_duty == null) return;
    setState(() => _isEnding = true);

    try {
      final response = await ApiService.post('/duty/complete', {
        'dutyId': _duty!['dutyId'],
      });

      if (response['success'] == true) {
        await _stopLocationSharing();
        if (!mounted) return;
        _loadDuty();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Duty completed successfully!'),
            backgroundColor: AppTheme.primaryGreen,
          ),
        );
      }
    } catch (e) {
      debugPrint('Complete duty error: $e');
    }
    if (!mounted) return;
    setState(() => _isEnding = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      appBar: AppBar(
        title: const Text('Today\'s Duty'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.primaryGreen),
            )
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Upcoming duty section
                  if (_upcomingDuty != null) ...[
                    const Text(
                      'Upcoming Duty',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textGrey,
                      ),
                    ),
                    const SizedBox(height: 8),
                    _buildUpcomingCard(),
                    const SizedBox(height: 20),
                  ],

                  // Today duty section
                  const Text(
                    'Today\'s Duty',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textGrey,
                    ),
                  ),
                  const SizedBox(height: 8),

                  _duty == null ? _buildNoDutyCard() : _buildTodayDutyCard(),
                ],
              ),
            ),
    );
  }

  Widget _buildUpcomingCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppTheme.lightGreen,
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.schedule,
              color: AppTheme.primaryGreen,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _upcomingDuty!['route'] ?? '',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textDark,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  '${_upcomingDuty!['scheduledStartTime']} - '
                  '${_upcomingDuty!['scheduledEndTime']}',
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppTheme.textGrey,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppTheme.lightGreen,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Text(
              'UPCOMING',
              style: TextStyle(
                color: AppTheme.primaryGreen,
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTodayDutyCard() {
    final bus = _duty!['bus'];
    final status = _duty!['status'];
    final isStarted = status == 'started';
    final isAssigned = status == 'assigned' || status == 'scheduled';

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 8)],
      ),
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              color: AppTheme.primaryGreen,
              borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.directions_bus,
                  color: AppTheme.white,
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    _duty!['route'] ?? '',
                    style: const TextStyle(
                      color: AppTheme.white,
                      fontWeight: FontWeight.w600,
                      fontSize: 15,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.white.withValues(alpha: 0.25),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    status.toString().toUpperCase(),
                    style: const TextStyle(
                      color: AppTheme.white,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Details
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                _detailRow(
                  Icons.directions_bus_outlined,
                  'Bus Number',
                  bus?['busNumber'] ?? 'N/A',
                ),
                const SizedBox(height: 12),
                _detailRow(
                  Icons.confirmation_number_outlined,
                  'Bus ID',
                  bus?['busId']?.toString() ?? 'N/A',
                ),
                const SizedBox(height: 12),
                _detailRow(
                  Icons.access_time,
                  'Start Time',
                  _duty!['scheduledStartTime'] ?? '',
                ),
                const SizedBox(height: 12),
                _detailRow(
                  Icons.timer_off_outlined,
                  'End Time',
                  _duty!['scheduledEndTime'] ?? '',
                ),

                const SizedBox(height: 20),

                if (isStarted) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.lightGreen,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      children: [
                        _detailRow(
                          Icons.speed,
                          'Current Speed',
                          '${_currentSpeedKmh.toStringAsFixed(1)} km/h',
                        ),
                        const SizedBox(height: 10),
                        _detailRow(
                          Icons.social_distance,
                          'Distance Covered',
                          '${_distanceCoveredKm.toStringAsFixed(2)} km',
                        ),
                        const SizedBox(height: 10),
                        _detailRow(
                          Icons.gps_fixed,
                          'GPS Update',
                          _lastLocationAt == null ? 'Waiting' : 'Live',
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                ],

                // Action buttons
                if (isAssigned)
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _isStarting ? null : _startDuty,
                      icon: _isStarting
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                color: AppTheme.white,
                                strokeWidth: 2,
                              ),
                            )
                          : const Icon(Icons.play_arrow, size: 20),
                      label: const Text('Start Duty'),
                    ),
                  ),

                if (isStarted) ...[
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _isEnding ? null : _completeDuty,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.redStatus,
                      ),
                      icon: _isEnding
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                color: AppTheme.white,
                                strokeWidth: 2,
                              ),
                            )
                          : const Icon(Icons.stop, size: 20),
                      label: const Text('End Duty'),
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

  Widget _detailRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, color: AppTheme.primaryGreen, size: 18),
        const SizedBox(width: 10),
        Text(
          '$label:',
          style: const TextStyle(fontSize: 13, color: AppTheme.textGrey),
        ),
        const Spacer(),
        Text(
          value,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: AppTheme.textDark,
          ),
        ),
      ],
    );
  }

  Widget _buildNoDutyCard() {
    return Container(
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(16),
      ),
      child: const Center(
        child: Column(
          children: [
            Icon(
              Icons.assignment_late_outlined,
              size: 52,
              color: AppTheme.textGrey,
            ),
            SizedBox(height: 12),
            Text(
              'No duty assigned for today',
              style: TextStyle(color: AppTheme.textGrey, fontSize: 14),
            ),
          ],
        ),
      ),
    );
  }
}
