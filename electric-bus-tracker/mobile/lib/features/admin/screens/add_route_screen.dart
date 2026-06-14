import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../widgets/admin_bottom_nav.dart';

enum _PointRole { start, destination }

class AddRouteScreen extends StatefulWidget {
  const AddRouteScreen({super.key});

  @override
  State<AddRouteScreen> createState() => _AddRouteScreenState();
}

class _AddRouteScreenState extends State<AddRouteScreen> {
  final _routeNameController = TextEditingController();
  final List<_RoutePlace> _selectedStops = [];

  List<_RoutePlace> _availableStops = [];
  _RoutePlace? _start;
  _RoutePlace? _destination;
  bool _isLoadingStops = true;
  bool _isSaving = false;

  static const List<_RoutePlace> _fallbackStops = [
    _RoutePlace('1', 'STP-001', 'Ban Hafiz', 32.4761000, 71.4489000),
    _RoutePlace('2', 'STP-002', 'Cha Agral', 32.4923000, 71.4620000),
    _RoutePlace('3', 'STP-003', 'Rikhi', 32.5085000, 71.4770000),
    _RoutePlace('4', 'STP-004', 'Namal', 32.5200000, 71.4800000),
    _RoutePlace('5', 'STP-005', 'Musa Khel', 32.5400000, 71.5000000),
    _RoutePlace('6', 'STP-006', 'Sohrab Wala', 32.5600000, 71.5220000),
    _RoutePlace('7', 'STP-007', 'Mianwali', 32.5838000, 71.5436000),
    _RoutePlace('11', 'STP-011', 'Daudkhel', 32.8833000, 71.5667000),
    _RoutePlace('14', 'STP-014', 'Wan Bachran', 32.3500000, 71.7000000),
    _RoutePlace('15', 'STP-015', 'Piplan', 32.2898000, 71.5539000),
    _RoutePlace('16', 'STP-016', 'Chashma', 32.4333000, 71.3500000),
    _RoutePlace('18', 'STP-018', 'Isa Khel', 32.6700000, 71.2750000),
  ];

  @override
  void initState() {
    super.initState();
    _loadStops();
  }

  @override
  void dispose() {
    _routeNameController.dispose();
    super.dispose();
  }

  Future<void> _loadStops() async {
    try {
      final response = await ApiService.get('/routes/stops');
      final stops = (response['stops'] as List? ?? [])
          .whereType<Map>()
          .map((raw) => _RoutePlace.fromJson(Map<String, dynamic>.from(raw)))
          .where((stop) => stop.hasCoordinates)
          .toList();

      if (!mounted) return;
      setState(() {
        _availableStops = stops.isEmpty ? _fallbackStops : stops;
        _isLoadingStops = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _availableStops = _fallbackStops;
        _isLoadingStops = false;
      });
    }
  }

  double get _distanceKm {
    if (_start == null || _destination == null) return 0;
    const distance = Distance();
    return distance.as(
      LengthUnit.Kilometer,
      _start!.position,
      _destination!.position,
    );
  }

  int get _estimatedMinutes {
    if (_distanceKm <= 0) return 0;
    return ((_distanceKm / 35) * 60).round().clamp(5, 240).toInt();
  }

  String get _routeCode {
    final startCode = _codeFromName(_start?.name ?? 'START');
    final destinationCode = _codeFromName(_destination?.name ?? 'END');
    final suffix = DateTime.now().millisecondsSinceEpoch % 10000;
    return '$startCode-$destinationCode-$suffix';
  }

  void _syncRouteName() {
    if (_start == null || _destination == null) {
      _routeNameController.clear();
      return;
    }

    _routeNameController.text =
        '${_start!.name.toUpperCase()} - ${_destination!.name.toUpperCase()}';
  }

