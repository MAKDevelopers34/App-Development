import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import '../../driver/screens/driver_dashboard_screen.dart';
import '../../admin/screens/admin_dashboard_screen.dart';
import 'reset_password_screen.dart';

class LoginScreen extends StatefulWidget {
  final String role;
  const LoginScreen({super.key, required this.role});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _userIdController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  String? _errorMessage;

  @override
  void dispose() {
    _usernameController.dispose();
    _userIdController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await ApiService.post('/auth/login', {
        'username': _usernameController.text.trim(),
        'userId': _userIdController.text.trim(),
        'password': _passwordController.text,
      });

      if (response['success'] == true) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('token', response['token']);
        await prefs.setString('role', response['user']['role']);
        await prefs.setString('userId', response['user']['userId'].toString());
        await prefs.setString('userDbId', response['user']['id'].toString());
        await prefs.setString('username', response['user']['username']);

        if (!mounted) return;

        if (response['user']['role'] == 'driver') {
          Navigator.pushAndRemoveUntil(
            context,
            MaterialPageRoute(builder: (_) => const DriverDashboardScreen()),
            (route) => false,
          );
        } else {
          Navigator.pushAndRemoveUntil(
            context,
            MaterialPageRoute(builder: (_) => const AdminDashboardScreen()),
            (route) => false,
          );
        }
      } else {
        setState(() {
          _errorMessage = response['message'] ?? 'Login failed';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Connection error. Check internet.';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDriver = widget.role == 'driver';

    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(isDriver ? 'Driver Login' : 'Admin Login'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 20),

              // Avatar icon
              Center(
                child: Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    color: AppTheme.lightGreen,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    isDriver ? Icons.person : Icons.admin_panel_settings,
                    size: 40,
                    color: AppTheme.primaryGreen,
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Username field
              const Text(
                'Username',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.textDark,
                ),
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _usernameController,
                decoration: const InputDecoration(
                  hintText: 'Enter your username',
                  prefixIcon: Icon(
                    Icons.person_outline,
                    color: AppTheme.textGrey,
                    size: 20,
                  ),
                ),
                validator: (v) => v!.isEmpty ? 'Username is required' : null,
              ),
              const SizedBox(height: 16),

              // User ID field
              const Text(
                'User ID',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.textDark,
                ),
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _userIdController,
                decoration: const InputDecoration(
                  hintText: 'Enter your user ID',
                  prefixIcon: Icon(
                    Icons.badge_outlined,
                    color: AppTheme.textGrey,
                    size: 20,
                  ),
                ),
                validator: (v) => v!.isEmpty ? 'User ID is required' : null,
              ),
              const SizedBox(height: 16),

              // Password field
              const Text(
                'Password',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.textDark,
                ),
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _passwordController,
                obscureText: _obscurePassword,
                decoration: InputDecoration(
                  hintText: 'Enter your password',
                  prefixIcon: const Icon(
                    Icons.lock_outline,
                    color: AppTheme.textGrey,
                    size: 20,
                  ),
                  suffixIcon: IconButton(
                    icon: Icon(
                      _obscurePassword
                          ? Icons.visibility_off_outlined
                          : Icons.visibility_outlined,
                      color: AppTheme.textGrey,
                      size: 20,
                    ),
                    onPressed: () =>
                        setState(() => _obscurePassword = !_obscurePassword),
                  ),
                ),
                validator: (v) => v!.isEmpty ? 'Password is required' : null,
              ),

              // Error message
              if (_errorMessage != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.redStatus.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: AppTheme.redStatus.withValues(alpha: 0.3),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.error_outline,
                        color: AppTheme.redStatus,
                        size: 16,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: const TextStyle(
                            color: AppTheme.redStatus,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              const SizedBox(height: 28),

              // Login button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _login,
                  child: _isLoading
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            color: AppTheme.white,
                            strokeWidth: 2.5,
                          ),
                        )
                      : const Text('Login'),
                ),
              ),

              const SizedBox(height: 16),

              // Forgot password
              Center(
                child: TextButton(
                  onPressed: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const ResetPasswordScreen(),
                    ),
                  ),
                  child: const Text(
                    'Forgot Password?',
                    style: TextStyle(
                      color: AppTheme.primaryGreen,
                      fontSize: 13,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
