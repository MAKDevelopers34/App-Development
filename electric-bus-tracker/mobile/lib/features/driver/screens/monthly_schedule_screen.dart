import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';

class MonthlyScheduleScreen extends StatefulWidget {
  const MonthlyScheduleScreen({super.key});

  @override
  State<MonthlyScheduleScreen> createState() => _MonthlyScheduleScreenState();
}

class _MonthlyScheduleScreenState extends State<MonthlyScheduleScreen> {
  List<dynamic> _duties = [];
  Map<String, dynamic>? _summary;
  bool _isLoading = true;
  DateTime _selectedMonth = DateTime.now();

  @override
  void initState() {
    super.initState();
    _loadSchedule();
  }

  Future<void> _loadSchedule() async {
    setState(() => _isLoading = true);
    try {
      final response = await ApiService.get(
        '/duty/monthly?month=${_selectedMonth.month}'
        '&year=${_selectedMonth.year}',
      );
      setState(() {
        _duties = response['duties'] ?? [];
        _summary = response['summary'];
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      appBar: AppBar(
        title: const Text('Monthly Schedule'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          // Month navigation
          IconButton(
            icon: const Icon(Icons.chevron_left),
            onPressed: () {
              setState(() {
                _selectedMonth = DateTime(
                  _selectedMonth.year,
                  _selectedMonth.month - 1,
                );
              });
              _loadSchedule();
            },
          ),
          TextButton(
            onPressed: null,
            child: Text(
              DateFormat('MMM yyyy').format(_selectedMonth),
              style: const TextStyle(
                color: AppTheme.primaryGreen,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.chevron_right),
            onPressed: () {
              setState(() {
                _selectedMonth = DateTime(
                  _selectedMonth.year,
                  _selectedMonth.month + 1,
                );
              });
              _loadSchedule();
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.primaryGreen),
            )
          : Column(
              children: [
                // Summary bar
                if (_summary != null) _buildSummaryBar(),

                // Duties list
                Expanded(
                  child: _duties.isEmpty
                      ? const Center(
                          child: Text(
                            'No duties this month',
                            style: TextStyle(color: AppTheme.textGrey),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _duties.length,
                          itemBuilder: (context, index) =>
                              _buildDutyItem(_duties[index]),
                        ),
                ),
              ],
            ),
    );
  }

  Widget _buildSummaryBar() {
    return Container(
      color: AppTheme.white,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _summaryChip(
            'Total',
            _summary!['total'].toString(),
            AppTheme.textDark,
          ),
          _summaryChip(
            'Completed',
            _summary!['completed'].toString(),
            AppTheme.primaryGreen,
          ),
          _summaryChip(
            'Skipped',
            _summary!['skipped'].toString(),
            AppTheme.redStatus,
          ),
          _summaryChip(
            'Assigned',
            _summary!['assigned'].toString(),
            AppTheme.orangeStatus,
          ),
        ],
      ),
    );
  }

  Widget _summaryChip(String label, String value, Color color) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
        Text(
          label,
          style: const TextStyle(fontSize: 11, color: AppTheme.textGrey),
        ),
      ],
    );
  }

  Widget _buildDutyItem(Map<String, dynamic> duty) {
    final date = DateTime.parse(duty['scheduledDate']);
    final status = duty['status'] as String;
    final bus = duty['bus'];

    Color statusColor;
    switch (status) {
      case 'completed':
        statusColor = AppTheme.primaryGreen;
        break;
      case 'skipped':
        statusColor = AppTheme.redStatus;
        break;
      case 'started':
        statusColor = AppTheme.orangeStatus;
        break;
      default:
        statusColor = AppTheme.textGrey;
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
          // Date box
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              color: AppTheme.lightGreen,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  DateFormat('dd').format(date),
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.primaryGreen,
                  ),
                ),
                Text(
                  DateFormat('MMM').format(date),
                  style: const TextStyle(
                    fontSize: 10,
                    color: AppTheme.primaryGreen,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),

          // Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  duty['route'] ?? '',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textDark,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  'Bus: ${bus?['busNumber'] ?? 'N/A'}  •  '
                  '${duty['scheduledStartTime']} - '
                  '${duty['scheduledEndTime']}',
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppTheme.textGrey,
                  ),
                ),
              ],
            ),
          ),

          // Status badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              status.toUpperCase(),
              style: TextStyle(
                color: statusColor,
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
