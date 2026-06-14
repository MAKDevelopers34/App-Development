import 'package:flutter/material.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../widgets/admin_bottom_nav.dart';
import 'admin_profile_screen.dart';
import 'admin_route_detail_screen.dart';

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  List<dynamic> _routes = [];
  List<dynamic> _activeBuses = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);

    try {
      final results = await Future.wait([
        ApiService.get('/routes'),
        ApiService.get('/gps/active-buses'),
      ]);

      final routeSummaries = results[0]['routes'] as List? ?? [];
      final detailedRoutes = await _loadDetailedRoutes(routeSummaries);

      if (!mounted) return;
      setState(() {
        _routes = detailedRoutes;
        _activeBuses = results[1]['buses'] ?? [];
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<List<dynamic>> _loadDetailedRoutes(List<dynamic> routeSummaries) {
    return Future.wait(
      routeSummaries.map((rawRoute) async {
        if (rawRoute is! Map) return rawRoute;
        final route = Map<String, dynamic>.from(rawRoute);
        final routeId = route['routeId']?.toString();
        if (routeId == null || routeId.isEmpty) return route;

        try {
          final response = await ApiService.get('/routes/$routeId');
          return response['route'] ?? route;
        } catch (_) {
          return route;
        }
      }),
    );
  }

  void _openRoute(Map<String, dynamic> route) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => AdminRouteDetailScreen(
          route: route,
          activeBuses: _activeBuses,
        ),
      ),
    ).then((_) => _loadData());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
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
                  : RefreshIndicator(
                      color: AppTheme.primaryGreen,
                      onRefresh: _loadData,
                      child: _routes.isEmpty
                          ? const SingleChildScrollView(
                              physics: AlwaysScrollableScrollPhysics(),
                              child: SizedBox(
                                height: 420,
                                child: Center(
                                  child: Text(
                                    'No routes found',
                                    style: TextStyle(
                                      color: AppTheme.textGrey,
                                      fontSize: 13,
                                    ),
                                  ),
                                ),
                              ),
                            )
                          : GridView.builder(
                              physics: const AlwaysScrollableScrollPhysics(),
                              padding: const EdgeInsets.fromLTRB(
                                16,
                                12,
                                16,
                                18,
                              ),
                              gridDelegate:
                                  const SliverGridDelegateWithFixedCrossAxisCount(
                                    crossAxisCount: 2,
                                    crossAxisSpacing: 10,
                                    mainAxisSpacing: 10,
                                    childAspectRatio: 0.82,
                                  ),
                              itemCount: _routes.length,
                              itemBuilder: (context, index) {
                                final route =
                                    Map<String, dynamic>.from(_routes[index]);
                                return _buildRouteCard(route);
                              },
                            ),
                    ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: const AdminBottomNav(selectedIndex: -1),
    );
  }

  Widget _buildHeader() {
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
          const SizedBox(height: 8),
          const Text(
            'Admin Dashboard',
            style: TextStyle(
              color: AppTheme.textDark,
              fontSize: 15,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRouteCard(Map<String, dynamic> route) {
    final routeName = route['routeName']?.toString() ?? 'Route';
    final busCount = _busCountFor(route);
    final isActive = route['status']?.toString().toLowerCase() == 'active';

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => _openRoute(route),
        borderRadius: BorderRadius.circular(8),
        child: Container(
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
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(8),
                  ),
                  child: _MiniRouteMap(route: route),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 7, 8, 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      routeName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppTheme.textDark,
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Expanded(
                          child: Text(
                            '$busCount\nbuses',
                            style: const TextStyle(
                              color: AppTheme.textGrey,
                              fontSize: 10,
                              height: 1.05,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 7,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: isActive
                                ? AppTheme.lightGreen
                                : const Color(0xFFECECEC),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            isActive ? 'Active' : 'Inactive',
                            style: TextStyle(
                              color: isActive
                                  ? AppTheme.primaryGreen
                                  : AppTheme.textGrey,
                              fontSize: 9,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  int _busCountFor(Map<String, dynamic> route) {
    final routeId = route['routeId']?.toString();
    final activeCount = _activeBuses.whereType<Map>().where((bus) {
      return bus['routeId']?.toString() == routeId;
    }).length;

    if (activeCount > 0) return activeCount;

    final busIds = <String>{};
    for (final rawSchedule in (route['schedule'] as List? ?? [])) {
      if (rawSchedule is! Map) continue;
      final busId = rawSchedule['busId']?.toString();
      if (busId != null && busId.isNotEmpty) busIds.add(busId);
    }

    return busIds.length;
  }
}

class _MiniRouteMap extends StatelessWidget {
  final Map<String, dynamic> route;

  const _MiniRouteMap({required this.route});

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _MiniRoutePainter(route),
      child: const SizedBox.expand(),
    );
  }
}

class _MiniRoutePainter extends CustomPainter {
  final Map<String, dynamic> route;

  _MiniRoutePainter(this.route);

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final bgPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFFF0FFF6), Color(0xFFEAF5FF)],
      ).createShader(rect);
    canvas.drawRect(rect, bgPaint);

    final gridPaint = Paint()
      ..color = AppTheme.primaryGreen.withValues(alpha: 0.07)
      ..strokeWidth = 1;

    for (var i = 1; i < 4; i++) {
      final dx = size.width * i / 4;
      final dy = size.height * i / 4;
      canvas.drawLine(Offset(dx, 0), Offset(dx, size.height), gridPaint);
      canvas.drawLine(Offset(0, dy), Offset(size.width, dy), gridPaint);
    }

    final rawPoints = _routePoints();
    final points = _toCanvasPoints(rawPoints, size);
    if (points.length >= 2) {
      final path = Path()..moveTo(points.first.dx, points.first.dy);
      for (final point in points.skip(1)) {
        path.lineTo(point.dx, point.dy);
      }

      canvas.drawPath(
        path,
        Paint()
          ..color = AppTheme.primaryGreen.withValues(alpha: 0.22)
          ..strokeWidth = 3
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round,
      );
    }

    final markerPoints = _markerPoints(points);
    for (final point in markerPoints) {
      canvas.drawCircle(
        point,
        6,
        Paint()..color = AppTheme.white.withValues(alpha: 0.96),
      );
      canvas.drawCircle(
        point,
        4.5,
        Paint()..color = AppTheme.primaryGreen,
      );
      canvas.drawCircle(point, 1.4, Paint()..color = AppTheme.white);
    }
  }

  @override
  bool shouldRepaint(covariant _MiniRoutePainter oldDelegate) {
    return oldDelegate.route != route;
  }

  List<_GeoPoint> _routePoints() {
    final points = <_GeoPoint>[
      ?_pointFrom(route['startPoint']),
      ...((route['stops'] as List? ?? [])
          .whereType<Map>()
          .map(_pointFrom)
          .whereType<_GeoPoint>()),
      ?_pointFrom(route['endPoint']),
    ];

    if (points.length >= 2) return points;
    return const [
      _GeoPoint(32.50, 71.45),
      _GeoPoint(32.58, 71.54),
    ];
  }

  List<Offset> _toCanvasPoints(List<_GeoPoint> points, Size size) {
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

    final latSpan = (maxLat - minLat).abs() < 0.0001
        ? 0.0001
        : (maxLat - minLat).abs();
    final lngSpan = (maxLng - minLng).abs() < 0.0001
        ? 0.0001
        : (maxLng - minLng).abs();
    const padding = 18.0;

    return points.map((point) {
      final x = padding +
          ((point.longitude - minLng) / lngSpan) * (size.width - padding * 2);
      final y = padding +
          (1 - ((point.latitude - minLat) / latSpan)) *
              (size.height - padding * 2);
      return Offset(x, y);
    }).toList();
  }

  List<Offset> _markerPoints(List<Offset> points) {
    if (points.length <= 3) return points;
    return [
      points.first,
      points[points.length ~/ 2],
      points.last,
    ];
  }

  _GeoPoint? _pointFrom(dynamic source) {
    if (source is! Map) return null;
    final lat = _numberFrom(source['latitude']);
    final lng = _numberFrom(source['longitude']);
    if (lat == null || lng == null) return null;
    return _GeoPoint(lat, lng);
  }

  double? _numberFrom(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '');
  }
}

class _GeoPoint {
  final double latitude;
  final double longitude;

  const _GeoPoint(this.latitude, this.longitude);
}
