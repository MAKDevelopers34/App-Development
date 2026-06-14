import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../utils/admin_navigation.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  static const _downloadChannel = MethodChannel(
    'electric_bus_tracker/downloads',
  );

  String? _downloadingType;

  Future<void> _downloadReport(String type) async {
    if (_downloadingType != null) return;

    setState(() => _downloadingType = type);
    try {
      final token = await ApiService.getToken();
      final now = DateTime.now().millisecondsSinceEpoch;
      final fileName = 'electric_bus_${type}_report_$now.pdf';

      await _downloadChannel.invokeMethod('downloadPdf', {
        'url': '${ApiService.baseUrl}/reports/generate-download/$type',
        'fileName': fileName,
        'token': token,
      });

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$fileName saved to Downloads'),
          backgroundColor: AppTheme.primaryGreen,
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Report download failed: $error'),
          backgroundColor: AppTheme.redStatus,
        ),
      );
    } finally {
      if (mounted) setState(() => _downloadingType = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AdminNavigation.dashboardBackScope(
      context: context,
      child: Scaffold(
        backgroundColor: AppTheme.bgGrey,
        appBar: AppBar(
          title: const Text('Reports'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back_ios, size: 18),
            onPressed: () => AdminNavigation.goDashboard(context),
          ),
        ),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _ReportOption(
              title: 'Daily Report',
              subtitle: 'Today only',
              icon: Icons.today_outlined,
              color: AppTheme.primaryGreen,
              loading: _downloadingType == 'daily',
              disabled: _downloadingType != null,
              onTap: () => _downloadReport('daily'),
            ),
            const SizedBox(height: 12),
            _ReportOption(
              title: 'Weekly Report',
              subtitle: 'Previous 7 days',
              icon: Icons.date_range_outlined,
              color: AppTheme.orangeStatus,
              loading: _downloadingType == 'weekly',
              disabled: _downloadingType != null,
              onTap: () => _downloadReport('weekly'),
            ),
            const SizedBox(height: 12),
            _ReportOption(
              title: 'Monthly Report',
              subtitle: 'Previous 30 days',
              icon: Icons.calendar_month_outlined,
              color: const Color(0xFF6D5DF6),
              loading: _downloadingType == 'monthly',
              disabled: _downloadingType != null,
              onTap: () => _downloadReport('monthly'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReportOption extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final bool loading;
  final bool disabled;
  final VoidCallback onTap;

  const _ReportOption({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.loading,
    required this.disabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: disabled && !loading ? 0.55 : 1,
      child: Material(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          onTap: disabled ? null : onTap,
          borderRadius: BorderRadius.circular(10),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.cardShadow,
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: color, size: 24),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          color: AppTheme.textDark,
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        subtitle,
                        style: const TextStyle(
                          color: AppTheme.textGrey,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
                loading
                    ? SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          color: color,
                          strokeWidth: 2.4,
                        ),
                      )
                    : Icon(Icons.download_outlined, color: color, size: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
