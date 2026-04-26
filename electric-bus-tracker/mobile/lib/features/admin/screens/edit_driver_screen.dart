import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';

class EditDriverScreen extends StatefulWidget {
  final Map<String, dynamic> driver;
  const EditDriverScreen({super.key, required this.driver});

  @override
  State<EditDriverScreen> createState() => _EditDriverScreenState();
}

class _EditDriverScreenState extends State<EditDriverScreen> {
  late TextEditingController _nameController;
  late TextEditingController _phoneController;
  late TextEditingController _addressController;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    final info = widget.driver['profileInfo'] ?? {};
    _nameController = TextEditingController(text: info['fullName'] ?? '');
    _phoneController = TextEditingController(text: info['phone'] ?? '');
    _addressController = TextEditingController(text: info['address'] ?? '');
  }

  Future<void> _save() async {
    setState(() => _isLoading = true);
    try {
      final res = await ApiService.put(
        '/admin/drivers/${widget.driver['_id']}',
        {
          'profileInfo': {
            'fullName': _nameController.text.trim(),
            'phone': _phoneController.text.trim(),
            'address': _addressController.text.trim(),
          },
        },
      );

      if (res['success'] == true) {
        if (!mounted) return;
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Driver updated successfully!'),
            backgroundColor: AppTheme.primaryGreen,
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
        title: const Text('EDIT DRIVER INFORMATION'),
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
            // Driver ID (read-only)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.bgGrey,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.badge_outlined,
                    color: AppTheme.textGrey,
                    size: 16,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'ID: ${widget.driver['userId']}',
                    style: const TextStyle(
                      color: AppTheme.textGrey,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            _field('Name *', _nameController, 'Enter driver full name'),
            const SizedBox(height: 14),
            _field(
              'Phone Number *',
              _phoneController,
              'Enter phone number',
              type: TextInputType.phone,
            ),
            const SizedBox(height: 14),
            _field('Address *', _addressController, 'Enter address'),

            const SizedBox(height: 32),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _save,
                child: _isLoading
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          color: AppTheme.white,
                          strokeWidth: 2.5,
                        ),
                      )
                    : const Text('Save'),
              ),
            ),
          ],
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
        TextField(
          controller: controller,
          keyboardType: type,
          decoration: InputDecoration(hintText: hint),
        ),
      ],
    );
  }
}
