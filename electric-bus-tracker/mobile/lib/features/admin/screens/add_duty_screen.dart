import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/services/api_service.dart';

class AddDutyScreen extends StatefulWidget {
  const AddDutyScreen({super.key});

  @override
  State<AddDutyScreen> createState() => _AddDutyScreenState();
}

class _AddDutyScreenState extends State<AddDutyScreen> {
  final _formKey = GlobalKey<FormState>();
  String? _selectedDriverId;
  String? _selectedBusId;
  String? _selectedRouteId;
  DateTime? _selectedDate;
  String? _startTime;
  String? _endTime;
  bool _isLoading = false;
  List<dynamic> _drivers = [];
  List<dynamic> _buses = [];
  List<dynamic> _routes = [];

  @override
  void initState() {
    super.initState();
    _loadOptions();
  }

  Future<void> _loadOptions() async {
    try {
      final dRes = await ApiService.get('/admin/drivers');
      final bRes = await ApiService.get('/admin/buses');
      final rRes = await ApiService.get('/routes');
      setState(() {
        _drivers = dRes['drivers'] ?? [];
        _buses = bRes['buses'] ?? [];
        _routes = rRes['routes'] ?? [];
      });
    } catch (e) {
      debugPrint('Load options error: $e');
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedDate == null || _startTime == null || _endTime == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please fill all fields'),
          backgroundColor: AppTheme.redStatus,
        ),
      );
      return;
    }

    setState(() => _isLoading = true);
    try {
      final res = await ApiService.post('/admin/duties', {
        'driverId': _selectedDriverId,
        'busId': _selectedBusId,
        'routeId': _selectedRouteId,
        'scheduledDate': DateFormat('yyyy-MM-dd').format(_selectedDate!),
        'scheduledStartTime': _startTime,
        'scheduledEndTime': _endTime,
      });

      if (res['success'] == true) {
        if (!mounted) return;
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Duty assigned successfully!'),
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

  Future<void> _pickDate() async {
    final date = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      builder: (context, child) => Theme(
        data: ThemeData.light().copyWith(
          colorScheme: const ColorScheme.light(primary: AppTheme.primaryGreen),
        ),
        child: child!,
      ),
    );
    if (date != null) setState(() => _selectedDate = date);
  }

  Future<void> _pickTime(bool isStart) async {
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.now(),
      builder: (context, child) => Theme(
        data: ThemeData.light().copyWith(
          colorScheme: const ColorScheme.light(primary: AppTheme.primaryGreen),
        ),
        child: child!,
      ),
    );
    if (time != null) {
      final formatted =
          '${time.hour.toString().padLeft(2, '0')}:'
          '${time.minute.toString().padLeft(2, '0')}';
      setState(() {
        if (isStart) {
          _startTime = formatted;
        } else {
          _endTime = formatted;
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      appBar: AppBar(
        title: const Text('Add New Duty'),
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
              // Driver dropdown
              _label('Driver Name *'),
              DropdownButtonFormField<String>(
                initialValue: _selectedDriverId,
                hint: const Text('Select driver'),
                decoration: const InputDecoration(),
                items: _drivers.map<DropdownMenuItem<String>>((d) {
                  return DropdownMenuItem(
                    value: d['_id'].toString(),
                    child: Text(
                      d['profileInfo']?['fullName'] ?? d['username'],
                      style: const TextStyle(fontSize: 14),
                    ),
                  );
                }).toList(),
                onChanged: (v) => setState(() => _selectedDriverId = v),
                validator: (v) => v == null ? 'Select a driver' : null,
              ),
              const SizedBox(height: 16),

              // Route dropdown
              _label('Route Name *'),
              DropdownButtonFormField<String>(
                initialValue: _selectedRouteId,
                hint: const Text('Select route'),
                decoration: const InputDecoration(),
                items: _routes.map<DropdownMenuItem<String>>((r) {
                  return DropdownMenuItem(
                    value: r['routeId'].toString(),
                    child: Text(
                      r['routeName'],
                      style: const TextStyle(fontSize: 14),
                    ),
                  );
                }).toList(),
                onChanged: (v) => setState(() => _selectedRouteId = v),
                validator: (v) => v == null ? 'Select a route' : null,
              ),
              const SizedBox(height: 16),

              // Bus dropdown
              _label('Bus *'),
              DropdownButtonFormField<String>(
                initialValue: _selectedBusId,
                hint: const Text('Select bus'),
                decoration: const InputDecoration(),
                items: _buses.map<DropdownMenuItem<String>>((b) {
                  return DropdownMenuItem(
                    value: b['_id'].toString(),
                    child: Text(
                      b['busNumber'],
                      style: const TextStyle(fontSize: 14),
                    ),
                  );
                }).toList(),
                onChanged: (v) => setState(() => _selectedBusId = v),
                validator: (v) => v == null ? 'Select a bus' : null,
              ),
              const SizedBox(height: 16),

              // Date picker
              _label('Date *'),
              GestureDetector(
                onTap: _pickDate,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 14,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.bgGrey,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.calendar_today_outlined,
                        color: AppTheme.textGrey,
                        size: 18,
                      ),
                      const SizedBox(width: 10),
                      Text(
                        _selectedDate == null
                            ? 'Select date'
                            : DateFormat('dd MMM yyyy').format(_selectedDate!),
                        style: TextStyle(
                          color: _selectedDate == null
                              ? AppTheme.textGrey
                              : AppTheme.textDark,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Time pickers
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _label('Start Time *'),
                        GestureDetector(
                          onTap: () => _pickTime(true),
                          child: _timeField(_startTime),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _label('End Time *'),
                        GestureDetector(
                          onTap: () => _pickTime(false),
                          child: _timeField(_endTime),
                        ),
                      ],
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 32),

              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _submit,
                  child: _isLoading
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            color: AppTheme.white,
                            strokeWidth: 2.5,
                          ),
                        )
                      : const Text('+ Add'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _label(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        text,
        style: const TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w500,
          color: AppTheme.textDark,
        ),
      ),
    );
  }

  Widget _timeField(String? time) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
      decoration: BoxDecoration(
        color: AppTheme.bgGrey,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Icon(Icons.access_time, color: AppTheme.textGrey, size: 16),
          const SizedBox(width: 6),
          Text(
            time ?? 'Select',
            style: TextStyle(
              color: time == null ? AppTheme.textGrey : AppTheme.textDark,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}
