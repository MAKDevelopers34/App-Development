import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map/src/layer/shared/mobile_layer_transformer.dart';
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
  final bool requireRoadGeometryForRoutes;
  final bool showRouteLabels;
  final bool showRouteDirectionArrows;
  final LatLng? focusPoint;
  final double? focusZoom;

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
    this.requireRoadGeometryForRoutes = false,
    this.showRouteLabels = true,
    this.showRouteDirectionArrows = true,
    this.focusPoint,
    this.focusZoom,
  });

  @override
  State<RealBusMap> createState() => _RealBusMapState();
}

class _RealBusMapState extends State<RealBusMap> {
  static const LatLng _defaultCenter = LatLng(32.5838, 71.5436);
  static const Distance _distance = Distance();

  final MapController _mapController = MapController();
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
    if (oldWidget.focusPoint != widget.focusPoint ||
        oldWidget.focusZoom != widget.focusZoom) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _moveToFocus());
    }
  }

  @override
  Widget build(BuildContext context) {
    final visibleRoutes = _visibleRoutes();
    final routePoints = visibleRoutes.expand(_mapFitRoutePoints).toList();
    final busPoints = widget.buses
        .whereType<Map>()
        .map((bus) => _displayBusPoint(Map<String, dynamic>.from(bus)))
        .whereType<LatLng>()
        .toList();
    final allPoints = [...routePoints, ...busPoints];
    final center = _centerOf(allPoints);
    final useSmartRouteOverlay = widget.requireRoadGeometryForRoutes;

    return ClipRRect(
      borderRadius: BorderRadius.circular(0),
      child: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
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
              if (useSmartRouteOverlay)
                _SmartRouteOverlayLayer(routes: _visualRoutes(visibleRoutes))
              else
                PolylineLayer(polylines: _buildRouteLines(visibleRoutes)),
              MarkerLayer(
                markers: _buildMarkers(
                  visibleRoutes,
                  includeRouteDirectionMarkers: !useSmartRouteOverlay,
                ),
              ),
            ],
          ),
          const Positioned(right: 8, bottom: 8, child: _MapAttribution()),
        ],
      ),
    );
  }

  void _moveToFocus() {
    final point = widget.focusPoint;
    if (!mounted || point == null) return;
    _mapController.move(point, widget.focusZoom ?? 14.8);
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
    final jobs = <Future<MapEntry<String, List<LatLng>>?>>[];
    final routesToFetch = _visibleRoutes().take(12).toList();

    for (final route in routesToFetch) {
      final rawPoints = _routePoints(route);
      final key = _routeKey(route, rawPoints);
      if (rawPoints.length < 2 ||
          _roadRoutes.containsKey(key) ||
          _loadingRoutes.contains(key)) {
        continue;
      }

      _loadingRoutes.add(key);
      jobs.add(() async {
        try {
          final roadPoints = await _fetchRoadGeometry(rawPoints);
          if (roadPoints.length < 2) return null;
          return MapEntry(key, roadPoints);
        } catch (_) {
          return null;
        }
      }());
    }

    if (jobs.isEmpty) return;

    final results = await Future.wait(jobs);
    if (!mounted) return;

    setState(() {
      for (final result in results.whereType<MapEntry<String, List<LatLng>>>()) {
        _roadRoutes[result.key] = result.value;
      }
      for (final route in routesToFetch) {
        _loadingRoutes.remove(_routeKey(route, _routePoints(route)));
      }
    });
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
          final roadOnlyStyle = widget.requireRoadGeometryForRoutes;
          return Polyline(
            points: points,
            color: selected
                ? AppTheme.primaryGreen
                : AppTheme.primaryGreen.withValues(
                    alpha: roadOnlyStyle ? 0.88 : 0.36,
                  ),
            strokeWidth: selected ? 8 : (roadOnlyStyle ? 6 : 3.5),
            borderColor: AppTheme.white.withValues(
              alpha: selected ? 0.96 : (roadOnlyStyle ? 0.82 : 0.62),
            ),
            borderStrokeWidth: selected ? 4 : (roadOnlyStyle ? 1.8 : 1.5),
          );
        })
        .where((line) => line.points.length >= 2)
        .toList();
  }

  List<_VisualRoute> _visualRoutes(List<Map<String, dynamic>> visibleRoutes) {
    return visibleRoutes
        .asMap()
        .entries
        .map((entry) {
          final route = entry.value;
          final routeId = route['routeId']?.toString() ?? '${entry.key}';
          final selected = routeId == widget.selectedRouteId;
          final points = _visibleRoutePoints(
            route,
            routeIndex: entry.key,
            routeCount: visibleRoutes.length,
          );
          return _VisualRoute(
            routeId: routeId,
            points: points,
            selected: selected,
          );
        })
        .where((route) => route.points.length >= 2)
        .toList();
  }

  List<Marker> _buildMarkers(
    List<Map<String, dynamic>> visibleRoutes, {
    bool includeRouteDirectionMarkers = true,
  }) {
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

      if (includeRouteDirectionMarkers) {
        markers.addAll(_routeDirectionMarkers(route, visualPoints));
      }

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

  List<LatLng> _mapFitRoutePoints(Map<String, dynamic> route) {
    return _displayRoutePoints(route, allowFallback: true);
  }

  List<LatLng> _displayRoutePoints(
    Map<String, dynamic> route, {
    bool allowFallback = true,
  }) {
    final rawPoints = _routePoints(route);
    final key = _routeKey(route, rawPoints);
    final roadPoints = _roadRoutes[key];
    if (roadPoints != null && roadPoints.length >= 2) return roadPoints;
    if (!allowFallback) return const [];
    return rawPoints;
  }

  List<LatLng> _visibleRoutePoints(
    Map<String, dynamic> route, {
    required int routeIndex,
    required int routeCount,
  }) {
    return _displayRoutePoints(
      route,
      allowFallback: !widget.requireRoadGeometryForRoutes,
    );
  }

  List<Marker> _routeDirectionMarkers(
    Map<String, dynamic> route,
    List<LatLng> points,
  ) {
    if (points.length < 2) return const [];

    final markers = <Marker>[];
    final routeName =
        route['routeName']?.toString() ?? route['name']?.toString() ?? 'Route';

    if (widget.showRouteLabels) {
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
    }

    if (!widget.showRouteDirectionArrows) return markers;

    final arrowPoints = _routeArrowPoints(points);
    for (final arrow in arrowPoints) {
      final previous = arrow.previous;
      final current = arrow.current;
      final radians = _bearing(previous, current) * math.pi / 180;

      markers.add(
        Marker(
          point: current,
          width: 16,
          height: 16,
          child: IgnorePointer(
            child: Transform.rotate(
              angle: radians,
              child: CustomPaint(
                painter: const _RouteArrowPainter(),
                child: const SizedBox.expand(),
              ),
            ),
          ),
        ),
      );
    }

    return markers;
  }

  List<_RouteArrowPoint> _routeArrowPoints(List<LatLng> points) {
    if (points.length < 2) return const [];

    var totalMeters = 0.0;
    for (var i = 0; i < points.length - 1; i++) {
      totalMeters += _distance.as(LengthUnit.Meter, points[i], points[i + 1]);
    }
    if (totalMeters <= 0) return const [];

    final spacing = (totalMeters / 14).clamp(120.0, 420.0);
    final arrows = <_RouteArrowPoint>[];
    for (var target = spacing; target < totalMeters; target += spacing) {
      final arrow = _pointAtDistance(points, target);
      if (arrow != null) arrows.add(arrow);
    }
    return arrows;
  }

  _RouteArrowPoint? _pointAtDistance(List<LatLng> points, double targetMeters) {
    var walkedMeters = 0.0;
    for (var i = 0; i < points.length - 1; i++) {
      final start = points[i];
      final end = points[i + 1];
      final segmentMeters = _distance.as(LengthUnit.Meter, start, end);
      if (segmentMeters <= 0) continue;

      if (walkedMeters + segmentMeters >= targetMeters) {
        final amount = ((targetMeters - walkedMeters) / segmentMeters)
            .clamp(0.0, 1.0)
            .toDouble();
        return _RouteArrowPoint(start, _interpolate(start, end, amount));
      }
      walkedMeters += segmentMeters;
    }
    return null;
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

class _RouteArrowPoint {
  final LatLng previous;
  final LatLng current;

  const _RouteArrowPoint(this.previous, this.current);
}

class _VisualRoute {
  final String routeId;
  final List<LatLng> points;
  final bool selected;

  const _VisualRoute({
    required this.routeId,
    required this.points,
    required this.selected,
  });
}

class _SmartRouteOverlayLayer extends StatelessWidget {
  final List<_VisualRoute> routes;

  const _SmartRouteOverlayLayer({required this.routes});

  @override
  Widget build(BuildContext context) {
    final camera = MapCamera.of(context);
    return MobileLayerTransformer(
      child: CustomPaint(
        size: camera.size,
        isComplex: true,
        painter: _SmartRoutePainter(routes: routes, camera: camera),
      ),
    );
  }
}

class _ProjectedVisualRoute {
  final _VisualRoute route;
  final List<Offset> points;

  const _ProjectedVisualRoute({required this.route, required this.points});
}

class _RouteSegment {
  final int routeIndex;
  final int segmentIndex;
  final Offset start;
  final Offset end;
  final Offset midpoint;
  final double angle;
  final double orientation;
  final String laneKey;

  const _RouteSegment({
    required this.routeIndex,
    required this.segmentIndex,
    required this.start,
    required this.end,
    required this.midpoint,
    required this.angle,
    required this.orientation,
    required this.laneKey,
  });

  double get length => (end - start).distance;

  Offset get normal {
    final delta = end - start;
    final length = delta.distance;
    if (length <= 0) return Offset.zero;
    return Offset(-delta.dy / length, delta.dx / length);
  }
}

class _PaintedSegment {
  final Offset start;
  final Offset end;
  final Offset originalStart;
  final Offset originalEnd;

  const _PaintedSegment({
    required this.start,
    required this.end,
    required this.originalStart,
    required this.originalEnd,
  });

  double get length => (end - start).distance;
}

class _LanePlan {
  final Map<String, _LaneGroup> groups;

  const _LanePlan(this.groups);

  factory _LanePlan.fromSegments(List<_RouteSegment> segments) {
    final groups = <String, _LaneGroup>{};
    for (final segment in segments) {
      groups.putIfAbsent(segment.laneKey, _LaneGroup.new).add(segment);
    }
    return _LanePlan(groups);
  }
}

class _LaneGroup {
  bool hasForward = false;
  bool hasReverse = false;

  bool get hasOppositeDirections => hasForward && hasReverse;

  void add(_RouteSegment segment) {
    if (_isForward(segment)) {
      hasForward = true;
    } else {
      hasReverse = true;
    }
  }

  double directionFor(_RouteSegment segment) => _isForward(segment) ? -1.0 : 1.0;

  bool _isForward(_RouteSegment segment) {
    final diff = _angleDifference(segment.angle, segment.orientation);
    return diff <= math.pi / 2;
  }

  static double _angleDifference(double a, double b) {
    var diff = (a - b).abs() % (math.pi * 2);
    if (diff > math.pi) diff = (math.pi * 2) - diff;
    return diff;
  }
}

class _SmartRoutePainter extends CustomPainter {
  static const double _routeStrokeWidth = 5.8;
  static const double _selectedStrokeWidth = 7.0;
  static const double _borderStrokeWidth = 1.8;
  static const double _sharedLaneOffset = 2.8;
  static const double _arrowSpacingPx = 96.0;
  static const double _laneSnapPx = 18.0;
  static const double _angleBucket = math.pi / 12;

  final List<_VisualRoute> routes;
  final MapCamera camera;

  const _SmartRoutePainter({required this.routes, required this.camera});

  @override
  void paint(Canvas canvas, Size size) {
    if (routes.isEmpty) return;

    final projectedRoutes = routes
        .map(
          (route) => _ProjectedVisualRoute(
            route: route,
            points: _simplifyScreenPoints(
              route.points.map(camera.getOffsetFromOrigin).toList(),
            ),
          ),
        )
        .where((route) => route.points.length >= 2)
        .toList();
    if (projectedRoutes.isEmpty) return;

    final segments = _buildSegments(projectedRoutes);
    final lanePlan = _LanePlan.fromSegments(segments);
    final paintedSegments = <List<_PaintedSegment>>[];

    for (var routeIndex = 0; routeIndex < projectedRoutes.length; routeIndex++) {
      final route = projectedRoutes[routeIndex];
      final routeSegments = <_PaintedSegment>[];
      for (var i = 0; i < route.points.length - 1; i++) {
        final start = route.points[i];
        final end = route.points[i + 1];
        final segment = _RouteSegment(
          routeIndex: routeIndex,
          segmentIndex: i,
          start: start,
          end: end,
          midpoint: Offset((start.dx + end.dx) / 2, (start.dy + end.dy) / 2),
          angle: math.atan2(end.dy - start.dy, end.dx - start.dx),
          orientation: _segmentOrientation(start, end),
          laneKey: _laneKey(start, end),
        );
        final offset = _laneOffsetFor(segment, lanePlan);
        routeSegments.add(
          _PaintedSegment(
            start: start + offset,
            end: end + offset,
            originalStart: start,
            originalEnd: end,
          ),
        );
      }
      paintedSegments.add(routeSegments);
    }

    _drawRouteBorders(canvas, projectedRoutes, paintedSegments);
    _drawRouteFills(canvas, projectedRoutes, paintedSegments);
    _drawRouteArrows(canvas, projectedRoutes, paintedSegments);
  }

  List<Offset> _simplifyScreenPoints(List<Offset> points) {
    if (points.length <= 2) return points;

    final simplified = <Offset>[points.first];
    for (final point in points.skip(1).take(points.length - 2)) {
      if ((point - simplified.last).distance >= 4.0) {
        simplified.add(point);
      }
    }
    if ((points.last - simplified.last).distance >= 1.0) {
      simplified.add(points.last);
    }
    return simplified;
  }

  List<_RouteSegment> _buildSegments(List<_ProjectedVisualRoute> routes) {
    final segments = <_RouteSegment>[];
    for (var routeIndex = 0; routeIndex < routes.length; routeIndex++) {
      final points = routes[routeIndex].points;
      for (var segmentIndex = 0; segmentIndex < points.length - 1; segmentIndex++) {
        final start = points[segmentIndex];
        final end = points[segmentIndex + 1];
        if ((end - start).distance < 6) continue;
        segments.add(
          _RouteSegment(
            routeIndex: routeIndex,
            segmentIndex: segmentIndex,
            start: start,
            end: end,
            midpoint: Offset((start.dx + end.dx) / 2, (start.dy + end.dy) / 2),
            angle: math.atan2(end.dy - start.dy, end.dx - start.dx),
            orientation: _segmentOrientation(start, end),
            laneKey: _laneKey(start, end),
          ),
        );
      }
    }
    return segments;
  }

  Offset _laneOffsetFor(_RouteSegment segment, _LanePlan lanePlan) {
    final lane = lanePlan.groups[segment.laneKey];
    if (lane == null || !lane.hasOppositeDirections) return Offset.zero;
    return segment.normal * (_sharedLaneOffset * lane.directionFor(segment));
  }

  static double _segmentOrientation(Offset start, Offset end) {
    var angle = math.atan2(end.dy - start.dy, end.dx - start.dx);
    while (angle < 0) {
      angle += math.pi;
    }
    while (angle >= math.pi) {
      angle -= math.pi;
    }
    return angle;
  }

  static String _laneKey(Offset start, Offset end) {
    final midpoint = Offset((start.dx + end.dx) / 2, (start.dy + end.dy) / 2);
    final orientation = _segmentOrientation(start, end);
    final x = (midpoint.dx / _laneSnapPx).round();
    final y = (midpoint.dy / _laneSnapPx).round();
    final angle = (orientation / _angleBucket).round();
    return '$x:$y:$angle';
  }

  void _drawRouteBorders(
    Canvas canvas,
    List<_ProjectedVisualRoute> routes,
    List<List<_PaintedSegment>> routeSegments,
  ) {
    for (var i = 0; i < routeSegments.length; i++) {
      final width =
          (routes[i].route.selected ? _selectedStrokeWidth : _routeStrokeWidth) +
          _borderStrokeWidth;
      final paint = Paint()
        ..color = Colors.black.withValues(alpha: 0.86)
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..strokeWidth = width;
      _drawSegments(canvas, routeSegments[i], paint);
    }
  }

  void _drawRouteFills(
    Canvas canvas,
    List<_ProjectedVisualRoute> routes,
    List<List<_PaintedSegment>> routeSegments,
  ) {
    for (var i = 0; i < routeSegments.length; i++) {
      final paint = Paint()
        ..color = AppTheme.primaryGreen.withValues(
          alpha: routes[i].route.selected ? 1.0 : 0.94,
        )
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..strokeWidth = routes[i].route.selected
            ? _selectedStrokeWidth
            : _routeStrokeWidth;
      _drawSegments(canvas, routeSegments[i], paint);
    }
  }

  void _drawSegments(
    Canvas canvas,
    List<_PaintedSegment> segments,
    Paint paint,
  ) {
    for (final segment in segments) {
      if (segment.length < 1) continue;
      canvas.drawLine(segment.start, segment.end, paint);
    }
  }

  void _drawRouteArrows(
    Canvas canvas,
    List<_ProjectedVisualRoute> routes,
    List<List<_PaintedSegment>> routeSegments,
  ) {
    final arrowPaint = Paint()
      ..color = AppTheme.white.withValues(alpha: 0.96)
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..strokeWidth = 1.15;

    for (final segments in routeSegments) {
      var walked = 0.0;
      var nextArrow = _arrowSpacingPx * 0.65;
      for (final segment in segments) {
        if (segment.length < 18) {
          walked += segment.length;
          continue;
        }
        while (walked + segment.length >= nextArrow) {
          final amount = ((nextArrow - walked) / segment.length)
              .clamp(0.0, 1.0)
              .toDouble();
          final center = Offset.lerp(segment.start, segment.end, amount)!;
          final angle = math.atan2(
            segment.end.dy - segment.start.dy,
            segment.end.dx - segment.start.dx,
          );
          _drawArrow(canvas, center, angle, arrowPaint);
          nextArrow += _arrowSpacingPx;
        }
        walked += segment.length;
      }
    }
  }

  void _drawArrow(Canvas canvas, Offset center, double angle, Paint paint) {
    const length = 5.8;
    const spread = 0.42;
    final forward = Offset(math.cos(angle), math.sin(angle));
    final tip = center + forward * 2.2;
    final left =
        tip - Offset(math.cos(angle - spread), math.sin(angle - spread)) * length;
    final right =
        tip - Offset(math.cos(angle + spread), math.sin(angle + spread)) * length;
    final path = ui.Path()
      ..moveTo(left.dx, left.dy)
      ..lineTo(tip.dx, tip.dy)
      ..lineTo(right.dx, right.dy);
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _SmartRoutePainter oldDelegate) {
    return oldDelegate.routes != routes || oldDelegate.camera != camera;
  }
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

class _RouteArrowPainter extends CustomPainter {
  const _RouteArrowPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final path = ui.Path()
      ..moveTo(size.width / 2, 1.5)
      ..lineTo(size.width - 2.5, size.height - 3)
      ..moveTo(size.width / 2, 1.5)
      ..lineTo(2.5, size.height - 3);

    canvas.drawPath(
      path,
      Paint()
        ..color = AppTheme.white
        ..style = PaintingStyle.stroke
        ..strokeWidth = 4.4
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );
    canvas.drawPath(
      path,
      Paint()
        ..color = AppTheme.primaryGreen
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.2
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );
  }

  @override
  bool shouldRepaint(covariant _RouteArrowPainter oldDelegate) => false;
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
