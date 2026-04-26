import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';

class EditDutyScreen extends StatefulWidget {
  final Map<String, dynamic> duty;
  const EditDutyScreen({super.key, required this.duty});

  @override
  State<EditDutyScreen> createState() => _EditDutyScreenState();
}

class _EditDutyScreenState extends State<EditDutyScreen> {
  late TextEditingController _startTimeController;
  late TextEditingController _endTimeController;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _startTimeController = TextEditingController(
      text: widget.duty['scheduledStartTime'] ?? '',
    );
    _endTimeController = TextEditingController(
      text: widget.duty['scheduledEndTime'] ?? '',
    );
  }

  Future<void> _save() async {
    setState(() => _isLoading = true);
    try {
      final res =
          await ApiService.put('/admin/duties/${widget.duty['dutyId']}', {
            'scheduledStartTime': _startTimeController.text,
            'scheduledEndTime': _endTimeController.text,
          });

      if (res['success'] == true) {
        if (!mounted) return;
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Duty updated successfully!'),
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
        title: const Text('Edit Duty'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Show current info
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.lightGreen,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Route: ${widget.duty['route']}',
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      color: AppTheme.darkGreen,
                    ),
                  ),
                  Text(
                    'Driver: ${widget.duty['driver']?['username'] ?? 'N/A'}',
                    style: const TextStyle(
                      color: AppTheme.darkGreen,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            const Text(
              'Online Driver *',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _startTimeController,
              decoration: const InputDecoration(
                hintText: 'Start time (HH:MM)',
                prefixIcon: Icon(
                  Icons.access_time,
                  color: AppTheme.textGrey,
                  size: 18,
                ),
              ),
            ),
            const SizedBox(height: 16),

            const Text(
              'Next Time *',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _endTimeController,
              decoration: const InputDecoration(
                hintText: 'End time (HH:MM)',
                prefixIcon: Icon(
                  Icons.timer_off_outlined,
                  color: AppTheme.textGrey,
                  size: 18,
                ),
              ),
            ),

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
}
