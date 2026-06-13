import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../widgets/admin_bottom_nav.dart';

class AddDutyScreen extends StatefulWidget {
  const AddDutyScreen({super.key});

  @override
  State<AddDutyScreen> createState() => _AddDutyScreenState();
}

class _AddDutyScreenState extends State<AddDutyScreen> {
  final _formKey = GlobalKey<FormState>();
  String? _selectedRouteId;
  String? _selectedDriverId;
  DateTime? _selectedDate;
  String? _startTime;
  bool _isLoading = false;
  bool _isOptionsLoading = true;
  List<dynamic> _routes = [];
  List<dynamic> _drivers = [];
  List<dynamic> _buses = [];

  @override
  void initState() {
    super.initState();
    _loadOptions();
  }

  Future<void> _loadOptions() async {
    try {
      final results = await Future.wait([
        ApiService.get('/routes'),
        ApiService.get('/admin/drivers'),
        ApiService.get('/admin/buses'),
      ]);
      if (!mounted) return;
      setState(() {
        _routes = results[0]['routes'] ?? [];
        _drivers = results[1]['drivers'] ?? [];
        _buses = results[2]['buses'] ?? [];
        _isOptionsLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isOptionsLoading = false);
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedDate == null || _startTime == null) {
      _showSnack('Please fill all required fields', isError: true);
      return;
    }

    final bus = _bestBus();
    if (bus == null) {
      _showSnack('No active bus available for this duty', isError: true);
      return;
    }

    setState(() => _isLoading = true);
    try {
      final res = await ApiService.post('/admin/duties', {
        'routeId': _selectedRouteId,
        'driverId': _selectedDriverId,
        'busId': _idOf(bus),
        'scheduledDate': DateFormat('yyyy-MM-dd').format(_selectedDate!),
        'scheduledStartTime': _startTime,
        'scheduledEndTime': _calculatedEndTime(),
      });

      if (!mounted) return;
      if (res['success'] == true) {
        Navigator.pop(context, true);
      } else {
        setState(() => _isLoading = false);
        _showSnack(res['message'] ?? 'Failed to assign duty', isError: true);
      }
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      _showSnack('Connection error. Try again.', isError: true);
    }
  }

  Future<void> _pickDate() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _selectedDate ?? DateTime.now(),
      firstDate: DateTime(2024),
      lastDate: DateTime.now().add(const Duration(days: 730)),
      builder: (context, child) => Theme(
        data: ThemeData.light().copyWith(
          colorScheme: const ColorScheme.light(primary: AppTheme.primaryGreen),
        ),
        child: child!,
      ),
    );
    if (date != null) setState(() => _selectedDate = date);
  }

  Future<void> _pickStartTime() async {
    final initial = _timeOfDay(_startTime) ?? TimeOfDay.now();
    final time = await showTimePicker(
      context: context,
      initialTime: initial,
      builder: (context, child) => Theme(
        data: ThemeData.light().copyWith(
          colorScheme: const ColorScheme.light(primary: AppTheme.primaryGreen),
        ),
        child: child!,
      ),
    );
    if (time != null) {
      setState(() {
        _startTime =
            '${time.hour.toString().padLeft(2, '0')}:'
            '${time.minute.toString().padLeft(2, '0')}';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      body: SafeArea(
        child: _isOptionsLoading
            ? const Center(
                child: CircularProgressIndicator(color: AppTheme.primaryGreen),
              )
            : SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(24, 26, 24, 28),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 280),
                    child: _buildCard(),
                  ),
                ),
              ),
      ),
      bottomNavigationBar: const AdminBottomNav(selectedIndex: 0),
    );
  }

  Widget _buildCard() {
    return Container(
      padding: const EdgeInsets.fromLTRB(22, 24, 22, 26),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(8),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.18),
            blurRadius: 24,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Center(
              child: Text(
                'Add New Duty',
                style: TextStyle(
                  color: AppTheme.textDark,
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            const SizedBox(height: 26),
            _label('Select Route *'),
            _routeDropdown(),
            const SizedBox(height: 18),
            _label('Select Driver *'),
            _driverDropdown(),
            const SizedBox(height: 18),
            _label('Date *'),
            _pickerField(
              value: _selectedDate == null
                  ? ''
                  : DateFormat('yyyy-MM-dd').format(_selectedDate!),
              onTap: _pickDate,
            ),
            const SizedBox(height: 18),
            _label('Start Time *'),
            _pickerField(value: _startTime ?? '', onTap: _pickStartTime),
            const SizedBox(height: 28),
            Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton.icon(
                onPressed: _isLoading ? null : _submit,
                icon: _isLoading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          color: AppTheme.white,
                          strokeWidth: 2,
                        ),
                      )
                    : const Icon(Icons.add, size: 18),
                label: const Text('Add'),
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(96, 48),
                  padding: const EdgeInsets.symmetric(horizontal: 18),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  elevation: 10,
                  shadowColor: AppTheme.primaryGreen.withValues(alpha: 0.32),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _routeDropdown() {
    return DropdownButtonFormField<String>(
      initialValue: _selectedRouteId,
      isExpanded: true,
      decoration: _inputDecoration(),
      items: _routes.map<DropdownMenuItem<String>>((raw) {
        final route = Map<String, dynamic>.from(raw as Map);
        return DropdownMenuItem(
          value: _idOf(route),
          child: Text(
            route['routeName']?.toString() ?? 'Route',
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 12),
          ),
        );
      }).toList(),
      onChanged: (value) => setState(() => _selectedRouteId = value),
      validator: (value) => value == null ? 'Select route' : null,
    );
  }

  Widget _driverDropdown() {
    return DropdownButtonFormField<String>(
      initialValue: _selectedDriverId,
      isExpanded: true,
      decoration: _inputDecoration(),
      items: _drivers.map<DropdownMenuItem<String>>((raw) {
        final driver = Map<String, dynamic>.from(raw as Map);
        final profile = driver['profileInfo'] as Map?;
        return DropdownMenuItem(
          value: _idOf(driver),
          child: Text(
            profile?['fullName']?.toString() ??
                driver['username']?.toString() ??
                'Driver',
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 12),
          ),
        );
      }).toList(),
      onChanged: (value) => setState(() => _selectedDriverId = value),
      validator: (value) => value == null ? 'Select driver' : null,
    );
  }

  Widget _pickerField({required String value, required VoidCallback onTap}) {
    return TextFormField(
      readOnly: true,
      controller: TextEditingController(text: value),
      onTap: onTap,
      style: const TextStyle(fontSize: 12),
      decoration: _inputDecoration(),
      validator: (text) => text == null || text.isEmpty ? 'Required' : null,
    );
  }

  Widget _label(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        text,
        style: const TextStyle(
          color: AppTheme.textDark,
          fontSize: 11,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  InputDecoration _inputDecoration() {
    return InputDecoration(
      filled: true,
      fillColor: AppTheme.white,
      isDense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(7),
        borderSide: const BorderSide(color: Color(0xFFD8DEE6)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(7),
        borderSide: const BorderSide(color: Color(0xFFD8DEE6)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(7),
        borderSide: const BorderSide(color: AppTheme.primaryGreen, width: 1.2),
      ),
    );
  }

  Map<String, dynamic>? _bestBus() {
    final active = _buses.whereType<Map>().where((bus) {
      final status = bus['status']?.toString().toLowerCase() ?? 'active';
      return status == 'active';
    }).toList();
    final source = active.isNotEmpty ? active : _buses.whereType<Map>().toList();
    if (source.isEmpty) return null;
    return Map<String, dynamic>.from(source.first);
  }

  String _calculatedEndTime() {
    final start = _timeOfDay(_startTime);
    if (start == null) return _startTime ?? '00:00';
    final route = _selectedRoute();
    final minutes = _intValue(route?['estimatedTotalTime']) ??
        _intValue(route?['estimatedDuration']) ??
        120;
    final date = DateTime(2026, 1, 1, start.hour, start.minute)
        .add(Duration(minutes: minutes <= 0 ? 120 : minutes));
    return '${date.hour.toString().padLeft(2, '0')}:'
        '${date.minute.toString().padLeft(2, '0')}';
  }

  Map<String, dynamic>? _selectedRoute() {
    for (final raw in _routes) {
      final route = Map<String, dynamic>.from(raw as Map);
      if (_idOf(route) == _selectedRouteId) return route;
    }
    return null;
  }

  TimeOfDay? _timeOfDay(String? value) {
    final parts = (value ?? '').split(':');
    if (parts.length < 2) return null;
    final hour = int.tryParse(parts[0]);
    final minute = int.tryParse(parts[1]);
    if (hour == null || minute == null) return null;
    return TimeOfDay(hour: hour, minute: minute);
  }

  int? _intValue(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.round();
    return int.tryParse(value?.toString() ?? '');
  }

  String _idOf(Map<dynamic, dynamic> value) {
    return (value['_id'] ?? value['driverId'] ?? value['routeId'] ?? value['busId'])
        .toString();
  }

  void _showSnack(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? AppTheme.redStatus : AppTheme.primaryGreen,
      ),
    );
  }
}
