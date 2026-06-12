import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../../admin/screens/changing_password_screen.dart';
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
      if (!mounted) return;
      setState(() {
        _user = response['user'];
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
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
    final profile = _user?['profileInfo'] ?? {};

    return Scaffold(
      backgroundColor: const Color(0xFFF7F8FA),
      body: SafeArea(
        child: _isLoading
            ? const Center(
                child: CircularProgressIndicator(color: AppTheme.primaryGreen),
              )
            : Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(18, 14, 18, 8),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton.icon(
                        onPressed: () => Navigator.pop(context),
                        icon: const Icon(Icons.arrow_back, size: 17),
                        label: const Text('Back to Dashboard'),
                        style: TextButton.styleFrom(
                          foregroundColor: AppTheme.textGrey,
                          padding: EdgeInsets.zero,
                        ),
                      ),
                    ),
                  ),
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(24, 20, 24, 24),
                      child: Column(
                        children: [
                          Container(
                            width: 90,
                            height: 90,
                            decoration: BoxDecoration(
                              color: AppTheme.primaryGreen,
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.2),
                                  blurRadius: 18,
                                  offset: const Offset(0, 8),
                                ),
                              ],
                            ),
                            child: const Icon(
                              Icons.person_outline,
                              color: AppTheme.white,
                              size: 48,
                            ),
                          ),
                          const SizedBox(height: 34),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              color: AppTheme.white,
                              borderRadius: BorderRadius.circular(8),
                              boxShadow: [
                                BoxShadow(
                                  color: AppTheme.cardShadow,
                                  blurRadius: 8,
                                  offset: const Offset(0, 3),
                                ),
                              ],
                            ),
                            child: Column(
                              children: [
                                _profileField(
                                  'Name',
                                  profile['fullName'] ?? 'N/A',
                                ),
                                const SizedBox(height: 16),
                                _profileField(
                                  'Email',
                                  _user?['email'] ?? 'N/A',
                                ),
                                const SizedBox(height: 16),
                                _profileField(
                                  'Phone Number',
                                  profile['phone'] ?? 'N/A',
                                ),
                                const SizedBox(height: 16),
                                _profileField(
                                  'License Number',
                                  profile['licenseNo'] ?? 'Not assigned',
                                ),
                                const SizedBox(height: 20),
                                SizedBox(
                                  width: double.infinity,
                                  child: OutlinedButton.icon(
                                    onPressed: () => Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (_) =>
                                            const ChangingPasswordScreen(),
                                      ),
                                    ),
                                    style: OutlinedButton.styleFrom(
                                      foregroundColor: AppTheme.primaryGreen,
                                      side: const BorderSide(
                                        color: AppTheme.primaryGreen,
                                      ),
                                      padding: const EdgeInsets.symmetric(
                                        vertical: 13,
                                      ),
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                    ),
                                    icon: const Icon(
                                      Icons.lock_reset,
                                      size: 18,
                                    ),
                                    label: const Text('Reset Password'),
                                  ),
                                ),
                                const SizedBox(height: 12),
                                SizedBox(
                                  width: double.infinity,
                                  child: ElevatedButton.icon(
                                    onPressed: _logout,
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: AppTheme.redStatus,
                                      foregroundColor: AppTheme.white,
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                    ),
                                    icon: const Icon(Icons.logout, size: 18),
                                    label: const Text('Logout'),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
      ),
      bottomNavigationBar: _buildProfileFooter(context),
    );
  }

  Widget _profileField(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Text(
            label,
            style: const TextStyle(
              color: AppTheme.textGrey,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        const SizedBox(height: 7),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
          decoration: BoxDecoration(
            color: const Color(0xFFF8F8FA),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFFDDE1E6)),
          ),
          child: Text(
            value,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildProfileFooter(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        height: 64,
        padding: const EdgeInsets.fromLTRB(12, 6, 12, 8),
        decoration: BoxDecoration(
          color: AppTheme.white,
          boxShadow: [
            BoxShadow(
              color: AppTheme.cardShadow,
              blurRadius: 10,
              offset: const Offset(0, -3),
            ),
          ],
        ),
        child: Row(
          children: [
            Expanded(
              child: _footerButton(
                icon: Icons.assignment_outlined,
                label: "Today's Duty",
                selected: true,
                onTap: () => Navigator.pop(context),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _footerButton(
                icon: Icons.calendar_month_outlined,
                label: 'Schedule',
                selected: false,
                onTap: () => Navigator.pop(context),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _footerButton({
    required IconData icon,
    required String label,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        decoration: BoxDecoration(
          color: selected ? AppTheme.primaryGreen : AppTheme.bgGrey,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 18,
              color: selected ? AppTheme.white : AppTheme.textDark,
            ),
            const SizedBox(height: 3),
            Text(
              label,
              style: TextStyle(
                color: selected ? AppTheme.white : AppTheme.textDark,
                fontSize: 10,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
