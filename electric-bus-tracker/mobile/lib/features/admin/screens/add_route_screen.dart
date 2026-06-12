import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/real_bus_map.dart';

class AddRouteScreen extends StatefulWidget {
  const AddRouteScreen({super.key});

  @override
  State<AddRouteScreen> createState() => _AddRouteScreenState();
}

class _AddRouteScreenState extends State<AddRouteScreen> {
  final _formKey = GlobalKey<FormState>();
  final _routeCodeController = TextEditingController();
  final _routeNameController = TextEditingController();
  final _startNameController = TextEditingController();
  final _endNameController = TextEditingController();

  LatLng? _startPoint;
  LatLng? _endPoint;
  bool _pickingStart = true;
  bool _isSaving = false;

  @override
  void dispose() {
    _routeCodeController.dispose();
    _routeNameController.dispose();
    _startNameController.dispose();
    _endNameController.dispose();
    super.dispose();
  }

  double get _distanceKm {
    if (_startPoint == null || _endPoint == null) return 0;
    const distance = Distance();
    return distance.as(LengthUnit.Kilometer, _startPoint!, _endPoint!);
  }

  int get _estimatedMinutes {
    if (_distanceKm <= 0) return 0;
    return ((_distanceKm / 35) * 60).round().clamp(5, 240).toInt();
  }

  Map<String, dynamic>? get _draftRoute {
    if (_startPoint == null && _endPoint == null) return null;

    return {
      'routeId': 'draft',
      'routeName': _routeNameController.text.trim().isEmpty
          ? 'New Route'
          : _routeNameController.text.trim(),
      'startPoint': _startPoint == null
          ? null
          : {
              'name': _startNameController.text.trim().isEmpty
                  ? 'Start'
                  : _startNameController.text.trim(),
              'latitude': _startPoint!.latitude,
              'longitude': _startPoint!.longitude,
            },
      'endPoint': _endPoint == null
          ? null
          : {
              'name': _endNameController.text.trim().isEmpty
                  ? 'End'
                  : _endNameController.text.trim(),
              'latitude': _endPoint!.latitude,
              'longitude': _endPoint!.longitude,
            },
      'stops': [],
    };
  }

  void _setMapPoint(LatLng point) {
    setState(() {
      if (_pickingStart) {
        _startPoint = point;
        _pickingStart = false;
      } else {
        _endPoint = point;
      }
    });
  }

