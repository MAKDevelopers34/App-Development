import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import 'choose_login_screen.dart';

class CreateNewPasswordScreen extends StatefulWidget {
  final String email;
  final String code;

  const CreateNewPasswordScreen({
    super.key,
    required this.email,
    required this.code,
  });

  @override
  State<CreateNewPasswordScreen> createState() =>
      _CreateNewPasswordScreenState();
}

class _CreateNewPasswordScreenState extends State<CreateNewPasswordScreen> {
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _isLoading = false;
  bool _obscure1 = true;
  bool _obscure2 = true;
  String? _error;

  Future<void> _confirm() async {
    // Validation
    if (_newPasswordController.text.isEmpty ||
        _confirmPasswordController.text.isEmpty) {
      setState(() => _error = 'Please fill all fields');
      return;
    }

    if (_newPasswordController.text != _confirmPasswordController.text) {
      setState(() => _error = 'Passwords do not match');
      return;
    }

    if (_newPasswordController.text.length < 6) {
      setState(() => _error = 'Password must be at least 6 characters');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final res = await ApiService.post('/auth/reset-password', {
        'email': widget.email,
        'code': widget.code,
        'newPassword': _newPasswordController.text,
      });

      if (res['success'] == true) {
        if (!mounted) return;

        // Show success then go to login
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Password reset successfully! Please login.'),
            backgroundColor: AppTheme.primaryGreen,
            duration: Duration(seconds: 3),
          ),
        );

        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder: (_) => const ChooseLoginScreen()),
          (route) => false,
        );
      } else {
        setState(() {
          _error = res['message'] ?? 'Reset failed';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Connection error. Try again.';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: AppBar(
        title: const Text('Creating New Password'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 10),

            // Info box
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.lightGreen,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.info_outline,
                    color: AppTheme.primaryGreen,
                    size: 16,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Resetting password for: ${widget.email}',
                      style: const TextStyle(
                        color: AppTheme.darkGreen,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // New password
            const Text(
              'New Password',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _newPasswordController,
              obscureText: _obscure1,
              decoration: InputDecoration(
                hintText: 'Enter new password',
                prefixIcon: const Icon(
                  Icons.lock_outline,
                  color: AppTheme.textGrey,
                  size: 20,
                ),
                suffixIcon: IconButton(
                  icon: Icon(
                    _obscure1
                        ? Icons.visibility_off_outlined
                        : Icons.visibility_outlined,
                    color: AppTheme.textGrey,
                    size: 20,
                  ),
                  onPressed: () => setState(() => _obscure1 = !_obscure1),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Confirm password
            const Text(
              'Confirm Password',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _confirmPasswordController,
              obscureText: _obscure2,
              decoration: InputDecoration(
                hintText: 'Confirm new password',
                prefixIcon: const Icon(
                  Icons.lock_outline,
                  color: AppTheme.textGrey,
                  size: 20,
                ),
                suffixIcon: IconButton(
                  icon: Icon(
                    _obscure2
                        ? Icons.visibility_off_outlined
                        : Icons.visibility_outlined,
                    color: AppTheme.textGrey,
                    size: 20,
                  ),
                  onPressed: () => setState(() => _obscure2 = !_obscure2),
                ),
              ),
            ),

            // Error
            if (_error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.redStatus.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
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
                        _error!,
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

            const SizedBox(height: 32),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _confirm,
                child: _isLoading
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          color: AppTheme.white,
                          strokeWidth: 2.5,
                        ),
                      )
                    : const Text('Confirm'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
