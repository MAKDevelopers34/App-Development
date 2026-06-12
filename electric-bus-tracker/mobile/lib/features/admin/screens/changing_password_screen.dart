import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';

class ChangingPasswordScreen extends StatefulWidget {
  const ChangingPasswordScreen({super.key});

  @override
  State<ChangingPasswordScreen> createState() => _ChangingPasswordScreenState();
}

class _ChangingPasswordScreenState extends State<ChangingPasswordScreen> {
  final _currentPassController = TextEditingController();
  final _newPassController = TextEditingController();
  final _confirmPassController = TextEditingController();
  bool _isLoading = false;
  bool _obscure1 = true;
  bool _obscure2 = true;
  bool _obscure3 = true;
  String? _error;
  String? _success;

  Future<void> _changePassword() async {
    if (_newPassController.text != _confirmPassController.text) {
      setState(() => _error = 'New passwords do not match');
      return;
    }
    if (_newPassController.text.length < 6) {
      setState(() => _error = 'Password must be at least 6 characters');
      return;
    }
    setState(() {
      _isLoading = true;
      _error = null;
      _success = null;
    });

    try {
      final res = await ApiService.post('/auth/change-password', {
        'currentPassword': _currentPassController.text,
        'newPassword': _newPassController.text,
      });

      if (res['success'] == true) {
        setState(() {
          _success = 'Password changed successfully!';
          _isLoading = false;
        });
        _currentPassController.clear();
        _newPassController.clear();
        _confirmPassController.clear();
      } else {
        setState(() {
          _error = res['message'] ?? 'Failed to change password';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Connection error';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: AppBar(
        title: const Text('Change Password'),
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
            _passwordField(
              'Current Password',
              _currentPassController,
              _obscure1,
              () => setState(() => _obscure1 = !_obscure1),
            ),
            const SizedBox(height: 16),
            _passwordField(
              'New Password',
              _newPassController,
              _obscure2,
              () => setState(() => _obscure2 = !_obscure2),
            ),
            const SizedBox(height: 16),
            _passwordField(
              'Confirm Password',
              _confirmPassController,
              _obscure3,
              () => setState(() => _obscure3 = !_obscure3),
            ),

            if (_error != null) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.redStatus.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _error!,
                  style: const TextStyle(
                    color: AppTheme.redStatus,
                    fontSize: 12,
                  ),
                ),
              ),
            ],

            if (_success != null) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.lightGreen,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _success!,
                  style: const TextStyle(
                    color: AppTheme.darkGreen,
                    fontSize: 12,
                  ),
                ),
              ),
            ],

            const SizedBox(height: 28),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _changePassword,
                child: _isLoading
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          color: AppTheme.white,
                          strokeWidth: 2.5,
                        ),
                      )
                    : const Text('OK'),
              ),
            ),

            const SizedBox(height: 12),
            Center(
              child: TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text(
                  'Back to Profile',
                  style: TextStyle(color: AppTheme.primaryGreen, fontSize: 13),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _passwordField(
    String label,
    TextEditingController controller,
    bool obscure,
    VoidCallback toggle,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: AppTheme.textDark,
          ),
        ),
        const SizedBox(height: 8),
        TextFormField(
          controller: controller,
          obscureText: obscure,
          decoration: InputDecoration(
            hintText: 'Enter $label',
            suffixIcon: IconButton(
              icon: Icon(
                obscure
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined,
                color: AppTheme.textGrey,
                size: 20,
              ),
              onPressed: toggle,
            ),
          ),
        ),
      ],
    );
  }
}