  Future<void> _saveRoute() async {
    if (!_formKey.currentState!.validate()) return;
    if (_startPoint == null || _endPoint == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Tap start and end points on the map'),
          backgroundColor: AppTheme.redStatus,
        ),
      );
      return;
    }

    setState(() => _isSaving = true);
    try {
      final response = await ApiService.post('/routes', {
        'routeCode': _routeCodeController.text.trim().toUpperCase(),
        'routeName': _routeNameController.text.trim(),
        'startPoint': {
          'name': _startNameController.text.trim(),
          'latitude': _startPoint!.latitude,
          'longitude': _startPoint!.longitude,
        },
        'endPoint': {
          'name': _endNameController.text.trim(),
          'latitude': _endPoint!.latitude,
          'longitude': _endPoint!.longitude,
        },
        'totalDistance': double.parse(_distanceKm.toStringAsFixed(2)),
        'estimatedTotalTime': _estimatedMinutes,
      });

      if (!mounted) return;
      setState(() => _isSaving = false);

      if (response['success'] == true) {
        Navigator.pop(context, true);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Route created successfully'),
            backgroundColor: AppTheme.primaryGreen,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(response['message'] ?? 'Failed to create route'),
            backgroundColor: AppTheme.redStatus,
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _isSaving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to create route: $e'),
          backgroundColor: AppTheme.redStatus,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final draftRoute = _draftRoute;

    return Scaffold(
      backgroundColor: AppTheme.bgGrey,
      appBar: AppBar(
        title: const Text('Add Route'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Column(
        children: [
          SizedBox(
            height: MediaQuery.of(context).size.height * 0.42,
            child: RealBusMap(
              routes: draftRoute == null ? const [] : [draftRoute],
              selectedRouteId: 'draft',
              showEndpointMarkers: true,
              onMapTap: _setMapPoint,
              forcedZoom: 11,
            ),
          ),
          _buildPickToolbar(),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  children: [
                    _field(
                      label: 'Route Code',
                      controller: _routeCodeController,
                      hint: 'MNW-NML',
                      textCapitalization: TextCapitalization.characters,
                    ),
                    const SizedBox(height: 12),
                    _field(
                      label: 'Route Name',
                      controller: _routeNameController,
                      hint: 'MIANWALI - NAMAL',
                    ),
                    const SizedBox(height: 12),
                    _field(
                      label: 'Start Point Name',
                      controller: _startNameController,
                      hint: 'Mianwali',
                    ),
                    const SizedBox(height: 12),
                    _field(
                      label: 'End Point Name',
                      controller: _endNameController,
                      hint: 'Namal University',
                    ),
                    const SizedBox(height: 16),
                    _buildRouteSummary(),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: _isSaving ? null : _saveRoute,
                        icon: _isSaving
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  color: AppTheme.white,
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.save_alt, size: 18),
                        label: const Text('Save Route'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPickToolbar() {
    return Container(
      color: AppTheme.white,
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
      child: Row(
        children: [
          _pickButton(
            label: 'Start',
            icon: Icons.trip_origin,
            active: _pickingStart,
            onTap: () => setState(() => _pickingStart = true),
          ),
          const SizedBox(width: 10),
          _pickButton(
            label: 'End',
            icon: Icons.flag,
            active: !_pickingStart,
            onTap: () => setState(() => _pickingStart = false),
          ),
          const Spacer(),
          Text(
            _pickingStart ? 'Tap map for start' : 'Tap map for end',
            style: const TextStyle(
              color: AppTheme.textGrey,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _pickButton({
    required String label,
    required IconData icon,
    required bool active,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: active ? AppTheme.primaryGreen : AppTheme.lightGreen,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 16,
              color: active ? AppTheme.white : AppTheme.primaryGreen,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color: active ? AppTheme.white : AppTheme.primaryGreen,
                fontWeight: FontWeight.w700,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _field({
    required String label,
    required TextEditingController controller,
    required String hint,
    TextCapitalization textCapitalization = TextCapitalization.words,
  }) {
    return TextFormField(
      controller: controller,
      textCapitalization: textCapitalization,
      decoration: InputDecoration(labelText: label, hintText: hint),
      validator: (value) {
        if (value == null || value.trim().isEmpty) return '$label is required';
        return null;
      },
      onChanged: (_) => setState(() {}),
    );
  }

  Widget _buildRouteSummary() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE8E8E8)),
      ),
      child: Column(
        children: [
          _summaryRow(
            Icons.place_outlined,
            'Start',
            _startPoint == null
                ? 'Not selected'
                : '${_startPoint!.latitude.toStringAsFixed(5)}, '
                      '${_startPoint!.longitude.toStringAsFixed(5)}',
          ),
          const SizedBox(height: 10),
          _summaryRow(
            Icons.flag_outlined,
            'End',
            _endPoint == null
                ? 'Not selected'
                : '${_endPoint!.latitude.toStringAsFixed(5)}, '
                      '${_endPoint!.longitude.toStringAsFixed(5)}',
          ),
          const SizedBox(height: 10),
          _summaryRow(
            Icons.social_distance,
            'Distance',
            '${_distanceKm.toStringAsFixed(2)} km',
          ),
          const SizedBox(height: 10),
          _summaryRow(Icons.timer, 'Time', '$_estimatedMinutes mins'),
        ],
      ),
    );
  }

  Widget _summaryRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, color: AppTheme.primaryGreen, size: 18),
        const SizedBox(width: 10),
        Text(
          '$label:',
          style: const TextStyle(color: AppTheme.textGrey, fontSize: 12),
        ),
        const Spacer(),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: const TextStyle(
              color: AppTheme.textDark,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    );
  }
}
