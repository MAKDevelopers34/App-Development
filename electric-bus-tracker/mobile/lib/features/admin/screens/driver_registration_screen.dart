import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';

class DriverRegistrationScreen extends StatefulWidget {
  const DriverRegistrationScreen({super.key});

  @override
  State<DriverRegistrationScreen> createState() =>
      _DriverRegistrationScreenState();
}

class _DriverRegistrationScreenState extends State<DriverRegistrationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _userIdController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _addressController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _obscure = true;

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);

    try {
      final username = _nameController.text.trim().toLowerCase().replaceAll(
        ' ',
        '_',
      );

      final res = await ApiService.post('/admin/drivers', {
        'username': username,
        'userId': _userIdController.text.trim(),
        'password': _passwordController.text,
        'email': _emailController.text.trim(),
        'fullName': _nameController.text.trim(),
        'phone': _phoneController.text.trim(),
      });

      if (res['success'] == true) {
        if (!mounted) return;
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Driver registered successfully!'),
            backgroundColor: AppTheme.primaryGreen,
          ),
        );
      } else {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(res['message'] ?? 'Failed'),
            backgroundColor: AppTheme.redStatus,
          ),
        );
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: AppBar(
        title: const Text('Driver Registration'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _field('Name *', _nameController, 'Enter driver full name'),
              const SizedBox(height: 14),
              _field('Unit *', _userIdController, 'Enter CMS number'),
              const SizedBox(height: 14),
              _field(
                'Email *',
                _emailController,
                'Enter email address',
                type: TextInputType.emailAddress,
              ),
              const SizedBox(height: 14),
              _field(
                'Phone Number *',
                _phoneController,
                'Enter phone number',
                type: TextInputType.phone,
              ),
              const SizedBox(height: 14),
              _field('Address *', _addressController, 'Enter address'),
              const SizedBox(height: 14),

              // Password field
              const Text(
                'Password *',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.textDark,
                ),
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _passwordController,
                obscureText: _obscure,
                decoration: InputDecoration(
                  hintText: 'Enter password',
                  suffixIcon: IconButton(
                    icon: Icon(
                      _obscure
                          ? Icons.visibility_off_outlined
                          : Icons.visibility_outlined,
                      color: AppTheme.textGrey,
                      size: 20,
                    ),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),
                validator: (v) => v!.length < 6 ? 'Min 6 characters' : null,
              ),

              const SizedBox(height: 32),

              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _register,
                  child: _isLoading
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            color: AppTheme.white,
                            strokeWidth: 2.5,
                          ),
                        )
                      : const Text('+ Create'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _field(
    String label,
    TextEditingController controller,
    String hint, {
    TextInputType type = TextInputType.text,
  }) {
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
          keyboardType: type,
          decoration: InputDecoration(hintText: hint),
          validator: (v) => v!.isEmpty ? 'This field is required' : null,
        ),
      ],
    );
  }
}
