import 'dart:async';
import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../../core/widgets/bottom_nav.dart';
import '../../../core/widgets/real_bus_map.dart';
import '../../routes/screens/favourite_stops_screen.dart';
import '../../routes/screens/route_search_screen.dart';
import 'bus_eat_screen.dart';

class PassengerMapScreen extends StatefulWidget {
  const PassengerMapScreen({super.key});

  @override
  State<PassengerMapScreen> createState() => _PassengerMapScreenState();
}

class _PassengerMapScreenState extends State<PassengerMapScreen> {
  final TextEditingController _searchController = TextEditingController();

  List<dynamic> _activeBuses = [];
  List<dynamic> _routes = [];
  bool _isLoading = true;
  int _currentNavIndex = 0;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadMapData();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _loadActiveBuses(),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  List<dynamic> get _filteredBuses {
    final query = _searchController.text.trim().toLowerCase();
    if (query.isEmpty) return _activeBuses;

    return _activeBuses.where((bus) {
      final busNumber = bus['busNumber']?.toString().toLowerCase() ?? '';
      final routeName = bus['routeName']?.toString().toLowerCase() ?? '';
      final driverName = bus['driverName']?.toString().toLowerCase() ?? '';
      return busNumber.contains(query) ||
          routeName.contains(query) ||
          driverName.contains(query);
    }).toList();
  }

  Future<void> _loadMapData() async {
    try {
      final routesResponse = await ApiService.get('/routes');
      final routeSummaries = routesResponse['routes'] as List? ?? [];
      final detailedRoutes = await Future.wait(
        routeSummaries.map((route) async {
          final routeId = route['routeId']?.toString();
          if (routeId == null || routeId.isEmpty) return route;

          try {
            final detail = await ApiService.get('/routes/$routeId');
            return detail['route'] ?? route;
          } catch (_) {
            return route;
          }
        }),
      );
      final busesResponse = await ApiService.get('/gps/active-buses');

      if (!mounted) return;
      setState(() {
        _routes = detailedRoutes;
        _activeBuses = busesResponse['buses'] as List? ?? [];
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadActiveBuses() async {
    try {
      final response = await ApiService.get('/gps/active-buses');
      if (response['success'] == true) {
        if (!mounted) return;
        setState(() {
          _activeBuses = response['buses'] as List? ?? [];
          _isLoading = false;
        });
      } else {
        if (!mounted) return;
        setState(() => _isLoading = false);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  void _showBusEAT(String routeId) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => BusEatScreen(routeId: routeId)),
    );
  }

  void _openRouteSearch() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const RouteSearchScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final visibleBuses = _filteredBuses;

    return Scaffold(
      backgroundColor: AppTheme.white,
      body: SafeArea(
        child: Stack(
          children: [
            RealBusMap(
              routes: _routes,
              buses: visibleBuses,
              onBusTap: (bus) {
                final routeId = bus['routeId']?.toString() ?? '';
                if (routeId.isNotEmpty) _showBusEAT(routeId);
              },
            ),
            Positioned(top: 12, left: 12, right: 12, child: _buildSearchBar()),
            Positioned(
              bottom: 90,
              left: 12,
              right: 12,
              child: _buildLiveBusPanel(visibleBuses),
            ),
            if (_isLoading)
              const Center(
                child: CircularProgressIndicator(color: AppTheme.primaryGreen),
              ),
          ],
        ),
      ),
      bottomNavigationBar: AppBottomNav(
        currentIndex: _currentNavIndex,
        onTap: (index) {
          setState(() => _currentNavIndex = index);
          if (index == 1) {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const FavouriteStopsScreen()),
            );
          }
        },
      ),
    );
  }

  Widget _buildSearchBar() {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: AppTheme.cardShadow,
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: AppTheme.primaryGreen,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                const Text(
                  'Electric Bus Tracking',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.primaryGreen,
                  ),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(
                    Icons.route_outlined,
                    color: AppTheme.primaryGreen,
                    size: 20,
                  ),
                  onPressed: _openRouteSearch,
                  tooltip: 'Routes',
                  constraints: const BoxConstraints(),
                  padding: EdgeInsets.zero,
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
            child: Row(
              children: [
                Expanded(
                  child: Container(
                    height: 38,
                    decoration: BoxDecoration(
                      color: AppTheme.bgGrey,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: TextField(
                      controller: _searchController,
                      onChanged: (_) => setState(() {}),
                      style: const TextStyle(fontSize: 13),
                      decoration: const InputDecoration(
                        hintText: 'Search bus, route, driver',
                        hintStyle: TextStyle(
                          color: AppTheme.textGrey,
                          fontSize: 13,
                        ),
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                        isDense: true,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                SizedBox(
                  height: 38,
                  child: ElevatedButton(
                    onPressed: _loadActiveBuses,
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      minimumSize: Size.zero,
                    ),
                    child: const Icon(Icons.refresh, size: 18),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLiveBusPanel(List<dynamic> buses) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 8)],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'Live Buses: ${buses.length}',
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.primaryGreen,
                ),
              ),
              const Spacer(),
              _legendItem(AppTheme.primaryGreen, 'Active'),
            ],
          ),
          const SizedBox(height: 10),
          SizedBox(
            height: 78,
            child: buses.isEmpty
                ? const Center(
                    child: Text(
                      'No matching live buses',
                      style: TextStyle(color: AppTheme.textGrey, fontSize: 12),
                    ),
                  )
                : ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: buses.length,
                    separatorBuilder: (context, index) =>
                        const SizedBox(width: 10),
                    itemBuilder: (context, index) =>
                        _buildBusCard(buses[index]),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildBusCard(Map<String, dynamic> bus) {
    final routeId = bus['routeId']?.toString() ?? '';
    final title =
        bus['busNumber']?.toString() ?? bus['busId']?.toString() ?? 'BUS';
    final routeName = bus['routeName']?.toString() ?? 'Route N/A';
    final speed = bus['speed']?.toString() ?? '0';

    return GestureDetector(
      onTap: routeId.isEmpty ? null : () => _showBusEAT(routeId),
      child: Container(
        width: 210,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: AppTheme.lightGreen,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
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
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textDark,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    routeName,
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppTheme.textGrey,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '$speed km/h',
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppTheme.primaryGreen,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _legendItem(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(
          label,
          style: const TextStyle(fontSize: 11, color: AppTheme.textDark),
        ),
      ],
    );
  }
}
