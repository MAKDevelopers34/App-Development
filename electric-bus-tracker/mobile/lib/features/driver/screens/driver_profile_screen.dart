import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../auth/screens/choose_login_screen.dart';

class DriverProfileScreen extends StatefulWidget {
  const DriverProfileScreen({super.key});

  @override
  State<DriverProfileScreen> createState() => _DriverProfileScreenState();
}

class _DriverProfileScreenState extends State<DriverProfileScreen> {
  Map<String, dynamic>? _user;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final response = await ApiService.get('/auth/profile');
      setState(() {
        _user = response['user'];
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    if (!mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => const ChooseLoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      appBar: AppBar(
        title: const Text('My Profile'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.primaryGreen),
            )
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  // Avatar
                  Container(
                    width: 90,
                    height: 90,
                    decoration: const BoxDecoration(
                      color: AppTheme.primaryGreen,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.person,
                      size: 48,
                      color: AppTheme.white,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _user?['profileInfo']?['fullName'] ?? '',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textDark,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: AppTheme.lightGreen,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Text(
                      'DRIVER',
                      style: TextStyle(
                        color: AppTheme.primaryGreen,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),

                  const SizedBox(height: 24),

                  // Info card
                  Container(
                    decoration: BoxDecoration(
                      color: AppTheme.white,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      children: [
                        _infoRow(
                          Icons.person_outline,
                          'Username',
                          _user?['username'] ?? '',
                        ),
                        const Divider(height: 1, indent: 56),
                        _infoRow(
                          Icons.badge_outlined,
                          'User ID',
                          _user?['userId'] ?? '',
                        ),
                        const Divider(height: 1, indent: 56),
                        _infoRow(
                          Icons.email_outlined,
                          'Email',
                          _user?['email'] ?? '',
                        ),
                        const Divider(height: 1, indent: 56),
                        _infoRow(
                          Icons.phone_outlined,
                          'Phone',
                          _user?['profileInfo']?['phone'] ?? 'N/A',
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 24),

                  // Logout button
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: _logout,
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.redStatus,
                        side: const BorderSide(color: AppTheme.redStatus),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      icon: const Icon(Icons.logout, size: 18),
                      label: const Text('Logout'),
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _infoRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: [
          Icon(icon, color: AppTheme.primaryGreen, size: 20),
          const SizedBox(width: 14),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(fontSize: 11, color: AppTheme.textGrey),
              ),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 14,
                  color: AppTheme.textDark,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
