import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import 'add_duty_screen.dart';
import 'edit_duty_screen.dart';

class ManageDutiesScreen extends StatefulWidget {
  const ManageDutiesScreen({super.key});

  @override
  State<ManageDutiesScreen> createState() => _ManageDutiesScreenState();
}

class _ManageDutiesScreenState extends State<ManageDutiesScreen> {
  List<dynamic> _duties = [];
  List<dynamic> _filtered = [];
  bool _isLoading = true;
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadDuties();
  }

  Future<void> _loadDuties() async {
    setState(() => _isLoading = true);
    try {
      final res = await ApiService.get('/admin/duties');
      setState(() {
        _duties = res['duties'] ?? [];
        _filtered = _duties;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  void _search(String query) {
    setState(() {
      _filtered = _duties.where((d) {
        final route = d['route']?.toString().toLowerCase() ?? '';
        final driver = d['driver']?['username']?.toString().toLowerCase() ?? '';
        return route.contains(query.toLowerCase()) ||
            driver.contains(query.toLowerCase());
      }).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      appBar: AppBar(
        title: const Text('Manage Duties'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          // Add duty button — green circle as in design
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: GestureDetector(
              onTap: () async {
                await Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const AddDutyScreen()),
                );
                _loadDuties();
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
          // Search bar
          Container(
            color: AppTheme.white,
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _searchController,
              onChanged: _search,
              decoration: InputDecoration(
                hintText: 'Search duties...',
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
                      'No duties found',
                      style: TextStyle(color: AppTheme.textGrey),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: _filtered.length,
                    itemBuilder: (context, i) => _buildDutyCard(_filtered[i]),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildDutyCard(Map<String, dynamic> duty) {
    final driver = duty['driver'];
    final bus = duty['bus'];
    final status = duty['status'] as String;

    Color dotColor;
    switch (status) {
      case 'completed':
        dotColor = AppTheme.primaryGreen;
        break;
      case 'started':
        dotColor = AppTheme.orangeStatus;
        break;
      case 'skipped':
        dotColor = AppTheme.redStatus;
        break;
      default:
        dotColor = AppTheme.orangeStatus;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 4)],
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        leading: Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: dotColor, shape: BoxShape.circle),
        ),
        title: Text(
          duty['route'] ?? 'Route N/A',
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: AppTheme.textDark,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 3),
            Text(
              'Driver: ${driver?['username'] ?? 'N/A'}',
              style: const TextStyle(fontSize: 11, color: AppTheme.textGrey),
            ),
            Text(
              'Bus: ${bus?['busNumber'] ?? 'N/A'}  •  '
              '${duty['scheduledStartTime']} - '
              '${duty['scheduledEndTime']}',
              style: const TextStyle(fontSize: 11, color: AppTheme.textGrey),
            ),
          ],
        ),
        trailing: IconButton(
          icon: const Icon(
            Icons.edit_outlined,
            color: AppTheme.primaryGreen,
            size: 20,
          ),
          onPressed: () async {
            await Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => EditDutyScreen(duty: duty)),
            );
            _loadDuties();
          },
        ),
      ),
    );
  }
}
