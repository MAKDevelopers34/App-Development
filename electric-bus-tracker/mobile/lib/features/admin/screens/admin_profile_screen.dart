import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../auth/screens/choose_login_screen.dart';
import 'changing_password_screen.dart';

class AdminProfileScreen extends StatefulWidget {
  const AdminProfileScreen({super.key});

  @override
  State<AdminProfileScreen> createState() => _AdminProfileScreenState();
}

class _AdminProfileScreenState extends State<AdminProfileScreen> {
  Map<String, dynamic>? _user;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final res = await ApiService.get('/auth/profile');
      setState(() {
        _user = res['user'];
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
        title: const Text('Back to Dashboard'),
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
                  const SizedBox(height: 10),

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
                  const SizedBox(height: 24),

                  // Info card — matching design
                  Container(
                    decoration: BoxDecoration(
                      color: AppTheme.white,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      children: [
                        _infoRow(
                          'Name',
                          _user?['profileInfo']?['fullName'] ?? 'Admin User',
                        ),
                        const Divider(height: 1, indent: 16),
                        _infoRow('User ID', _user?['userId'] ?? ''),
                        const Divider(height: 1, indent: 16),
                        _infoRow('Email', _user?['email'] ?? ''),
                        const Divider(height: 1, indent: 16),
                        _infoRow(
                          'Phone Number',
                          _user?['profileInfo']?['phone'] ?? 'N/A',
                        ),
                        const Divider(height: 1, indent: 16),
                        _infoRow(
                          'Contact Number',
                          _user?['profileInfo']?['phone'] ?? 'N/A',
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 20),

                  // Reset Password button — red as in design
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => const ChangingPasswordScreen(),
                        ),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.redStatus,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      icon: const Icon(Icons.lock_reset, size: 18),
                      label: const Text('Reset Password'),
                    ),
                  ),

                  const SizedBox(height: 12),

                  // Logout button — green outline
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: _logout,
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.primaryGreen,
                        side: const BorderSide(color: AppTheme.primaryGreen),
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

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: const TextStyle(fontSize: 13, color: AppTheme.textGrey),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.textDark,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
