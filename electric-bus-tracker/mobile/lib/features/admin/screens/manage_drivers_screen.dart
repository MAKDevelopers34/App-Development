import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import 'driver_registration_screen.dart';
import 'edit_driver_screen.dart';

class ManageDriversScreen extends StatefulWidget {
  const ManageDriversScreen({super.key});

  @override
  State<ManageDriversScreen> createState() => _ManageDriversScreenState();
}

class _ManageDriversScreenState extends State<ManageDriversScreen> {
  List<dynamic> _drivers = [];
  List<dynamic> _filtered = [];
  bool _isLoading = true;
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadDrivers();
  }

  Future<void> _loadDrivers() async {
    setState(() => _isLoading = true);
    try {
      final res = await ApiService.get('/admin/drivers');
      setState(() {
        _drivers = res['drivers'] ?? [];
        _filtered = _drivers;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  void _search(String query) {
    setState(() {
      _filtered = _drivers.where((d) {
        final name =
            d['profileInfo']?['fullName']?.toString().toLowerCase() ?? '';
        final username = d['username']?.toString().toLowerCase() ?? '';
        return name.contains(query.toLowerCase()) ||
            username.contains(query.toLowerCase());
      }).toList();
    });
  }

  Future<void> _toggleStatus(String driverId, bool isActive) async {
    try {
      if (isActive) {
        await ApiService.post('/admin/drivers/$driverId/deactivate', {});
      } else {
        await ApiService.post('/admin/drivers/$driverId/activate', {});
      }
      _loadDrivers();
    } catch (e) {
      debugPrint('Toggle error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      appBar: AppBar(
        title: const Text('Manage Drivers'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: GestureDetector(
              onTap: () async {
                await Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const DriverRegistrationScreen(),
                  ),
                );
                _loadDrivers();
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
      body: Column(
        children: [
          Container(
            color: AppTheme.white,
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _searchController,
              onChanged: _search,
              decoration: InputDecoration(
                hintText: 'Search by name...',
                prefixIcon: const Icon(
                  Icons.search,
                  color: AppTheme.primaryGreen,
                  size: 20,
                ),
                isDense: true,
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 18),
                        onPressed: () {
                          _searchController.clear();
                          _search('');
                        },
                      )
                    : null,
              ),
            ),
          ),

          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                      color: AppTheme.primaryGreen,
                    ),
                  )
                : _filtered.isEmpty
                ? const Center(
                    child: Text(
                      'No drivers found',
                      style: TextStyle(color: AppTheme.textGrey),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: _filtered.length,
                    itemBuilder: (context, i) => _buildDriverCard(_filtered[i]),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildDriverCard(Map<String, dynamic> driver) {
    final isActive = driver['isActive'] == true;
    final fullName = driver['profileInfo']?['fullName'] ?? driver['username'];
    final phone = driver['profileInfo']?['phone'] ?? 'N/A';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 4)],
      ),
      child: Row(
        children: [
          // Avatar
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: isActive ? AppTheme.lightGreen : const Color(0xFFFEECEC),
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.person,
              color: isActive ? AppTheme.primaryGreen : AppTheme.redStatus,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),

          // Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  fullName,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textDark,
                  ),
                ),
                Text(
                  driver['userId'] ?? '',
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppTheme.textGrey,
                  ),
                ),
                Text(
                  phone,
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppTheme.textGrey,
                  ),
                ),
              ],
            ),
          ),

          // Status + actions column
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              // Status badge — Active/Inactive
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: isActive ? AppTheme.primaryGreen : AppTheme.redStatus,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  isActive ? 'Active' : 'Inactive',
                  style: const TextStyle(
                    color: AppTheme.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(height: 6),

              // Action buttons row
              Row(
                children: [
                  // Edit button
                  GestureDetector(
                    onTap: () async {
                      await Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => EditDriverScreen(driver: driver),
                        ),
                      );
                      _loadDrivers();
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryGreen,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Text(
                        'Edit',
                        style: TextStyle(color: AppTheme.white, fontSize: 10),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),

                  // Deactivate/Activate button
                  GestureDetector(
                    onTap: () => _toggleStatus(driver['_id'], isActive),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: isActive
                            ? AppTheme.redStatus
                            : AppTheme.primaryGreen,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        isActive ? 'Deactivate' : 'Activate',
                        style: const TextStyle(
                          color: AppTheme.white,
                          fontSize: 10,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
