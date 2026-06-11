import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class SchematicBusMap extends StatelessWidget {
  final List<dynamic> buses;
  final bool showEmptyState;

  const SchematicBusMap({
    super.key,
    required this.buses,
    this.showEmptyState = true,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return Stack(
          fit: StackFit.expand,
          children: [
            CustomPaint(
              painter: _SchematicBusPainter(buses),
              size: Size(constraints.maxWidth, constraints.maxHeight),
            ),
            if (buses.isEmpty && showEmptyState)
              Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.white,
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(color: AppTheme.cardShadow, blurRadius: 8),
                    ],
                  ),
                  child: const Text(
                    'No live buses right now',
                    style: TextStyle(
                      color: AppTheme.textGrey,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

class _SchematicBusPainter extends CustomPainter {
  final List<dynamic> buses;

  _SchematicBusPainter(this.buses);

  @override
  void paint(Canvas canvas, Size size) {
    _paintBackground(canvas, size);
    final routePath = _buildRoutePath(size);

    final routePaint = Paint()
      ..color = AppTheme.darkGreen.withValues(alpha: 0.35)
      ..strokeWidth = 10
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(routePath, routePaint);

    final routeLinePaint = Paint()
      ..color = AppTheme.primaryGreen
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(routePath, routeLinePaint);

    _paintStops(canvas, size);
    _paintBuses(canvas, size);
  }

  void _paintBackground(Canvas canvas, Size size) {
    final bg = Paint()..color = const Color(0xFFF1F7F3);
    canvas.drawRect(Offset.zero & size, bg);

    final gridPaint = Paint()
      ..color = AppTheme.darkGreen.withValues(alpha: 0.08)
      ..strokeWidth = 1;

    for (double x = -size.height; x < size.width; x += 48) {
      canvas.drawLine(
        Offset(x, size.height),
        Offset(x + size.height, 0),
        gridPaint,
      );
    }

    final districtPaint = Paint()
      ..color = AppTheme.primaryGreen.withValues(alpha: 0.06)
      ..style = PaintingStyle.fill;
    final districtPath = Path()
      ..moveTo(size.width * 0.08, size.height * 0.25)
      ..quadraticBezierTo(
        size.width * 0.42,
        size.height * 0.05,
        size.width * 0.88,
        size.height * 0.18,
      )
      ..quadraticBezierTo(
        size.width * 0.98,
        size.height * 0.58,
        size.width * 0.74,
        size.height * 0.86,
      )
      ..quadraticBezierTo(
        size.width * 0.35,
        size.height * 0.98,
        size.width * 0.1,
        size.height * 0.7,
      )
      ..close();
    canvas.drawPath(districtPath, districtPaint);
  }

  Path _buildRoutePath(Size size) {
    return Path()
      ..moveTo(size.width * 0.12, size.height * 0.78)
      ..cubicTo(
        size.width * 0.25,
        size.height * 0.58,
        size.width * 0.38,
        size.height * 0.72,
        size.width * 0.48,
        size.height * 0.48,
      )
      ..cubicTo(
        size.width * 0.58,
        size.height * 0.23,
        size.width * 0.78,
        size.height * 0.38,
        size.width * 0.88,
        size.height * 0.18,
      );
  }

  void _paintStops(Canvas canvas, Size size) {
    final stops = <Offset>[
      Offset(size.width * 0.12, size.height * 0.78),
      Offset(size.width * 0.31, size.height * 0.63),
      Offset(size.width * 0.48, size.height * 0.48),
      Offset(size.width * 0.68, size.height * 0.35),
      Offset(size.width * 0.88, size.height * 0.18),
    ];

    final stopPaint = Paint()..color = AppTheme.white;
    final ringPaint = Paint()
      ..color = AppTheme.primaryGreen
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;

    for (final stop in stops) {
      canvas.drawCircle(stop, 7, stopPaint);
      canvas.drawCircle(stop, 7, ringPaint);
    }
  }

  void _paintBuses(Canvas canvas, Size size) {
    final points = _busPoints(size);
    for (var i = 0; i < points.length; i += 1) {
      final point = points[i];
      final shadowPaint = Paint()
        ..color = Colors.black.withValues(alpha: 0.18)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
      canvas.drawCircle(point.translate(0, 2), 15, shadowPaint);

      final busPaint = Paint()..color = AppTheme.primaryGreen;
      canvas.drawCircle(point, 15, busPaint);

      final textPainter = TextPainter(
        text: const TextSpan(
          text: 'BUS',
          style: TextStyle(
            color: AppTheme.white,
            fontSize: 8,
            fontWeight: FontWeight.w700,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      textPainter.paint(
        canvas,
        point - Offset(textPainter.width / 2, textPainter.height / 2),
      );
    }
  }

  List<Offset> _busPoints(Size size) {
    if (buses.isEmpty) return [];

    final coordinates = buses.map((bus) {
      final location = bus['location'] ?? {};
      final lat = (location['latitude'] as num?)?.toDouble() ?? 32.5838;
      final lng = (location['longitude'] as num?)?.toDouble() ?? 71.5436;
      return _Coordinate(lat, lng);
    }).toList();

    final minLat = coordinates.map((c) => c.lat).reduce(
          (a, b) => a < b ? a : b,
        );
    final maxLat = coordinates.map((c) => c.lat).reduce(
          (a, b) => a > b ? a : b,
        );
    final minLng = coordinates.map((c) => c.lng).reduce(
          (a, b) => a < b ? a : b,
        );
    final maxLng = coordinates.map((c) => c.lng).reduce(
          (a, b) => a > b ? a : b,
        );

    return coordinates.asMap().entries.map((entry) {
      final fallbackProgress = (entry.key + 1) / (coordinates.length + 1);
      final xRatio = maxLng == minLng
          ? fallbackProgress
          : (entry.value.lng - minLng) / (maxLng - minLng);
      final yRatio = maxLat == minLat
          ? fallbackProgress
          : (maxLat - entry.value.lat) / (maxLat - minLat);

      final x = size.width * (0.14 + (xRatio * 0.72));
      final y = size.height * (0.18 + (yRatio * 0.62));
      return Offset(x, y);
    }).toList();
  }

  @override
  bool shouldRepaint(covariant _SchematicBusPainter oldDelegate) {
    return oldDelegate.buses != buses;
  }
}

class _Coordinate {
  final double lat;
  final double lng;

  _Coordinate(this.lat, this.lng);
}
