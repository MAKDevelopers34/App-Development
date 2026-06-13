import 'package:flutter/material.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/real_bus_map.dart';
import '../../tracking/screens/bus_eat_screen.dart';
import 'add_route_screen.dart';
import '../utils/admin_navigation.dart';

class ManageRoutesScreen extends StatefulWidget {
  const ManageRoutesScreen({super.key});

  @override
  State<ManageRoutesScreen> createState() => _ManageRoutesScreenState();
}

class _ManageRoutesScreenState extends State<ManageRoutesScreen> {
  List<dynamic> _routes = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadRoutes();
  }

  Future<void> _loadRoutes() async {
    setState(() => _isLoading = true);
    try {
      final res = await ApiService.get('/routes');
      if (!mounted) return;
      setState(() {
        _routes = res['routes'] ?? [];
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<void> _openAddRoute() async {
    final created = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const AddRouteScreen()),
    );
    if (created == true) _loadRoutes();
  }

  Future<void> _deleteRoute(String routeId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Route'),
        content: const Text('Are you sure you want to delete this route?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: AppTheme.redStatus),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await ApiService.delete('/routes/$routeId');
      _loadRoutes();
    }
  }

  void _openRouteMap(Map<String, dynamic> route) {
    final routeId = route['routeId']?.toString();
    if (routeId == null || routeId.isEmpty) return;

    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => BusEatScreen(routeId: routeId)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      appBar: AppBar(
        title: const Text('Manage Routes'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => AdminNavigation.goDashboard(context),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: IconButton.filled(
              onPressed: _openAddRoute,
              icon: const Icon(Icons.add, size: 18),
              tooltip: 'Add route',
            ),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.primaryGreen),
            )
          : _routes.isEmpty
          ? const Center(
              child: Text(
                'No routes found',
                style: TextStyle(color: AppTheme.textGrey),
              ),
            )
          : Column(
              children: [
                SizedBox(
                  height: 220,
                  child: RealBusMap(routes: _routes, forcedZoom: 9.8),
                ),
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: _routes.length,
                    itemBuilder: (context, i) => _buildRouteCard(_routes[i]),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildRouteCard(Map<String, dynamic> route) {
    final stops = route['stops'] as List? ?? [];

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 6)],
      ),
      child: Column(
        children: [
          InkWell(
            onTap: () => _openRouteMap(route),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(14)),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: const BoxDecoration(
                color: AppTheme.primaryGreen,
                borderRadius: BorderRadius.vertical(top: Radius.circular(14)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.route, color: AppTheme.white, size: 16),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      route['routeName'] ?? '',
                      style: const TextStyle(
                        color: AppTheme.white,
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                      ),
                    ),
                  ),
                  const Icon(
                    Icons.map_outlined,
                    color: AppTheme.white,
                    size: 17,
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: [
                _routeDetailRow('From', route['startPoint']?['name'] ?? ''),
                const SizedBox(height: 6),
                _routeDetailRow('To', route['endPoint']?['name'] ?? ''),
                const SizedBox(height: 6),
                _routeDetailRow(
                  'Stops',
                  '${route['stopCount'] ?? stops.length} stops',
                ),
                const SizedBox(height: 6),
                _routeDetailRow(
                  'Distance',
                  '${route['totalDistance'] ?? 0} km',
                ),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton.icon(
                      onPressed: () => _openRouteMap(route),
                      icon: const Icon(Icons.map_outlined, size: 16),
                      label: const Text('View Map'),
                    ),
                    const SizedBox(width: 8),
                    InkWell(
                      onTap: () =>
                          _deleteRoute(route['routeId']?.toString() ?? ''),
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: AppTheme.redStatus,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          'Delete',
                          style: TextStyle(color: AppTheme.white, fontSize: 11),
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
    );
  }

  Widget _routeDetailRow(String label, String value) {
    return Row(
      children: [
        SizedBox(
          width: 70,
          child: Text(
            label,
            style: const TextStyle(fontSize: 12, color: AppTheme.textGrey),
          ),
        ),
        Expanded(
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: AppTheme.textDark,
            ),
          ),
        ),
      ],
    );
  }
}
