import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';

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
      setState(() {
        _routes = res['routes'] ?? [];
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      appBar: AppBar(
        title: const Text('Manage Routes'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: GestureDetector(
              onTap: () {
                // Navigate to create route screen
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text(
                      'Creating route via map — coming in Phase 6!',
                    ),
                    backgroundColor: AppTheme.primaryGreen,
                  ),
                );
              },
              child: Container(
                width: 32,
                height: 32,
                decoration: const BoxDecoration(
                  color: AppTheme.primaryGreen,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.add, color: AppTheme.white, size: 18),
              ),
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
          : ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _routes.length,
              itemBuilder: (context, i) => _buildRouteCard(_routes[i]),
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
          // Route name header
          Container(
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
                Text(
                  'Edit',
                  style: TextStyle(
                    color: AppTheme.white.withValues(alpha: 0.85),
                    fontSize: 12,
                    decoration: TextDecoration.underline,
                  ),
                ),
              ],
            ),
          ),

          // Route details
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: [
                _routeDetailRow('From', route['startPoint']?['name'] ?? ''),
                const SizedBox(height: 6),
                _routeDetailRow('To', route['endPoint']?['name'] ?? ''),
                const SizedBox(height: 6),
                _routeDetailRow('Stops', '${stops.length} stops'),
                const SizedBox(height: 6),
                _routeDetailRow(
                  'Distance',
                  '${route['totalDistance'] ?? 0} km',
                ),

                const SizedBox(height: 10),

                // Delete button
                Align(
                  alignment: Alignment.centerRight,
                  child: GestureDetector(
                    onTap: () => _deleteRoute(route['routeId']),
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
        Text(
          value,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: AppTheme.textDark,
          ),
        ),
      ],
    );
  }
}
