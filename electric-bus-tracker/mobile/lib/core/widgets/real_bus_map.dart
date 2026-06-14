import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';

import '../theme/app_theme.dart';

class RealBusMap extends StatefulWidget {
  final List<dynamic> routes;
  final List<dynamic> buses;
  final String? selectedRouteId;
  final bool showStopMarkers;
  final bool showEndpointMarkers;
  final void Function(Map<String, dynamic> bus)? onBusTap;
  final void Function(LatLng point)? onMapTap;
  final double? forcedZoom;

  const RealBusMap({
    super.key,
    this.routes = const [],
    this.buses = const [],
    this.selectedRouteId,
    this.showStopMarkers = false,
    this.showEndpointMarkers = false,
    this.onBusTap,
    this.onMapTap,
    this.forcedZoom,
  });

  @override
  State<RealBusMap> createState() => _RealBusMapState();
}

class _RealBusMapState extends State<RealBusMap> {
  static const LatLng _defaultCenter = LatLng(32.5838, 71.5436);
  static const Distance _distance = Distance();

  final Map<String, List<LatLng>> _roadRoutes = {};
  final Set<String> _loadingRoutes = {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _fetchRoadRoutes());
  }

  @override
  void didUpdateWidget(covariant RealBusMap oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.routes != widget.routes ||
        oldWidget.selectedRouteId != widget.selectedRouteId) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _fetchRoadRoutes());
    }
  }

  @override
  Widget build(BuildContext context) {
    final visibleRoutes = _visibleRoutes();
    final routePoints = visibleRoutes.expand(_displayRoutePoints).toList();
    final busPoints = widget.buses
        .whereType<Map>()
        .map((bus) => _displayBusPoint(Map<String, dynamic>.from(bus)))
        .whereType<LatLng>()
        .toList();
    final allPoints = [...routePoints, ...busPoints];
    final center = _centerOf(allPoints);

    return ClipRRect(
      borderRadius: BorderRadius.circular(0),
      child: Stack(
        children: [
          FlutterMap(
            options: MapOptions(
              initialCenter: center,
              initialZoom: widget.forcedZoom ?? _zoomFor(allPoints),
              minZoom: 8,
              maxZoom: 18,
              onTap: widget.onMapTap == null
                  ? null
                  : (tapPosition, point) => widget.onMapTap!(point),
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.example.mobile',
                maxNativeZoom: 19,
              ),
              PolylineLayer(polylines: _buildRouteLines(visibleRoutes)),
              MarkerLayer(markers: _buildMarkers(visibleRoutes)),
            ],
          ),
          const Positioned(right: 8, bottom: 8, child: _MapAttribution()),
        ],
      ),
    );
  }

  List<Map<String, dynamic>> _visibleRoutes() {
    final typedRoutes = widget.routes
        .whereType<Map>()
        .map((route) => Map<String, dynamic>.from(route))
        .toList();

    if (widget.selectedRouteId == null) return typedRoutes;

    final selected = typedRoutes
        .where(
          (route) => route['routeId']?.toString() == widget.selectedRouteId,
        )
        .toList();
    return selected.isEmpty ? typedRoutes : selected;
  }

  Future<void> _fetchRoadRoutes() async {
    final routesToFetch = _visibleRoutes().take(8).toList();
    for (final route in routesToFetch) {
      final rawPoints = _routePoints(route);
      final key = _routeKey(route, rawPoints);
      if (rawPoints.length < 2 ||
          _roadRoutes.containsKey(key) ||
          _loadingRoutes.contains(key)) {
        continue;
      }

      _loadingRoutes.add(key);
      try {
        final roadPoints = await _fetchRoadGeometry(rawPoints);
        if (!mounted) return;
        if (roadPoints.length >= 2) {
          setState(() => _roadRoutes[key] = roadPoints);
        }
      } catch (_) {
        // The saved route points are still useful if the public router is busy.
      } finally {
        _loadingRoutes.remove(key);
      }
    }
  }

  Future<List<LatLng>> _fetchRoadGeometry(List<LatLng> points) async {
    final sampledPoints = _samplePoints(points, 24);
    final coordinates = sampledPoints
        .map((point) => '${point.longitude},${point.latitude}')
        .join(';');
    final uri = Uri.parse(
      'https://router.project-osrm.org/route/v1/driving/$coordinates'
      '?overview=full&geometries=geojson&continue_straight=false',
    );
    final response = await http.get(uri).timeout(const Duration(seconds: 5));
    if (response.statusCode != 200) return const [];

    final decoded = jsonDecode(response.body);
    if (decoded is! Map || decoded['code'] != 'Ok') return const [];

    final routes = decoded['routes'];
    if (routes is! List || routes.isEmpty) return const [];

    final geometry = routes.first['geometry'];
    final coordinatesList = geometry?['coordinates'];
    if (coordinatesList is! List) return const [];

    return coordinatesList
        .whereType<List>()
        .map((coordinate) {
          if (coordinate.length < 2) return null;
          final lng = _numberFrom(coordinate[0]);
          final lat = _numberFrom(coordinate[1]);
          if (lat == null || lng == null) return null;
          return LatLng(lat, lng);
        })
        .whereType<LatLng>()
        .toList();
  }

  List<LatLng> _samplePoints(List<LatLng> points, int maxPoints) {
    if (points.length <= maxPoints) return points;

    final sampled = <LatLng>[];
    for (var i = 0; i < maxPoints; i++) {
      final index = ((points.length - 1) * i / (maxPoints - 1)).round();
      sampled.add(points[index]);
    }
    return sampled;
  }

  List<Polyline> _buildRouteLines(List<Map<String, dynamic>> visibleRoutes) {
    return visibleRoutes
        .asMap()
        .entries
        .map((entry) {
          final route = entry.value;
          final points = _visibleRoutePoints(
            route,
            routeIndex: entry.key,
            routeCount: visibleRoutes.length,
          );
          final selected =
              route['routeId']?.toString() == widget.selectedRouteId;
          return Polyline(
            points: points,
            color: selected
                ? AppTheme.primaryGreen
                : AppTheme.darkGreen.withValues(alpha: 0.36),
            strokeWidth: selected ? 8 : 3.5,
            borderColor: AppTheme.white.withValues(
              alpha: selected ? 0.96 : 0.62,
            ),
            borderStrokeWidth: selected ? 4 : 1.5,
          );
        })
        .where((line) => line.points.length >= 2)
        .toList();
  }

  List<Marker> _buildMarkers(List<Map<String, dynamic>> visibleRoutes) {
    final markers = <Marker>[];

    for (final entry in visibleRoutes.asMap().entries) {
      final route = entry.value;
      final isSelected = route['routeId']?.toString() == widget.selectedRouteId;
      final showDetails = widget.showStopMarkers || isSelected;
      final points = _routePoints(route);
      final visualPoints = _visibleRoutePoints(
        route,
        routeIndex: entry.key,
        routeCount: visibleRoutes.length,
      );

      markers.addAll(_routeDirectionMarkers(route, visualPoints));

      if ((widget.showEndpointMarkers || isSelected) && points.isNotEmpty) {
        final startLabel = route['startPoint']?['name']?.toString() ?? 'Start';
        final endLabel = route['endPoint']?['name']?.toString() ?? 'End';
        markers.add(_pointMarker(points.first, Icons.trip_origin, startLabel));
        if (points.length > 1) {
          markers.add(_pointMarker(points.last, Icons.flag, endLabel));
        }
      }

      if (showDetails) {
        final stops =
            (route['stops'] as List? ?? [])
                .whereType<Map>()
                .map((stop) => Map<String, dynamic>.from(stop))
                .toList()
              ..sort((a, b) => (a['order'] ?? 0).compareTo(b['order'] ?? 0));

        for (final stop in stops) {
          final point = _pointFrom(stop);
          if (point != null) {
            markers.add(_stopMarker(point, stop, route));
          }
        }
      }
    }

    for (final rawBus in widget.buses.whereType<Map>()) {
      final bus = Map<String, dynamic>.from(rawBus);
      final point = _displayBusPoint(bus);
      if (point != null) {
        markers.add(_busMarker(point, bus));
      }
    }

    return markers;
  }

  Marker _pointMarker(LatLng point, IconData icon, String label) {
    return Marker(
      point: point,
      width: 86,
      height: 62,
      child: Tooltip(
        message: label,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: AppTheme.white,
                shape: BoxShape.circle,
                border: Border.all(color: AppTheme.primaryGreen, width: 3),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.18),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Icon(icon, color: AppTheme.primaryGreen, size: 17),
            ),
            const SizedBox(height: 2),
            _MapLabel(text: label.toUpperCase()),
          ],
        ),
      ),
    );
  }

  Marker _stopMarker(
    LatLng point,
    Map<String, dynamic> stop,
    Map<String, dynamic> route,
  ) {
    final label = stop['name']?.toString() ?? 'Stop';
    return Marker(
      point: point,
      width: 74,
      height: 44,
      child: GestureDetector(
        onTap: () => _showStopEatSheet(route, stop),
        child: Tooltip(
          message: label,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 15,
                height: 15,
                decoration: BoxDecoration(
                  color: AppTheme.primaryGreen,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppTheme.white, width: 2),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.12),
                      blurRadius: 4,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 2),
              _MapLabel(text: label),
            ],
          ),
        ),
      ),
    );
  }

  void _showStopEatSheet(
    Map<String, dynamic> route,
    Map<String, dynamic> stop,
  ) {
    final estimates = _stopEstimates(route, stop);
    final stopName = stop['name']?.toString() ?? 'Stop';

    showModalBottomSheet<void>(
      context: context,
      backgroundColor: AppTheme.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (context) {
        return SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.location_on_outlined,
                      color: AppTheme.primaryGreen,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        stopName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: AppTheme.textDark,
                          fontSize: 17,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                if (estimates.isEmpty)
                  const Text(
                    'No active bus is still remaining for this stop.',
                    style: TextStyle(
                      color: AppTheme.textGrey,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  )
                else
                  ...estimates.map(_buildEatRow),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildEatRow(_StopEat estimate) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.bgGrey,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: const BoxDecoration(
              color: AppTheme.primaryGreen,
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.directions_bus,
              color: AppTheme.white,
              size: 18,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  estimate.busName,
                  style: const TextStyle(
                    color: AppTheme.textDark,
                    fontSize: 13,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  '${estimate.distanceKm.toStringAsFixed(1)} km remaining at ${estimate.speedKmh.round()} km/h',
                  style: const TextStyle(
                    color: AppTheme.textGrey,
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          Text(
            estimate.durationText,
            style: const TextStyle(
              color: AppTheme.primaryGreen,
              fontSize: 14,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }

  Marker _busMarker(LatLng point, Map<String, dynamic> bus) {
    final busNumber = bus['busNumber']?.toString() ?? 'BUS';
    final routeName = bus['routeName']?.toString() ?? 'Route';

    return Marker(
      point: point,
      width: 100,
      height: 72,
      child: GestureDetector(
        onTap: () {
          if (widget.onBusTap != null) {
            widget.onBusTap!(bus);
          } else {
            _showBusSheet(bus);
          }
        },
        child: Tooltip(
          message: '$busNumber - $routeName',
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: AppTheme.primaryGreen,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.white, width: 3),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.22),
                      blurRadius: 8,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.directions_bus,
                  color: AppTheme.white,
                  size: 24,
                ),
              ),
              Container(
                margin: const EdgeInsets.only(top: 2),
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppTheme.white,
                  borderRadius: BorderRadius.circular(8),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.12),
                      blurRadius: 4,
                    ),
                  ],
                ),
                child: Text(
                  busNumber,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppTheme.textDark,
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showBusSheet(Map<String, dynamic> bus) {
    final busNumber = bus['busNumber']?.toString() ?? 'BUS';
    final routeName = bus['routeName']?.toString() ?? 'Route';
    final speed = (_numberFrom(bus['speed']) ?? 0).round();
    final driver = bus['driverName']?.toString();

    showModalBottomSheet<void>(
      context: context,
      backgroundColor: AppTheme.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (context) {
        return SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      decoration: const BoxDecoration(
                        color: AppTheme.primaryGreen,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.directions_bus,
                        color: AppTheme.white,
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            busNumber,
                            style: const TextStyle(
                              color: AppTheme.textDark,
                              fontSize: 17,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          Text(
                            routeName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: AppTheme.textGrey,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                _BusInfoRow(label: 'Speed', value: '$speed km/h'),
                if (driver != null && driver.isNotEmpty)
                  _BusInfoRow(label: 'Driver', value: driver),
              ],
            ),
          ),
        );
      },
    );
  }

  List<LatLng> _displayRoutePoints(Map<String, dynamic> route) {
    final rawPoints = _routePoints(route);
    final key = _routeKey(route, rawPoints);
    return _roadRoutes[key] ?? rawPoints;
  }

  List<LatLng> _visibleRoutePoints(
    Map<String, dynamic> route, {
    required int routeIndex,
    required int routeCount,
  }) {
    final points = _displayRoutePoints(route);
    if (points.length < 2 ||
        routeCount <= 1 ||
        widget.selectedRouteId != null) {
      return points;
    }

    final offsetMeters = ((routeIndex - ((routeCount - 1) / 2)) * 5.5)
        .clamp(-11.0, 11.0)
        .toDouble();
    if (offsetMeters.abs() < 0.1) return points;

    return _offsetPolyline(points, offsetMeters);
  }

  List<LatLng> _offsetPolyline(List<LatLng> points, double offsetMeters) {
    final offsetPoints = <LatLng>[];
    for (var i = 0; i < points.length; i++) {
      final previous = points[math.max(0, i - 1)];
      final next = points[math.min(points.length - 1, i + 1)];
      final bearing = _bearing(previous, next) + 90;
      offsetPoints.add(_destinationPoint(points[i], bearing, offsetMeters));
    }
    return offsetPoints;
  }

  List<Marker> _routeDirectionMarkers(
    Map<String, dynamic> route,
    List<LatLng> points,
  ) {
    if (points.length < 2) return const [];

    final markers = <Marker>[];
    final routeName =
        route['routeName']?.toString() ?? route['name']?.toString() ?? 'Route';
    final labelIndex = (points.length * 0.52).floor().clamp(
      1,
      points.length - 1,
    );
    final labelPoint = points[labelIndex];

    markers.add(
      Marker(
        point: labelPoint,
        width: 126,
        height: 26,
        child: IgnorePointer(
          child: Center(
            child: Container(
              constraints: const BoxConstraints(maxWidth: 118),
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: AppTheme.white.withValues(alpha: 0.94),
                borderRadius: BorderRadius.circular(7),
                border: Border.all(
                  color: AppTheme.primaryGreen.withValues(alpha: 0.45),
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.14),
                    blurRadius: 5,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Text(
                routeName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppTheme.primaryGreen,
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ),
        ),
      ),
    );

    for (final fraction in const [0.28, 0.66]) {
      final index = (points.length * fraction).floor().clamp(
        1,
        points.length - 1,
      );
      final previous = points[index - 1];
      final current = points[index];
      final radians =
          (_bearing(previous, current) * math.pi / 180) + math.pi / 2;

      markers.add(
        Marker(
          point: current,
          width: 28,
          height: 28,
          child: IgnorePointer(
            child: Transform.rotate(
              angle: radians,
              child: Container(
                decoration: BoxDecoration(
                  color: AppTheme.primaryGreen,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppTheme.white, width: 2),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.18),
                      blurRadius: 4,
                      offset: const Offset(0, 1),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.navigation,
                  color: AppTheme.white,
                  size: 15,
                ),
              ),
            ),
          ),
        ),
      );
    }

    return markers;
  }

  LatLng? _displayBusPoint(Map<String, dynamic> bus) {
    final rawPoint = _busPoint(bus);
    if (rawPoint == null) return null;

    final routeId = bus['routeId']?.toString();
    if (routeId == null) return rawPoint;

    for (final route in _visibleRoutes()) {
      if (route['routeId']?.toString() != routeId) continue;
      final routePoints = _displayRoutePoints(route);
      final snapped = _snapPointToRoute(routePoints, rawPoint);
      return snapped ?? rawPoint;
    }

    return rawPoint;
  }

  LatLng? _snapPointToRoute(List<LatLng> points, LatLng target) {
    if (points.length < 2) return null;

    var bestDistance = double.infinity;
    LatLng? bestPoint;
    for (var i = 0; i < points.length - 1; i++) {
      final projection = _projectToSegment(points[i], points[i + 1], target);
      final projectedPoint = _interpolate(points[i], points[i + 1], projection);
      final distanceToSegment = _distance.as(
        LengthUnit.Meter,
        target,
        projectedPoint,
      );

      if (distanceToSegment < bestDistance) {
        bestDistance = distanceToSegment;
        bestPoint = projectedPoint;
      }
    }

    return bestDistance <= 500 ? bestPoint : target;
  }

  double _bearing(LatLng from, LatLng to) {
    final lat1 = from.latitude * math.pi / 180;
    final lat2 = to.latitude * math.pi / 180;
    final deltaLng = (to.longitude - from.longitude) * math.pi / 180;
    final y = math.sin(deltaLng) * math.cos(lat2);
    final x =
        math.cos(lat1) * math.sin(lat2) -
        math.sin(lat1) * math.cos(lat2) * math.cos(deltaLng);
    return (math.atan2(y, x) * 180 / math.pi + 360) % 360;
  }

  LatLng _destinationPoint(LatLng start, double bearing, double meters) {
    const earthRadius = 6371000.0;
    final angularDistance = meters / earthRadius;
    final bearingRad = bearing * math.pi / 180;
    final lat1 = start.latitude * math.pi / 180;
    final lng1 = start.longitude * math.pi / 180;

    final lat2 = math.asin(
      math.sin(lat1) * math.cos(angularDistance) +
          math.cos(lat1) * math.sin(angularDistance) * math.cos(bearingRad),
    );
    final lng2 =
        lng1 +
        math.atan2(
          math.sin(bearingRad) * math.sin(angularDistance) * math.cos(lat1),
          math.cos(angularDistance) - math.sin(lat1) * math.sin(lat2),
        );

    return LatLng(lat2 * 180 / math.pi, lng2 * 180 / math.pi);
  }

  String _routeKey(Map<String, dynamic> route, List<LatLng> points) {
    final routeId = route['routeId']?.toString() ?? 'route';
    final first = points.isEmpty ? 'empty' : _pointKey(points.first);
    final last = points.length < 2 ? first : _pointKey(points.last);
    return '$routeId:${points.length}:$first:$last';
  }

  String _pointKey(LatLng point) {
    return '${point.latitude.toStringAsFixed(5)},'
        '${point.longitude.toStringAsFixed(5)}';
  }

  List<LatLng> _routePoints(Map<String, dynamic> route) {
    final start = _pointFrom(route['startPoint']);
    final end = _pointFrom(route['endPoint']);
    final stops =
        (route['stops'] as List? ?? [])
            .whereType<Map>()
            .map((stop) => Map<String, dynamic>.from(stop))
            .toList()
          ..sort((a, b) => (a['order'] ?? 0).compareTo(b['order'] ?? 0));

    return <LatLng>[?start, ...stops.map(_pointFrom).whereType<LatLng>(), ?end];
  }

  List<_StopEat> _stopEstimates(
    Map<String, dynamic> route,
    Map<String, dynamic> stop,
  ) {
    final routeId = route['routeId']?.toString();
    final targetPoint = _pointFrom(stop);
    final routePoints = _routePoints(route);
    if (routeId == null || targetPoint == null || routePoints.length < 2) {
      return const [];
    }

    final targetProgress = _progressAlongRoute(routePoints, targetPoint);
    if (targetProgress == null) return const [];

    final estimates = <_StopEat>[];
    for (final rawBus in widget.buses.whereType<Map>()) {
      final bus = Map<String, dynamic>.from(rawBus);
      if (bus['routeId']?.toString() != routeId) continue;

      final busPoint = _busPoint(bus);
      if (busPoint == null) continue;

      final busProgress = _progressAlongRoute(routePoints, busPoint);
      if (busProgress == null) continue;

      final remainingMeters = targetProgress.meters - busProgress.meters;
      if (remainingMeters <= 35) continue;

      final rawSpeed = _numberFrom(bus['speed']) ?? 0;
      final speedKmh = rawSpeed > 3 ? rawSpeed : 18.0;
      final minutes = math.max(
        1,
        ((remainingMeters / 1000) / speedKmh * 60).round(),
      );

      estimates.add(
        _StopEat(
          busName: bus['busNumber']?.toString() ?? 'Bus ${bus['busId'] ?? ''}',
          distanceKm: remainingMeters / 1000,
          speedKmh: speedKmh,
          durationMinutes: minutes,
        ),
      );
    }

    estimates.sort((a, b) => a.durationMinutes.compareTo(b.durationMinutes));
    return estimates;
  }

  _RouteProgress? _progressAlongRoute(List<LatLng> points, LatLng target) {
    if (points.length < 2) return null;

    var bestDistance = double.infinity;
    var bestProgress = 0.0;
    var cumulative = 0.0;

    for (var i = 0; i < points.length - 1; i++) {
      final start = points[i];
      final end = points[i + 1];
      final segmentMeters = _distance.as(LengthUnit.Meter, start, end);
      if (segmentMeters <= 0) continue;

      final projection = _projectToSegment(start, end, target);
      final projectedPoint = _interpolate(start, end, projection);
      final distanceToSegment = _distance.as(
        LengthUnit.Meter,
        target,
        projectedPoint,
      );

      if (distanceToSegment < bestDistance) {
        bestDistance = distanceToSegment;
        bestProgress = cumulative + (segmentMeters * projection);
      }

      cumulative += segmentMeters;
    }

    return _RouteProgress(bestProgress);
  }

  double _projectToSegment(LatLng start, LatLng end, LatLng target) {
    final latScale = math.cos(start.latitude * math.pi / 180);
    final ax = start.longitude * latScale;
    final ay = start.latitude;
    final bx = end.longitude * latScale;
    final by = end.latitude;
    final px = target.longitude * latScale;
    final py = target.latitude;

    final dx = bx - ax;
    final dy = by - ay;
    final lengthSquared = dx * dx + dy * dy;
    if (lengthSquared <= 0) return 0;

    final t = ((px - ax) * dx + (py - ay) * dy) / lengthSquared;
    return t.clamp(0.0, 1.0).toDouble();
  }

  LatLng _interpolate(LatLng start, LatLng end, double amount) {
    return LatLng(
      start.latitude + ((end.latitude - start.latitude) * amount),
      start.longitude + ((end.longitude - start.longitude) * amount),
    );
  }

  LatLng? _busPoint(dynamic bus) {
    if (bus is! Map) return null;
    return _pointFrom(bus['location']);
  }

  LatLng? _pointFrom(dynamic source) {
    if (source is! Map) return null;
    final lat = _numberFrom(source['latitude']);
    final lng = _numberFrom(source['longitude']);

    if (lat == null || lng == null) return null;
    if (lat.abs() > 90 || lng.abs() > 180) return null;

    return LatLng(lat, lng);
  }

  double? _numberFrom(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '');
  }

  LatLng _centerOf(List<LatLng> points) {
    if (points.isEmpty) return _defaultCenter;

    final lat = points.map((point) => point.latitude).reduce((a, b) => a + b);
    final lng = points.map((point) => point.longitude).reduce((a, b) => a + b);
    return LatLng(lat / points.length, lng / points.length);
  }

  double _zoomFor(List<LatLng> points) {
    if (points.length <= 1) return 13;

    final minLat = points
        .map((point) => point.latitude)
        .reduce((a, b) => a < b ? a : b);
    final maxLat = points
        .map((point) => point.latitude)
        .reduce((a, b) => a > b ? a : b);
    final minLng = points
        .map((point) => point.longitude)
        .reduce((a, b) => a < b ? a : b);
    final maxLng = points
        .map((point) => point.longitude)
        .reduce((a, b) => a > b ? a : b);
    final span = ((maxLat - minLat).abs() + (maxLng - minLng).abs()) / 2;

    if (span > 0.5) return 8.7;
    if (span > 0.28) return 9.5;
    if (span > 0.15) return 10.5;
    if (span > 0.07) return 11.7;
    if (span > 0.025) return 13;
    return 14.4;
  }
}

class _RouteProgress {
  final double meters;

  const _RouteProgress(this.meters);
}

class _StopEat {
  final String busName;
  final double distanceKm;
  final double speedKmh;
  final int durationMinutes;

  const _StopEat({
    required this.busName,
    required this.distanceKm,
    required this.speedKmh,
    required this.durationMinutes,
  });

  String get durationText {
    if (durationMinutes < 60) return '$durationMinutes min';
    final hours = durationMinutes ~/ 60;
    final minutes = durationMinutes % 60;
    return minutes == 0 ? '${hours}h' : '${hours}h ${minutes}m';
  }
}

class _BusInfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _BusInfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.bgGrey,
        borderRadius: BorderRadius.circular(9),
      ),
      child: Row(
        children: [
          Text(
            label,
            style: const TextStyle(
              color: AppTheme.textGrey,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          const Spacer(),
          Text(
            value,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontSize: 13,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _MapAttribution extends StatelessWidget {
  const _MapAttribution();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: AppTheme.white.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(4),
      ),
      child: const Text(
        'OSM',
        style: TextStyle(
          color: AppTheme.textGrey,
          fontSize: 10,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}

class _MapLabel extends StatelessWidget {
  final String text;

  const _MapLabel({required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 78),
      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
      decoration: BoxDecoration(
        color: AppTheme.white.withValues(alpha: 0.94),
        borderRadius: BorderRadius.circular(4),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.12),
            blurRadius: 4,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      child: Text(
        text,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        textAlign: TextAlign.center,
        style: const TextStyle(
          color: AppTheme.textGrey,
          fontSize: 8,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