  Future<void> _pickPoint(_PointRole role) async {
    final selected = await Navigator.push<_RoutePlace>(
      context,
      MaterialPageRoute(
        builder: (_) => _RoutePointPickerScreen(
          role: role,
          stops: _availableStops,
          current: role == _PointRole.start ? _start : _destination,
          otherPoint: role == _PointRole.start ? _destination : _start,
        ),
      ),
    );

    if (selected == null || !mounted) return;
    setState(() {
      if (role == _PointRole.start) {
        _start = selected;
        if (_destination == selected) _destination = null;
      } else {
        _destination = selected;
        if (_start == selected) _start = null;
      }
      _selectedStops.removeWhere((stop) => stop == selected);
      _syncRouteName();
    });
  }

  Future<void> _pickStops() async {
    if (_start == null || _destination == null) {
      _showSnack('Select start and destination first', isError: true);
      return;
    }

    final stops = await Navigator.push<List<_RoutePlace>>(
      context,
      MaterialPageRoute(
        builder: (_) => _RouteStopsPickerScreen(
          stops: _availableStops,
          selectedStops: _selectedStops,
          start: _start!,
          destination: _destination!,
        ),
      ),
    );

    if (stops == null || !mounted) return;
    setState(() {
      _selectedStops
        ..clear()
        ..addAll(stops);
    });
  }

