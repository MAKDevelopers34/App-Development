import 'dart:async';

import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../../core/widgets/real_bus_map.dart';

class BusEatScreen extends StatefulWidget {
  final String routeId;
  final String? stopId;

  const BusEatScreen({super.key, required this.routeId, this.stopId});

  @override
  State<BusEatScreen> createState() => _BusEatScreenState();
}

class _BusEatScreenState extends State<BusEatScreen> {
  Map<String, dynamic>? _routeData;
  List<dynamic> _routeBuses = [];
  List<dynamic> _estimates = [];
  bool _isLoading = true;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadData();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _loadLiveData(),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadData() async {
    try {
      final routeResponse = await ApiService.get('/routes/${widget.routeId}');
      final busesResponse = await ApiService.get(
        '/gps/route/${widget.routeId}',
      );

      List<dynamic> estimates = [];
      if (widget.stopId != null) {
        final eatResponse = await ApiService.get(
          '/routes/${widget.routeId}/eat/${widget.stopId}',
        );
        estimates = eatResponse['estimates'] ?? [];
      }

      if (!mounted) return;
      setState(() {
        _routeData = routeResponse['route'];
        _routeBuses = busesResponse['buses'] ?? [];
        _estimates = estimates;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadLiveData() async {
    try {
      final busesResponse = await ApiService.get(
        '/gps/route/${widget.routeId}',
      );

      List<dynamic> estimates = _estimates;
      if (widget.stopId != null) {
        final eatResponse = await ApiService.get(
          '/routes/${widget.routeId}/eat/${widget.stopId}',
        );
        estimates = eatResponse['estimates'] ?? [];
      }

      if (!mounted) return;
      setState(() {
        _routeBuses = busesResponse['buses'] ?? [];
        _estimates = estimates;
      });
    } catch (e) {
      debugPrint('Live route refresh error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text('Electric Bus Tracking'),
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.primaryGreen),
            )
          : _buildContent(),
    );
  }

  Widget _buildContent() {
    if (_routeData == null) {
      return const Center(child: Text('Route not found'));
    }

    final routeName =
        '${_routeData!['startPoint']['name']} - '
        '${_routeData!['endPoint']['name']}';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Route header — green text matching design
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Route: $routeName',
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.primaryGreen,
                ),
              ),
              if (widget.stopId != null) ...[
                const SizedBox(height: 4),
                Text(
                  'Stop: ${widget.stopId}',
                  style: const TextStyle(
                    fontSize: 13,
                    color: AppTheme.textGrey,
                  ),
                ),
              ],
            ],
          ),
        ),

        SizedBox(
          height: 260,
          child: RealBusMap(
            routes: [_routeData!],
            buses: _routeBuses,
            selectedRouteId: widget.routeId,
            showStopMarkers: true,
            showEndpointMarkers: true,
          ),
        ),

        const Divider(height: 1),

        // Bus EAT list
        Expanded(
          child: _estimates.isEmpty
              ? _buildNoBusesView()
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _estimates.length,
                  itemBuilder: (context, index) {
                    return _buildBusEatCard(_estimates[index]);
                  },
                ),
        ),

        // Back to Dashboard button — matching design
        Padding(
          padding: const EdgeInsets.all(16),
          child: SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => Navigator.pop(context),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppTheme.primaryGreen),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
              child: const Text(
                'Back to Dashboard',
                style: TextStyle(
                  color: AppTheme.primaryGreen,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildBusEatCard(Map<String, dynamic> estimate) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE8E8E8)),
        boxShadow: [
          BoxShadow(
            color: AppTheme.cardShadow,
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          // Bus icon
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppTheme.lightGreen,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(
              Icons.directions_bus,
              color: AppTheme.primaryGreen,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),

          // Bus info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  estimate['busId'] ?? 'BUS',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textDark,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  'Estimated time to arrive — '
                  '${estimate['stopName'] ?? 'Stop'}',
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppTheme.textGrey,
                  ),
                ),
              ],
            ),
          ),

          // EAT badge — green matching design
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: AppTheme.primaryGreen,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              estimate['durationText'] ?? '--',
              style: const TextStyle(
                color: AppTheme.white,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNoBusesView() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.directions_bus_outlined,
            size: 60,
            color: AppTheme.textGrey.withValues(alpha: 0.4),
          ),
          const SizedBox(height: 16),
          const Text(
            'No active buses on this route',
            style: TextStyle(color: AppTheme.textGrey, fontSize: 14),
          ),
        ],
      ),
    );
  }
}
