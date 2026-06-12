import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../../core/widgets/bottom_nav.dart';
import '../../tracking/screens/bus_eat_screen.dart';

class FavouriteStopsScreen extends StatefulWidget {
  const FavouriteStopsScreen({super.key});

  @override
  State<FavouriteStopsScreen> createState() => _FavouriteStopsScreenState();
}

class _FavouriteStopsScreenState extends State<FavouriteStopsScreen> {
  List<dynamic> _favouriteRoutes = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadFavourites();
  }

  Future<void> _loadFavourites() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final favoriteIds = prefs.getStringList('favoriteRouteIds') ?? [];

      if (favoriteIds.isEmpty) {
        setState(() {
          _favouriteRoutes = [];
          _isLoading = false;
        });
        return;
      }

      final response = await ApiService.get('/routes');
      final routes = response['routes'] as List? ?? [];
      final favoriteSet = favoriteIds.toSet();

      setState(() {
        _favouriteRoutes = routes.where((route) {
          return favoriteSet.contains(route['routeId']?.toString());
        }).toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _removeFavourite(String routeId) async {
    final prefs = await SharedPreferences.getInstance();
    final ids = prefs.getStringList('favoriteRouteIds') ?? [];
    ids.removeWhere((id) => id == routeId);
    await prefs.setStringList('favoriteRouteIds', ids);
    _loadFavourites();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: AppBar(
        title: const Text('Favourite Stops'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.primaryGreen),
            )
          : _favouriteRoutes.isEmpty
          ? _buildEmptyState()
          : _buildRouteList(),
      bottomNavigationBar: AppBottomNav(
        currentIndex: 1,
        onTap: (index) {
          if (index == 0) Navigator.pop(context);
        },
      ),
    );
  }

  Widget _buildRouteList() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _favouriteRoutes.length,
      itemBuilder: (context, index) {
        final route = _favouriteRoutes[index];
        return _buildRouteCard(route);
      },
    );
  }

  Widget _buildRouteCard(Map<String, dynamic> route) {
    final stops = route['stops'] as List? ?? [];
    final stopCount = stops.length;
    final routeId = route['routeId']?.toString() ?? '';

    return GestureDetector(
      onTap: routeId.isEmpty
          ? null
          : () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => BusEatScreen(routeId: routeId)),
            ),
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        decoration: BoxDecoration(
          color: AppTheme.white,
          borderRadius: BorderRadius.circular(14),
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
            // Route header — green background matching design
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: const BoxDecoration(
                color: AppTheme.primaryGreen,
                borderRadius: BorderRadius.vertical(top: Radius.circular(14)),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      route['routeName'] ?? '',
                      style: const TextStyle(
                        color: AppTheme.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: AppTheme.white.withValues(alpha: 0.25),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '$stopCount Stops',
                      style: const TextStyle(
                        color: AppTheme.white,
                        fontSize: 11,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  GestureDetector(
                    onTap: () => _removeFavourite(routeId),
                    child: const Icon(
                      Icons.star,
                      color: Colors.amber,
                      size: 20,
                    ),
                  ),
                ],
              ),
            ),

            // Stops list
            ...stops.take(4).map((stop) => _buildStopRow(stop)),

            if (stops.length > 4)
              Padding(
                padding: const EdgeInsets.all(10),
                child: Text(
                  '+${stops.length - 4} more stops',
                  style: const TextStyle(
                    color: AppTheme.textGrey,
                    fontSize: 12,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildStopRow(Map<String, dynamic> stop) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: Color(0xFFF0F0F0))),
      ),
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
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              stop['name'] ?? '',
              style: const TextStyle(fontSize: 13, color: AppTheme.textDark),
            ),
          ),
          Text(
            stop['arrivalTimes']?.isNotEmpty == true
                ? stop['arrivalTimes'][0]
                : '',
            style: const TextStyle(fontSize: 12, color: AppTheme.textGrey),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.star_outline,
            size: 64,
            color: AppTheme.textGrey.withValues(alpha: 0.4),
          ),
          const SizedBox(height: 16),
          const Text(
            'No favourite routes yet',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w500,
              color: AppTheme.textGrey,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Add routes from the map screen',
            style: TextStyle(fontSize: 13, color: AppTheme.textGrey),
          ),
        ],
      ),
    );
  }
}
