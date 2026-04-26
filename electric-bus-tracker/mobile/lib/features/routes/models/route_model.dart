class BusStop {
  final String stopId;
  final String name;
  final double latitude;
  final double longitude;
  final int order;
  final List<String> arrivalTimes;

  BusStop({
    required this.stopId,
    required this.name,
    required this.latitude,
    required this.longitude,
    required this.order,
    required this.arrivalTimes,
  });

  factory BusStop.fromJson(Map<String, dynamic> json) => BusStop(
    stopId: json['stopId'] ?? '',
    name: json['name'] ?? '',
    latitude: (json['latitude'] ?? 0).toDouble(),
    longitude: (json['longitude'] ?? 0).toDouble(),
    order: json['order'] ?? 0,
    arrivalTimes: List<String>.from(json['arrivalTimes'] ?? []),
  );
}

class RouteModel {
  final String routeId;
  final String routeName;
  final Map<String, dynamic> startPoint;
  final Map<String, dynamic> endPoint;
  final List<BusStop> stops;
  final double totalDistance;
  final int estimatedTotalTime;
  final List<dynamic> schedule;

  RouteModel({
    required this.routeId,
    required this.routeName,
    required this.startPoint,
    required this.endPoint,
    required this.stops,
    required this.totalDistance,
    required this.estimatedTotalTime,
    required this.schedule,
  });

  factory RouteModel.fromJson(Map<String, dynamic> json) => RouteModel(
    routeId: json['routeId'] ?? '',
    routeName: json['routeName'] ?? '',
    startPoint: json['startPoint'] ?? {},
    endPoint: json['endPoint'] ?? {},
    stops: (json['stops'] as List? ?? [])
        .map((s) => BusStop.fromJson(s))
        .toList(),
    totalDistance: (json['totalDistance'] ?? 0).toDouble(),
    estimatedTotalTime: json['estimatedTotalTime'] ?? 0,
    schedule: json['schedule'] ?? [],
  );
}
