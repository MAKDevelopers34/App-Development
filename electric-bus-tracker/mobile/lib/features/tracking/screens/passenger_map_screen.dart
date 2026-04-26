import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'dart:async';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../../core/widgets/bottom_nav.dart';
import '../../routes/screens/favourite_stops_screen.dart';
import 'bus_eat_screen.dart';

class PassengerMapScreen extends StatefulWidget {
  const PassengerMapScreen({super.key});

  @override
  State<PassengerMapScreen> createState() => _PassengerMapScreenState();
}

class _PassengerMapScreenState extends State<PassengerMapScreen> {
  final Completer<GoogleMapController> _mapController = Completer();
  final TextEditingController _searchController = TextEditingController();

  Set<Marker> _markers = {};
  List<dynamic> _activeBuses = [];
  bool _isLoading = true;
  int _currentNavIndex = 0;
  Timer? _refreshTimer;

  // Mianwali center coordinates
  static const LatLng _mianwaliCenter = LatLng(32.5838, 71.5436);

  @override
  void initState() {
    super.initState();
    _loadActiveBuses();
    // Refresh every 5 seconds for live tracking
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

  Future<void> _loadActiveBuses() async {
    try {
      final response = await ApiService.get('/gps/active-buses');
      if (response['success'] == true) {
        final buses = response['buses'] as List? ?? [];
        setState(() {
          _activeBuses = buses;
          _markers = _buildMarkers(buses);
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Set<Marker> _buildMarkers(List<dynamic> buses) {
    return buses.map((bus) {
      final lat = bus['location']['latitude'];
      final lng = bus['location']['longitude'];
      return Marker(
        markerId: MarkerId(bus['busId']),
        position: LatLng(lat, lng),
        icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueGreen),
        infoWindow: InfoWindow(
          title: bus['busId'],
          snippet: 'Speed: ${bus['speed']} km/h',
          onTap: () => _showBusEAT(bus['routeId']),
        ),
      );
    }).toSet();
  }

  void _showBusEAT(String routeId) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => BusEatScreen(routeId: routeId)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      body: SafeArea(
        child: Stack(
          children: [
            // Google Map
            GoogleMap(
              initialCameraPosition: const CameraPosition(
                target: _mianwaliCenter,
                zoom: 12,
              ),
              onMapCreated: (controller) => _mapController.complete(controller),
              markers: _markers,
              myLocationEnabled: true,
              myLocationButtonEnabled: false,
              zoomControlsEnabled: false,
              mapToolbarEnabled: false,
            ),

            // Top search bar — matching your design
            Positioned(top: 12, left: 12, right: 12, child: _buildSearchBar()),

            // Legend — Active/Inactive — matching your design
            Positioned(bottom: 90, left: 12, child: _buildLegend()),

            // Loading indicator
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
          // Title row
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
              ],
            ),
          ),
          // Search row
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
                      style: const TextStyle(fontSize: 13),
                      decoration: const InputDecoration(
                        hintText: 'Enter stop',
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
                Expanded(
                  child: Container(
                    height: 38,
                    decoration: BoxDecoration(
                      color: AppTheme.bgGrey,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const TextField(
                      style: TextStyle(fontSize: 13),
                      decoration: InputDecoration(
                        hintText: 'Select stop',
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
                    child: const Text('Search', style: TextStyle(fontSize: 13)),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLegend() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(10),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 6)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Live Buses: ${_activeBuses.length}',
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: AppTheme.primaryGreen,
            ),
          ),
          _legendItem(AppTheme.primaryGreen, 'Active Bus'),
          const SizedBox(height: 4),
          _legendItem(AppTheme.redStatus, 'Inactive Bus'),
          const SizedBox(height: 4),
          _legendItem(AppTheme.orangeStatus, 'Your Location'),
        ],
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
