import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
import 'create_new_password_screen.dart';

class ResetPasswordScreen extends StatefulWidget {
  const ResetPasswordScreen({super.key});

  @override
  State<ResetPasswordScreen> createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends State<ResetPasswordScreen> {
  final _emailController = TextEditingController();
  final _codeController = TextEditingController();
  bool _isLoading = false;
  bool _codeSent = false;
  String? _error;
  String? _success;

  @override
  void dispose() {
    _emailController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _sendCode() async {
    if (_emailController.text.trim().isEmpty) {
      setState(() => _error = 'Please enter your email');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final res = await ApiService.post('/auth/forgot-password', {
        'email': _emailController.text.trim(),
      });

      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _codeSent = res['success'] == true;
        _success = res['success'] == true
            ? 'Code sent! Check your email inbox.'
            : null;
        _error = res['success'] == true
            ? null
            : res['message'] ?? 'Unable to send reset code.';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = 'Connection error. Try again.';
      });
    }
  }

  Future<void> _verifyCode() async {
    if (_codeController.text.trim().isEmpty) {
      setState(() => _error = 'Please enter the code');
      return;
    }
    if (_codeController.text.trim().length != 6) {
      setState(() => _error = 'Code must be 6 digits');
      return;
    }

    // Navigate to Create New Password screen
    // passing email and code
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CreateNewPasswordScreen(
          email: _emailController.text.trim(),
          code: _codeController.text.trim(),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: AppBar(
        title: const Text('Reset Password'),
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
            const SizedBox(height: 20),

            // Email field
            const Text(
              'Email',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              enabled: !_codeSent,
              decoration: InputDecoration(
                hintText: 'Enter your email',
                prefixIcon: const Icon(
                  Icons.email_outlined,
                  color: AppTheme.textGrey,
                  size: 20,
                ),
                filled: true,
                fillColor: _codeSent ? AppTheme.bgGrey : AppTheme.bgGrey,
              ),
            ),

            const SizedBox(height: 16),

            // Get Code button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isLoading || _codeSent ? null : _sendCode,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _codeSent
                      ? AppTheme.textGrey
                      : AppTheme.primaryGreen,
                ),
                child: _isLoading
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          color: AppTheme.white,
                          strokeWidth: 2.5,
                        ),
                      )
                    : Text(_codeSent ? 'Code Sent ✓' : 'Get Code'),
              ),
            ),

            // Success message
            if (_success != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.lightGreen,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.check_circle_outline,
                      color: AppTheme.primaryGreen,
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _success!,
                        style: const TextStyle(
                          color: AppTheme.darkGreen,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Code field — shows after email sent
            if (_codeSent) ...[
              const SizedBox(height: 24),
              const Text(
                'Code',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.textDark,
                ),
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _codeController,
                keyboardType: TextInputType.number,
                maxLength: 6,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 8,
                ),
                decoration: const InputDecoration(
                  hintText: '000000',
                  counterText: '',
                  prefixIcon: Icon(
                    Icons.lock_outline,
                    color: AppTheme.textGrey,
                    size: 20,
                  ),
                ),
              ),
              const SizedBox(height: 8),

              // Resend code option
              Center(
                child: TextButton(
                  onPressed: () {
                    setState(() {
                      _codeSent = false;
                      _success = null;
                      _codeController.clear();
                    });
                  },
                  child: const Text(
                    'Resend Code',
                    style: TextStyle(
                      color: AppTheme.primaryGreen,
                      fontSize: 12,
                    ),
                  ),
                ),
              ),
            ],

            // Error message
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

            const SizedBox(height: 28),

            // Confirm button
            if (_codeSent)
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _verifyCode,
                  child: const Text('Confirm'),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
