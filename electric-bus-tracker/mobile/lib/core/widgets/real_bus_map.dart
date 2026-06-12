import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../theme/app_theme.dart';

class RealBusMap extends StatelessWidget {
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

  static const LatLng _defaultCenter = LatLng(32.5838, 71.5436);

  @override
  Widget build(BuildContext context) {
    final visibleRoutes = _visibleRoutes();
    final routePoints = visibleRoutes.expand(_routePoints).toList();
    final busPoints = buses.map(_busPoint).whereType<LatLng>().toList();
    final allPoints = [...routePoints, ...busPoints];
    final center = _centerOf(allPoints);

    return ClipRRect(
      borderRadius: BorderRadius.circular(0),
      child: Stack(
        children: [
          FlutterMap(
            options: MapOptions(
              initialCenter: center,
              initialZoom: forcedZoom ?? _zoomFor(allPoints),
              minZoom: 8,
              maxZoom: 18,
              onTap: onMapTap == null
                  ? null
                  : (tapPosition, point) => onMapTap!(point),
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
    final typedRoutes = routes
        .whereType<Map>()
        .map((route) => Map<String, dynamic>.from(route))
        .toList();

    if (selectedRouteId == null) return typedRoutes;

    final selected = typedRoutes
        .where((route) => route['routeId']?.toString() == selectedRouteId)
        .toList();
    return selected.isEmpty ? typedRoutes : selected;
  }

  List<Polyline> _buildRouteLines(List<Map<String, dynamic>> visibleRoutes) {
    return visibleRoutes
        .map((route) {
          final points = _routePoints(route);
          final selected = route['routeId']?.toString() == selectedRouteId;
          return Polyline(
            points: points,
            color: selected
                ? AppTheme.primaryGreen
                : AppTheme.darkGreen.withValues(alpha: 0.42),
            strokeWidth: selected ? 6 : 3.5,
            borderColor: AppTheme.white.withValues(
              alpha: selected ? 0.9 : 0.55,
            ),
            borderStrokeWidth: selected ? 2 : 1,
          );
        })
        .where((line) => line.points.length >= 2)
        .toList();
  }

  List<Marker> _buildMarkers(List<Map<String, dynamic>> visibleRoutes) {
    final markers = <Marker>[];

    for (final route in visibleRoutes) {
      final isSelected = route['routeId']?.toString() == selectedRouteId;
      final showDetails = showStopMarkers || isSelected;
      final points = _routePoints(route);

      if ((showEndpointMarkers || isSelected) && points.isNotEmpty) {
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

    for (final rawBus in buses.whereType<Map>()) {
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
      width: 46,
      height: 46,
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
      width: 22,
      height: 22,
      child: Tooltip(
        message: label,
        child: Container(
          decoration: BoxDecoration(
            color: AppTheme.white,
            shape: BoxShape.circle,
            border: Border.all(color: AppTheme.darkGreen, width: 2),
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
      width: 82,
      height: 58,
      child: GestureDetector(
        onTap: onBusTap == null ? null : () => onBusTap!(bus),
        child: Tooltip(
          message: '$busNumber - $routeName',
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 44,
                height: 36,
                decoration: BoxDecoration(
                  color: AppTheme.primaryGreen,
                  borderRadius: BorderRadius.circular(18),
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

  List<LatLng> _routePoints(Map<String, dynamic> route) {
    final start = _pointFrom(route['startPoint']);
    final end = _pointFrom(route['endPoint']);
    final stops =
        (route['stops'] as List? ?? [])
            .whereType<Map>()
            .map((stop) => Map<String, dynamic>.from(stop))
            .toList()
          ..sort((a, b) => (a['order'] ?? 0).compareTo(b['order'] ?? 0));

    final points = <LatLng>[
      ?start,
      ...stops.map(_pointFrom).whereType<LatLng>(),
      ?end,
    ];

    return points;
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
        '© OpenStreetMap contributors',
        style: TextStyle(
          color: AppTheme.textGrey,
          fontSize: 10,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}
