import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../tracking/screens/bus_eat_screen.dart';

class RouteSearchScreen extends StatefulWidget {
  const RouteSearchScreen({super.key});

  @override
  State<RouteSearchScreen> createState() => _RouteSearchScreenState();
}

class _RouteSearchScreenState extends State<RouteSearchScreen> {
  final TextEditingController _searchController = TextEditingController();
  List<dynamic> _routes = [];
  List<dynamic> _searchResults = [];
  bool _isLoading = true;
  bool _isSearching = false;

  @override
  void initState() {
    super.initState();
    _loadAllRoutes();
  }

  Future<void> _loadAllRoutes() async {
    try {
      final response = await ApiService.get('/routes');
      setState(() {
        _routes = response['routes'] ?? [];
        _searchResults = _routes;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _searchRoutes(String query) async {
    if (query.isEmpty) {
      setState(() => _searchResults = _routes);
      return;
    }
    setState(() => _isSearching = true);
    try {
      final response = await ApiService.get('/routes/search?query=$query');
      setState(() {
        _searchResults = response['routes'] ?? [];
        _isSearching = false;
      });
    } catch (e) {
      setState(() => _isSearching = false);
    }
  }

  Future<void> _addToFavourites(String routeId) async {
    await ApiService.post('/routes/favorites', {'routeId': routeId});
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Added to favourites'),
        backgroundColor: AppTheme.primaryGreen,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      appBar: AppBar(
        backgroundColor: AppTheme.white,
        title: const Text('Search Routes'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Column(
        children: [
          // Search bar
          Container(
            color: AppTheme.white,
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              onChanged: _searchRoutes,
              decoration: InputDecoration(
                hintText: 'Search by route or stop name...',
                prefixIcon: const Icon(
                  Icons.search,
                  color: AppTheme.primaryGreen,
                ),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 18),
                        onPressed: () {
                          _searchController.clear();
                          _searchRoutes('');
                        },
                      )
                    : null,
              ),
            ),
          ),

          const SizedBox(height: 8),

          // Results
          Expanded(
            child: _isLoading || _isSearching
                ? const Center(
                    child: CircularProgressIndicator(
                      color: AppTheme.primaryGreen,
                    ),
                  )
                : _searchResults.isEmpty
                ? const Center(
                    child: Text(
                      'No routes found',
                      style: TextStyle(color: AppTheme.textGrey),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    itemCount: _searchResults.length,
                    itemBuilder: (context, index) =>
                        _buildRouteCard(_searchResults[index]),
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
        boxShadow: [
          BoxShadow(
            color: AppTheme.cardShadow,
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          // Route header
          GestureDetector(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => BusEatScreen(routeId: route['routeId']),
              ),
            ),
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: const BoxDecoration(
                color: AppTheme.primaryGreen,
                borderRadius: BorderRadius.vertical(top: Radius.circular(14)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.route, color: AppTheme.white, size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          route['routeName'] ?? '',
                          style: const TextStyle(
                            color: AppTheme.white,
                            fontWeight: FontWeight.w600,
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${route['totalDistance'] ?? 0} km  •  '
                          '${route['estimatedTotalTime'] ?? 0} mins',
                          style: TextStyle(
                            color: AppTheme.white.withOpacity(0.85),
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(
                      Icons.star_border,
                      color: AppTheme.white,
                      size: 20,
                    ),
                    onPressed: () => _addToFavourites(route['routeId']),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                ],
              ),
            ),
          ),

          // Stops preview
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: stops.take(3).map((stop) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    children: [
                      Container(
                        width: 7,
                        height: 7,
                        decoration: const BoxDecoration(
                          color: AppTheme.primaryGreen,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          stop['name'] ?? '',
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppTheme.textDark,
                          ),
                        ),
                      ),
                      Text(
                        stop['arrivalTimes']?.isNotEmpty == true
                            ? stop['arrivalTimes'][0]
                            : '',
                        style: const TextStyle(
                          fontSize: 11,
                          color: AppTheme.textGrey,
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }
}