  Future<void> _saveRoute() async {
    if (_start == null || _destination == null) {
      _showSnack('Select start and destination first', isError: true);
      return;
    }

    _syncRouteName();
    setState(() => _isSaving = true);
    try {
      final response = await ApiService.post('/routes', {
        'routeCode': _routeCode,
        'routeName': _routeNameController.text.trim(),
        'startPoint': _start!.toJson(),
        'endPoint': _destination!.toJson(),
        'totalDistance': double.parse(_distanceKm.toStringAsFixed(2)),
        'estimatedTotalTime': _estimatedMinutes,
        'stops': _selectedStops.map((stop) => stop.toJson()).toList(),
      });

      if (!mounted) return;
      if (response['success'] == true) {
        Navigator.pop(context, true);
      } else {
        setState(() => _isSaving = false);
        _showSnack(
          response['message'] ?? 'Failed to create route',
          isError: true,
        );
      }
    } catch (_) {
      if (!mounted) return;
      setState(() => _isSaving = false);
      _showSnack('Connection error. Try again.', isError: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF7F8FA),
      body: SafeArea(
        child: _isLoadingStops
            ? const Center(
                child: CircularProgressIndicator(color: AppTheme.primaryGreen),
              )
            : SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(18, 22, 18, 26),
                child: _buildCreateCard(),
              ),
      ),
      bottomNavigationBar: const AdminBottomNav(selectedIndex: 2),
    );
  }

  Widget _buildCreateCard() {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 360),
        child: Container(
          padding: const EdgeInsets.fromLTRB(18, 22, 18, 18),
          decoration: BoxDecoration(
            color: AppTheme.white,
            borderRadius: BorderRadius.circular(10),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.16),
                blurRadius: 24,
                offset: const Offset(0, 12),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Creating Route',
                style: TextStyle(
                  color: AppTheme.textDark,
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 22),
              Row(
                children: [
                  Expanded(
                    child: _RoutePointCard(
                      title: 'Start\nPoint',
                      value: _start?.name ?? 'Select',
                      color: AppTheme.primaryGreen,
                      icon: Icons.near_me,
                      selected: _start != null,
                      onTap: () => _pickPoint(_PointRole.start),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _RoutePointCard(
                      title: 'Destination',
                      value: _destination?.name ?? 'Select',
                      color: AppTheme.redStatus,
                      icon: Icons.flag,
                      selected: _destination != null,
                      onTap: () => _pickPoint(_PointRole.destination),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              const Text(
                'Route Name',
                style: TextStyle(
                  color: AppTheme.textGrey,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 6),
              TextField(
                controller: _routeNameController,
                readOnly: true,
                decoration: InputDecoration(
                  hintText: 'Select start and destination',
                  filled: true,
                  fillColor: const Color(0xFFF7F8FA),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 14,
                  ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: const BorderSide(color: Color(0xFFDDE1E6)),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: const BorderSide(color: Color(0xFFDDE1E6)),
                  ),
                ),
                style: const TextStyle(
                  color: AppTheme.textDark,
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Route name is automatically set based on start and destination',
                style: TextStyle(color: AppTheme.textGrey, fontSize: 10),
              ),
              const SizedBox(height: 18),
              _PrimaryActionButton(
                label: 'Add Stops to Route',
                icon: Icons.add,
                onTap: _pickStops,
              ),
              const SizedBox(height: 12),
              _PrimaryActionButton(
                label: 'Save Route',
                icon: Icons.check,
                loading: _isSaving,
                onTap: _isSaving ? null : _saveRoute,
              ),
              const SizedBox(height: 16),
              _RouteNote(
                selectedStops: _selectedStops.length,
                distanceKm: _distanceKm,
                estimatedMinutes: _estimatedMinutes,
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _codeFromName(String name) {
    final letters = name
        .trim()
        .toUpperCase()
        .replaceAll(RegExp(r'[^A-Z0-9 ]'), '')
        .split(RegExp(r'\s+'))
        .where((part) => part.isNotEmpty)
        .map((part) => part.substring(0, 1))
        .join();
    return letters.isEmpty ? 'CUS' : letters.padRight(3, 'X').substring(0, 3);
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

class _RoutePointCard extends StatelessWidget {
  final String title;
  final String value;
  final Color color;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  const _RoutePointCard({
    required this.title,
    required this.value,
    required this.color,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        height: 150,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withValues(alpha: 0.65), width: 1.4),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 28,
                  height: 42,
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(icon, color: AppTheme.white, size: 17),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppTheme.textDark,
                      fontSize: 14,
                      height: 1.08,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ],
            ),
            const Spacer(),
            Text(
              value.toUpperCase(),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: AppTheme.textDark,
                fontSize: 15,
                height: 1.18,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              selected ? 'Click to change' : 'Click to select',
              style: TextStyle(
                color: color,
                fontSize: 10,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PrimaryActionButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool loading;
  final VoidCallback? onTap;

  const _PrimaryActionButton({
    required this.label,
    required this.icon,
    this.loading = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ElevatedButton.icon(
      onPressed: onTap,
      icon: loading
          ? const SizedBox(
              width: 17,
              height: 17,
              child: CircularProgressIndicator(
                color: AppTheme.white,
                strokeWidth: 2,
              ),
            )
          : Icon(icon, size: 19),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        minimumSize: const Size(double.infinity, 46),
        backgroundColor: AppTheme.primaryGreen,
        foregroundColor: AppTheme.white,
        disabledBackgroundColor: AppTheme.primaryGreen.withValues(alpha: 0.6),
        elevation: 10,
        shadowColor: AppTheme.primaryGreen.withValues(alpha: 0.25),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w900),
      ),
    );
  }
}

class _RouteNote extends StatelessWidget {
  final int selectedStops;
  final double distanceKm;
  final int estimatedMinutes;

  const _RouteNote({
    required this.selectedStops,
    required this.distanceKm,
    required this.estimatedMinutes,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.lightGreen,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: AppTheme.primaryGreen.withValues(alpha: 0.18),
        ),
      ),
      child: Text.rich(
        TextSpan(
          children: [
            const TextSpan(
              text: 'Note: ',
              style: TextStyle(fontWeight: FontWeight.w900),
            ),
            const TextSpan(
              text: 'You can save the route now or click Add Stops to Route ',
            ),
            TextSpan(
              text: 'to add intermediate stops. ',
              style: TextStyle(
                color: selectedStops > 0
                    ? AppTheme.primaryGreen
                    : AppTheme.textGrey,
                fontWeight: FontWeight.w800,
              ),
            ),
            TextSpan(
              text:
                  '$selectedStops stops selected, ${distanceKm.toStringAsFixed(1)} km, $estimatedMinutes min.',
            ),
          ],
        ),
        style: const TextStyle(
          color: AppTheme.darkGreen,
          fontSize: 10,
          height: 1.28,
        ),
      ),
    );
  }
}

class _RoutePointPickerScreen extends StatefulWidget {
  final _PointRole role;
  final List<_RoutePlace> stops;
  final _RoutePlace? current;
  final _RoutePlace? otherPoint;

  const _RoutePointPickerScreen({
    required this.role,
    required this.stops,
    required this.current,
    required this.otherPoint,
  });

  @override
  State<_RoutePointPickerScreen> createState() =>
      _RoutePointPickerScreenState();
}

class _RoutePointPickerScreenState extends State<_RoutePointPickerScreen> {
  final _nameController = TextEditingController();
  LatLng? _pendingCustomPoint;

  _PointRole get role => widget.role;

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  void _beginCustomPoint(LatLng point) {
    setState(() {
      _pendingCustomPoint = point;
      _nameController.clear();
    });
  }

  void _cancelCustomPoint() {
    setState(() {
      _pendingCustomPoint = null;
      _nameController.clear();
    });
  }

  void _submitCustomPoint() {
    final point = _pendingCustomPoint;
    final name = _nameController.text.trim();
    if (point == null || name.isEmpty) return;

    FocusManager.instance.primaryFocus?.unfocus();
    Navigator.of(context).pop(_RoutePlace.custom(name, point));
  }

  @override
  Widget build(BuildContext context) {
    final color = role == _PointRole.start
        ? AppTheme.primaryGreen
        : AppTheme.redStatus;
    final title = role == _PointRole.start
        ? 'Select Starting Point'
        : 'Select Destination';

    return Scaffold(
      backgroundColor: AppTheme.white,
      body: SafeArea(
        child: Column(
          children: [
            _PickerHeader(title: title, color: color),
            Expanded(
              child: Stack(
                children: [
                  _RouteEditorMap(
                    stops: widget.stops,
                    start: role == _PointRole.start
                        ? widget.current
                        : widget.otherPoint,
                    destination: role == _PointRole.destination
                        ? widget.current
                        : widget.otherPoint,
                    selectedStops: const [],
                    modeColor: color,
                    role: role,
                    onStopTap: (stop) {
                      if (widget.otherPoint != null &&
                          stop == widget.otherPoint) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              role == _PointRole.start
                                  ? 'Start cannot be the same as destination'
                                  : 'Destination cannot be the same as start',
                            ),
                            backgroundColor: AppTheme.redStatus,
                          ),
                        );
                        return;
                      }
                      Navigator.pop(context, stop);
                    },
                    onMapTap: _beginCustomPoint,
                  ),
                  if (_pendingCustomPoint == null)
                    Positioned(
                      left: 18,
                      right: 18,
                      bottom: 24,
                      child: _MapInstructionCard(
                        text: role == _PointRole.start
                            ? 'Click a stored stop or tap the map to set a new starting point'
                            : 'Click a stored stop or tap the map to set a new destination',
                      ),
                    ),
                  if (_pendingCustomPoint != null)
                    Positioned(
                      left: 18,
                      right: 18,
                      bottom: 20,
                      child: _PointNamePanel(
                        label: role == _PointRole.start
                            ? 'Starting Point'
                            : 'Destination',
                        controller: _nameController,
                        color: color,
                        onCancel: _cancelCustomPoint,
                        onSet: _submitCustomPoint,
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: const AdminBottomNav(selectedIndex: 2),
    );
  }
}

class _RouteStopsPickerScreen extends StatefulWidget {
  final List<_RoutePlace> stops;
  final List<_RoutePlace> selectedStops;
  final _RoutePlace start;
  final _RoutePlace destination;

  const _RouteStopsPickerScreen({
    required this.stops,
    required this.selectedStops,
    required this.start,
    required this.destination,
  });

  @override
  State<_RouteStopsPickerScreen> createState() =>
      _RouteStopsPickerScreenState();
}

class _RouteStopsPickerScreenState extends State<_RouteStopsPickerScreen> {
  final _nameController = TextEditingController();
  late final List<_RoutePlace> _selectedStops;
  LatLng? _pendingCustomPoint;

  @override
  void initState() {
    super.initState();
    _selectedStops = [...widget.selectedStops];
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  double get _distanceKm {
    const distance = Distance();
    return distance.as(
      LengthUnit.Kilometer,
      widget.start.position,
      widget.destination.position,
    );
  }

  int get _estimatedMinutes {
    if (_distanceKm <= 0) return 0;
    return ((_distanceKm / 35) * 60).round().clamp(5, 240).toInt();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.white,
      body: SafeArea(
        child: Column(
          children: [
            const _PickerHeader(
              title: 'Adding stops',
              color: AppTheme.primaryGreen,
            ),
            Expanded(
              child: Stack(
                children: [
                  _RouteEditorMap(
                    stops: widget.stops,
                    start: widget.start,
                    destination: widget.destination,
                    selectedStops: _selectedStops,
                    modeColor: AppTheme.primaryGreen,
                    onStopTap: _toggleStop,
                    onMapTap: _beginCustomStop,
                  ),
                  Positioned(
                    right: 14,
                    top: 16,
                    child: _TotalStopsCard(count: 2 + _selectedStops.length),
                  ),
                  Positioned(
                    left: 12,
                    right: 18,
                    bottom: _pendingCustomPoint == null ? 78 : 154,
                    child: _RouteLegend(
                      distanceKm: _distanceKm,
                      estimatedMinutes: _estimatedMinutes,
                    ),
                  ),
                  Positioned(
                    right: 18,
                    bottom: 22,
                    child: ElevatedButton.icon(
                      onPressed: () => Navigator.pop(context, _selectedStops),
                      icon: const Icon(Icons.save_outlined, size: 17),
                      label: const Text('Save Route'),
                      style: ElevatedButton.styleFrom(
                        minimumSize: const Size(116, 44),
                        backgroundColor: AppTheme.primaryGreen,
                        foregroundColor: AppTheme.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        elevation: 10,
                        shadowColor: AppTheme.primaryGreen.withValues(
                          alpha: 0.32,
                        ),
                      ),
                    ),
                  ),
                  if (_pendingCustomPoint != null)
                    Positioned(
                      left: 12,
                      right: 18,
                      bottom: 74,
                      child: _PointNamePanel(
                        label: 'Stop',
                        controller: _nameController,
                        color: AppTheme.primaryGreen,
                        onCancel: _cancelCustomStop,
                        onSet: _submitCustomStop,
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: const AdminBottomNav(selectedIndex: 2),
    );
  }

  void _toggleStop(_RoutePlace stop) {
    if (stop == widget.start || stop == widget.destination) return;
    setState(() {
      if (_selectedStops.contains(stop)) {
        _selectedStops.remove(stop);
      } else {
        _selectedStops.add(stop);
      }
    });
  }

  void _beginCustomStop(LatLng point) {
    setState(() {
      _pendingCustomPoint = point;
      _nameController.clear();
    });
  }

  void _cancelCustomStop() {
    setState(() {
      _pendingCustomPoint = null;
      _nameController.clear();
    });
  }

  void _submitCustomStop() {
    final point = _pendingCustomPoint;
    final name = _nameController.text.trim();
    if (point == null || name.isEmpty) return;

    FocusManager.instance.primaryFocus?.unfocus();
    setState(() {
      _selectedStops.add(_RoutePlace.custom(name, point));
      _pendingCustomPoint = null;
      _nameController.clear();
    });
  }
}

class _PickerHeader extends StatelessWidget {
  final String title;
  final Color color;

  const _PickerHeader({required this.title, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 66,
      color: AppTheme.white,
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Row(
        children: [
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.arrow_back_ios_new, size: 17),
          ),
          Icon(Icons.location_on_outlined, color: color, size: 22),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              title,
              style: const TextStyle(
                color: AppTheme.textDark,
                fontSize: 16,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RouteEditorMap extends StatelessWidget {
  final List<_RoutePlace> stops;
  final _RoutePlace? start;
  final _RoutePlace? destination;
  final List<_RoutePlace> selectedStops;
  final Color modeColor;
  final _PointRole? role;
  final ValueChanged<_RoutePlace> onStopTap;
  final ValueChanged<LatLng> onMapTap;

  const _RouteEditorMap({
    required this.stops,
    required this.start,
    required this.destination,
    required this.selectedStops,
    required this.modeColor,
    this.role,
    required this.onStopTap,
    required this.onMapTap,
  });

  @override
  Widget build(BuildContext context) {
    final visiblePlaces = _visiblePlaces();
    final center = _MapMath.centerOf(visiblePlaces.map((e) => e.position));
    final zoom = _MapMath.zoomFor(visiblePlaces.map((e) => e.position));

    final routeLine = _routeLinePoints();

    return Stack(
      children: [
        FlutterMap(
          options: MapOptions(
            initialCenter: center,
            initialZoom: zoom,
            minZoom: 8,
            maxZoom: 18,
            onTap: (tapPosition, point) => onMapTap(point),
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.example.mobile',
              maxNativeZoom: 19,
            ),
            if (routeLine.length >= 2)
              PolylineLayer(
                polylines: [
                  Polyline(
                    points: routeLine,
                    color: AppTheme.primaryGreen,
                    strokeWidth: 5.8,
                    borderColor: Colors.black.withValues(alpha: 0.86),
                    borderStrokeWidth: 1.8,
                  ),
                ],
              ),
            MarkerLayer(markers: visiblePlaces.map(_markerFor).toList()),
          ],
        ),
        const _MapAttribution(),
      ],
    );
  }

  Marker _markerFor(_RoutePlace stop) {
    final visual = _visualFor(stop);
    return Marker(
      point: stop.position,
      width: 112,
      height: 124,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => onStopTap(stop),
        child: _MapStopMarker(
          label: stop.name,
          color: visual.color,
          tag: visual.tag,
          selected: visual.selected,
        ),
      ),
    );
  }

  _MarkerVisual _visualFor(_RoutePlace stop) {
    if (stop == start) {
      return const _MarkerVisual(
        color: AppTheme.primaryGreen,
        tag: 'START',
        selected: true,
      );
    }
    if (stop == destination) {
      return const _MarkerVisual(
        color: AppTheme.redStatus,
        tag: 'END',
        selected: true,
      );
    }
    if (selectedStops.contains(stop)) {
      return const _MarkerVisual(
        color: AppTheme.primaryGreen,
        tag: 'STOP',
        selected: true,
      );
    }
    if (role != null) {
      return _MarkerVisual(color: modeColor, tag: null, selected: false);
    }
    return const _MarkerVisual(
      color: Color(0xFF9CA3AF),
      tag: null,
      selected: false,
    );
  }

  List<_RoutePlace> _visiblePlaces() {
    final unique = <String, _RoutePlace>{};
    for (final stop in stops) {
      unique[stop.identity] = stop;
    }
    for (final stop in selectedStops) {
      unique[stop.identity] = stop;
    }
    if (start != null) unique[start!.identity] = start!;
    if (destination != null) unique[destination!.identity] = destination!;
    return unique.values.toList();
  }

  List<LatLng> _routeLinePoints() {
    if (start == null || destination == null) return const [];
    return [
      start!.position,
      ...selectedStops.map((stop) => stop.position),
      destination!.position,
    ];
  }
}

class _MarkerVisual {
  final Color color;
  final String? tag;
  final bool selected;

  const _MarkerVisual({
    required this.color,
    required this.tag,
    required this.selected,
  });
}

class _MapStopMarker extends StatelessWidget {
  final String label;
  final Color color;
  final String? tag;
  final bool selected;

  const _MapStopMarker({
    required this.label,
    required this.color,
    required this.tag,
    required this.selected,
  });

  @override
  Widget build(BuildContext context) {
    final isNeutral = color == const Color(0xFF9CA3AF);
    return SizedBox(
      width: 112,
      height: 124,
      child: Center(
        child: FittedBox(
          fit: BoxFit.scaleDown,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (tag != null)
                Container(
                  margin: const EdgeInsets.only(bottom: 2),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(9),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.12),
                        blurRadius: 6,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Text(
                    tag!,
                    style: const TextStyle(
                      color: AppTheme.white,
                      fontSize: 8,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              Container(
                width: selected ? 42 : 38,
                height: selected ? 42 : 38,
                decoration: BoxDecoration(
                  color: color,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppTheme.white, width: 3),
                  boxShadow: [
                    BoxShadow(
                      color: color.withValues(alpha: isNeutral ? 0.24 : 0.35),
                      blurRadius: 12,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.location_on_outlined,
                  color: AppTheme.white,
                  size: 23,
                ),
              ),
              Container(
                margin: const EdgeInsets.only(top: 4),
                constraints: const BoxConstraints(minWidth: 58, maxWidth: 86),
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 5),
                decoration: BoxDecoration(
                  color: isNeutral ? AppTheme.white : color,
                  borderRadius: BorderRadius.circular(5),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.16),
                      blurRadius: 8,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: isNeutral ? AppTheme.textDark : AppTheme.white,
                    fontSize: 9,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MapInstructionCard extends StatelessWidget {
  final String text;

  const _MapInstructionCard({required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1463FF), width: 1.4),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.12),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Text(
        text,
        textAlign: TextAlign.center,
        style: const TextStyle(
          color: AppTheme.textDark,
          fontSize: 11,
          height: 1.25,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _PointNamePanel extends StatelessWidget {
  final String label;
  final TextEditingController controller;
  final Color color;
  final VoidCallback onCancel;
  final VoidCallback onSet;

  const _PointNamePanel({
    required this.label,
    required this.controller,
    required this.color,
    required this.onCancel,
    required this.onSet,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.42), width: 1.4),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.16),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Set $label Name',
            style: const TextStyle(
              color: AppTheme.textDark,
              fontSize: 13,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: controller,
            autofocus: true,
            textCapitalization: TextCapitalization.words,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => onSet(),
            decoration: InputDecoration(
              hintText: 'Enter $label name',
              isDense: true,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 12,
                vertical: 12,
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: onCancel,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.textGrey,
                    side: const BorderSide(color: Color(0xFFDDE1E6)),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: const Text('Cancel'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton(
                  onPressed: onSet,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: color,
                    foregroundColor: AppTheme.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: const Text('Set'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TotalStopsCard extends StatelessWidget {
  final int count;

  const _TotalStopsCard({required this.count});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 110,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1463FF), width: 1.4),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.13),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$count Total Stops',
            style: const TextStyle(
              color: AppTheme.textDark,
              fontSize: 12,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            '${count - 2} intermediate stops',
            style: const TextStyle(color: AppTheme.textGrey, fontSize: 9),
          ),
        ],
      ),
    );
  }
}

class _RouteLegend extends StatelessWidget {
  final double distanceKm;
  final int estimatedMinutes;

  const _RouteLegend({
    required this.distanceKm,
    required this.estimatedMinutes,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1463FF), width: 1.4),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              _LegendDot(color: AppTheme.primaryGreen, label: 'Start (Fixed)'),
              SizedBox(width: 8),
              _LegendDot(color: AppTheme.redStatus, label: 'End (Fixed)'),
            ],
          ),
          const SizedBox(height: 7),
          Text(
            'Click gray stops to add them to the route - '
            '${distanceKm.toStringAsFixed(1)} km, $estimatedMinutes min',
            style: const TextStyle(color: AppTheme.textGrey, fontSize: 9),
          ),
        ],
      ),
    );
  }
}

class _LegendDot extends StatelessWidget {
  final Color color;
  final String label;

  const _LegendDot({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(
            color: AppTheme.textDark,
            fontSize: 9,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _MapAttribution extends StatelessWidget {
  const _MapAttribution();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.bottomRight,
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
          decoration: BoxDecoration(
            color: AppTheme.white.withValues(alpha: 0.88),
            borderRadius: BorderRadius.circular(4),
          ),
          child: const Text(
            'OSM',
            style: TextStyle(
              color: AppTheme.textGrey,
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ),
    );
  }
}

class _MapMath {
  static const LatLng defaultCenter = LatLng(32.5838, 71.5436);

  static LatLng centerOf(Iterable<LatLng> points) {
    final list = points.toList();
    if (list.isEmpty) return defaultCenter;

    final lat = list.map((point) => point.latitude).reduce((a, b) => a + b);
    final lng = list.map((point) => point.longitude).reduce((a, b) => a + b);
    return LatLng(lat / list.length, lng / list.length);
  }

  static double zoomFor(Iterable<LatLng> points) {
    final list = points.toList();
    if (list.length <= 1) return 12.5;

    final minLat = list
        .map((point) => point.latitude)
        .reduce((a, b) => a < b ? a : b);
    final maxLat = list
        .map((point) => point.latitude)
        .reduce((a, b) => a > b ? a : b);
    final minLng = list
        .map((point) => point.longitude)
        .reduce((a, b) => a < b ? a : b);
    final maxLng = list
        .map((point) => point.longitude)
        .reduce((a, b) => a > b ? a : b);
    final span = ((maxLat - minLat).abs() + (maxLng - minLng).abs()) / 2;

    if (span > 0.5) return 8.7;
    if (span > 0.28) return 9.5;
    if (span > 0.15) return 10.5;
    if (span > 0.07) return 11.7;
    if (span > 0.025) return 13;
    return 14.4;
  }
}

class _RoutePlace {
  final String? stopId;
  final String stopCode;
  final String name;
  final double latitude;
  final double longitude;

  const _RoutePlace(
    this.stopId,
    this.stopCode,
    this.name,
    this.latitude,
    this.longitude,
  );

  factory _RoutePlace.fromJson(Map<String, dynamic> json) {
    return _RoutePlace(
      json['stopId']?.toString() ?? json['stop_id']?.toString(),
      json['stopCode']?.toString() ?? json['stop_code']?.toString() ?? '',
      json['name']?.toString() ?? 'Stop',
      _number(json['latitude']),
      _number(json['longitude']),
    );
  }

  factory _RoutePlace.custom(String name, LatLng position) {
    final id = DateTime.now().microsecondsSinceEpoch;
    return _RoutePlace(
      null,
      'CUSTOM-$id',
      name,
      position.latitude,
      position.longitude,
    );
  }

  bool get hasCoordinates => latitude != 0 || longitude != 0;

  String get identity => stopId ?? '$stopCode-$name-$latitude-$longitude';

  LatLng get position => LatLng(latitude, longitude);

  Map<String, dynamic> toJson() {
    return {
      if (stopId != null) 'stopId': stopId,
      'name': name,
      'latitude': latitude,
      'longitude': longitude,
    };
  }

  static double _number(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '') ?? 0;
  }

  @override
  bool operator ==(Object other) {
    return other is _RoutePlace && other.identity == identity;
  }

  @override
  int get hashCode => identity.hashCode;
}
