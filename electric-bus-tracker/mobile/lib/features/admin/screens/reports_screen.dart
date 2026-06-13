import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';
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

  List<dynamic> _reports = [];
  bool _isLoading = true;
  bool _isGenerating = false;

  @override
  void initState() {
    super.initState();
    _loadReports();
  }

  Future<void> _loadReports() async {
    try {
      final res = await ApiService.get('/reports');
      setState(() {
        _reports = res['reports'] ?? [];
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _generateReport(String type) async {
    setState(() => _isGenerating = true);
    try {
      final res = await ApiService.post('/reports/generate/$type', {});
      if (res['success'] == true) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${type.toUpperCase()} report generated as PDF'),
            backgroundColor: AppTheme.primaryGreen,
          ),
        );
        _loadReports();
      }
    } catch (e) {
      debugPrint('Generate error: $e');
    }
    if (!mounted) return;
    setState(() => _isGenerating = false);
  }

  Future<void> _downloadReport(Map<String, dynamic> report) async {
    final reportId = report['reportId']?.toString();
    if (reportId == null || reportId.isEmpty) return;

    try {
      final token = await ApiService.getToken();
      final safeId = reportId.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
      await _downloadChannel.invokeMethod('downloadPdf', {
        'url': '${ApiService.baseUrl}/reports/download/$reportId',
        'fileName': '$safeId.pdf',
        'token': token,
      });

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$safeId.pdf downloading to phone Downloads'),
          backgroundColor: AppTheme.primaryGreen,
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not download PDF: $error'),
          backgroundColor: AppTheme.redStatus,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      appBar: AppBar(
        title: const Text('Reports'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => AdminNavigation.goDashboard(context),
        ),
      ),
      body: Column(
        children: [
          // Generate buttons
          Container(
            color: AppTheme.white,
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Generate Report',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textDark,
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    _generateBtn('Daily', Icons.today),
                    const SizedBox(width: 8),
                    _generateBtn('Weekly', Icons.date_range),
                    const SizedBox(width: 8),
                    _generateBtn('Monthly', Icons.calendar_month),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 8),

          // Reports list
          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                      color: AppTheme.primaryGreen,
                    ),
                  )
                : _reports.isEmpty
                ? _buildEmptyState()
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: _reports.length,
                    itemBuilder: (context, i) => _buildReportCard(_reports[i]),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _generateBtn(String type, IconData icon) {
    return Expanded(
      child: ElevatedButton.icon(
        onPressed: _isGenerating
            ? null
            : () => _generateReport(type.toLowerCase()),
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 10),
          textStyle: const TextStyle(fontSize: 12),
        ),
        icon: _isGenerating
            ? const SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                  color: AppTheme.white,
                  strokeWidth: 2,
                ),
              )
            : Icon(icon, size: 16),
        label: Text(type),
      ),
    );
  }

  Widget _buildReportCard(Map<String, dynamic> report) {
    final type = report['type']?.toString() ?? 'daily';
    final generatedAt = DateTime.tryParse(
      report['generatedAt']?.toString() ?? '',
    );
    final data = report['data'] ?? {};

    Color typeColor;
    IconData typeIcon;
    switch (type) {
      case 'daily':
        typeColor = AppTheme.primaryGreen;
        typeIcon = Icons.today;
        break;
      case 'weekly':
        typeColor = AppTheme.orangeStatus;
        typeIcon = Icons.date_range;
        break;
      default:
        typeColor = Colors.purple;
        typeIcon = Icons.calendar_month;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [BoxShadow(color: AppTheme.cardShadow, blurRadius: 4)],
      ),
      child: Row(
        children: [
          // Type icon
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: typeColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(typeIcon, color: typeColor, size: 22),
          ),
          const SizedBox(width: 12),

          // Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: typeColor,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        type.toUpperCase(),
                        style: const TextStyle(
                          color: AppTheme.white,
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (generatedAt != null)
                      Text(
                        DateFormat('dd MMM yyyy').format(generatedAt),
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppTheme.textGrey,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  'Duties: ${data['totalDuties'] ?? 0}  -  '
                  'Completed: ${data['completedDuties'] ?? 0}  -  '
                  'Skipped: ${data['skippedDuties'] ?? 0}',
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppTheme.textGrey,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Drivers: ${data['driversPerformedDuties'] ?? data['activeDrivers'] ?? 0}/${data['totalDrivers'] ?? 0}  -  '
                  'Buses: ${data['busesPerformedDuties'] ?? 0}/${data['totalBuses'] ?? 0}  -  '
                  'Routes: ${data['totalRoutes'] ?? 0}  -  '
                  'Stops: ${data['totalStops'] ?? 0}',
                  style: const TextStyle(
                    fontSize: 10,
                    color: AppTheme.textGrey,
                  ),
                ),
              ],
            ),
          ),

          // Download icon
          IconButton(
            icon: const Icon(
              Icons.download_outlined,
              color: AppTheme.primaryGreen,
              size: 22,
            ),
            onPressed: () => _downloadReport(report),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.assessment_outlined,
            size: 64,
            color: AppTheme.textGrey.withValues(alpha: 0.4),
          ),
          const SizedBox(height: 16),
          const Text(
            'No reports generated yet',
            style: TextStyle(color: AppTheme.textGrey, fontSize: 14),
          ),
          const SizedBox(height: 8),
          const Text(
            'Use the buttons above to generate reports',
            style: TextStyle(color: AppTheme.textGrey, fontSize: 12),
          ),
        ],
      ),
    );
  }
}
