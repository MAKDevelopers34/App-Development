import 'dart:async';
import 'dart:convert';

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
    final busPoints = widget.buses.map(_busPoint).whereType<LatLng>().toList();
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
        .map((route) {
          final points = _displayRoutePoints(route);
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

    for (final route in visibleRoutes) {
      final isSelected = route['routeId']?.toString() == widget.selectedRouteId;
      final showDetails = widget.showStopMarkers || isSelected;
      final points = _routePoints(route);

      if ((widget.showEndpointMarkers || isSelected) && points.isNotEmpty) {
        markers.add(_pointMarker(points.first, Icons.trip_origin, 'Start'));
        if (points.length > 1) {
          markers.add(_pointMarker(points.last, Icons.flag, 'End'));
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
            markers.add(_stopMarker(point, stop['name']?.toString() ?? 'Stop'));
          }
        }
      }
    }

    for (final rawBus in widget.buses.whereType<Map>()) {
      final bus = Map<String, dynamic>.from(rawBus);
      final point = _busPoint(bus);
      if (point != null) {
        markers.add(_busMarker(point, bus));
      }
    }

    return markers;
  }

  Marker _pointMarker(LatLng point, IconData icon, String label) {
    return Marker(
      point: point,
      width: 48,
      height: 48,
      child: Tooltip(
        message: label,
        child: Container(
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
          child: Icon(icon, color: AppTheme.primaryGreen, size: 20),
        ),
      ),
    );
  }

  Marker _stopMarker(LatLng point, String label) {
    return Marker(
      point: point,
      width: 24,
      height: 24,
      child: Tooltip(
        message: label,
        child: Container(
          decoration: BoxDecoration(
            color: AppTheme.white,
            shape: BoxShape.circle,
            border: Border.all(color: AppTheme.darkGreen, width: 2),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.12),
                blurRadius: 4,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Marker _busMarker(LatLng point, Map<String, dynamic> bus) {
    final busNumber = bus['busNumber']?.toString() ?? 'BUS';
    final speed = (bus['speed'] as num?)?.round() ?? 0;
    final routeName = bus['routeName']?.toString() ?? 'Route';

    return Marker(
      point: point,
      width: 88,
      height: 60,
      child: GestureDetector(
        onTap: widget.onBusTap == null ? null : () => widget.onBusTap!(bus),
        child: Tooltip(
          message: '$busNumber - $routeName',
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 46,
                height: 38,
                decoration: BoxDecoration(
                  color: AppTheme.primaryGreen,
                  borderRadius: BorderRadius.circular(19),
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
                  size: 22,
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
                  '$busNumber  $speed km/h',
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

  List<LatLng> _displayRoutePoints(Map<String, dynamic> route) {
    final rawPoints = _routePoints(route);
    final key = _routeKey(route, rawPoints);
    return _roadRoutes[key] ?? rawPoints;
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
