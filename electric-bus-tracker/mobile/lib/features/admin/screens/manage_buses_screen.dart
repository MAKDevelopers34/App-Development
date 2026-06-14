import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/services/api_service.dart';
import '../../../core/theme/app_theme.dart';
import '../utils/admin_navigation.dart';
import '../widgets/admin_bottom_nav.dart';

class ManageBusesScreen extends StatefulWidget {
  const ManageBusesScreen({super.key});

  @override
  State<ManageBusesScreen> createState() => _ManageBusesScreenState();
}

class _ManageBusesScreenState extends State<ManageBusesScreen> {
  final _searchController = TextEditingController();
  List<dynamic> _buses = [];
  List<dynamic> _filtered = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadBuses();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadBuses() async {
    setState(() => _isLoading = true);
    try {
      final res = await ApiService.get('/admin/buses');
      if (!mounted) return;
      setState(() {
        _buses = res['buses'] ?? [];
        _applySearch();
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      _showSnack('Could not load buses', isError: true);
    }
  }

  void _applySearch() {
    final term = _searchController.text.trim().toLowerCase();
    _filtered = _buses.where((raw) {
      final bus = Map<String, dynamic>.from(raw as Map);
      final values = [
        bus['busNumber'],
        bus['model'],
        bus['capacity'],
        bus['status'],
      ].map((value) => value?.toString().toLowerCase() ?? '');
      return term.isEmpty || values.any((value) => value.contains(term));
    }).toList();
  }

  void _search(String query) {
    setState(_applySearch);
  }

  Future<void> _openForm({Map<String, dynamic>? bus}) async {
    final saved = await showDialog<bool>(
      context: context,
      builder: (ctx) => _BusFormDialog(bus: bus),
    );
    if (saved == true) _loadBuses();
  }

  Future<void> _removeBus(Map<String, dynamic> bus) async {
    final busNumber = bus['busNumber']?.toString() ?? 'this bus';
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Remove Bus'),
        content: Text('Remove $busNumber from the active bus list?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: AppTheme.redStatus),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      final id = bus['busId']?.toString() ?? bus['_id']?.toString();
      if (id == null || id.isEmpty) return;
      final res = await ApiService.delete('/admin/buses/$id');
      if (!mounted) return;
      if (res['success'] == true) {
        _showSnack('Bus removed');
        _loadBuses();
      } else {
        _showSnack(res['message'] ?? 'Could not remove bus', isError: true);
      }
    } catch (_) {
      if (!mounted) return;
      _showSnack('Could not remove bus', isError: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AdminNavigation.dashboardBackScope(
      context: context,
      child: Scaffold(
        backgroundColor: AppTheme.bgGrey,
        appBar: AppBar(
          title: const Text('Manage Buses'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back_ios_new, size: 18),
            onPressed: () => AdminNavigation.goDashboard(context),
          ),
          actions: [
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: IconButton.filled(
                onPressed: () => _openForm(),
                icon: const Icon(Icons.add, size: 18),
                tooltip: 'Add bus',
              ),
            ),
          ],
        ),
        body: Column(
          children: [
            _buildSearch(),
            Expanded(
              child: _isLoading
                  ? const Center(
                      child: CircularProgressIndicator(
                        color: AppTheme.primaryGreen,
                      ),
                    )
                  : RefreshIndicator(
                      color: AppTheme.primaryGreen,
                      onRefresh: _loadBuses,
                      child: _filtered.isEmpty
                          ? const SingleChildScrollView(
                              physics: AlwaysScrollableScrollPhysics(),
                              child: SizedBox(
                                height: 420,
                                child: Center(
                                  child: Text(
                                    'No buses found',
                                    style: TextStyle(color: AppTheme.textGrey),
                                  ),
                                ),
                              ),
                            )
                          : ListView.builder(
                              physics: const AlwaysScrollableScrollPhysics(),
                              padding: const EdgeInsets.fromLTRB(
                                12,
                                10,
                                12,
                                12,
                              ),
                              itemCount: _filtered.length,
                              itemBuilder: (context, index) {
                                return _buildBusCard(
                                  Map<String, dynamic>.from(
                                    _filtered[index] as Map,
                                  ),
                                );
                              },
                            ),
                    ),
            ),
          ],
        ),
        bottomNavigationBar: const AdminBottomNav(selectedIndex: 2),
      ),
    );
  }

  Widget _buildSearch() {
    return Container(
      color: AppTheme.white,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: AppTheme.white,
          borderRadius: BorderRadius.circular(8),
          boxShadow: [
            BoxShadow(
              color: AppTheme.cardShadow,
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: TextField(
          controller: _searchController,
          onChanged: _search,
          style: const TextStyle(fontSize: 12),
          decoration: InputDecoration(
            hintText: 'Search bus number or model...',
            hintStyle: const TextStyle(fontSize: 12, color: AppTheme.textGrey),
            isDense: true,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 12,
              vertical: 10,
            ),
            suffixIcon: _searchController.text.isEmpty
                ? null
                : IconButton(
                    icon: const Icon(Icons.close, size: 16),
                    onPressed: () {
                      _searchController.clear();
                      _search('');
                    },
                  ),
          ),
        ),
      ),
    );
  }

  Widget _buildBusCard(Map<String, dynamic> bus) {
    final status = bus['status']?.toString().toLowerCase() ?? 'active';
    final active = status == 'active';
    final registered = _formatDate(bus['registrationDate']);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
      decoration: BoxDecoration(
        color: AppTheme.white,
        borderRadius: BorderRadius.circular(8),
        boxShadow: [
          BoxShadow(
            color: AppTheme.cardShadow,
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      bus['busNumber']?.toString() ?? 'Bus',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppTheme.textDark,
                        fontSize: 13,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 8),
                    _smallLine('Model: ${bus['model'] ?? 'Electric Bus'}'),
                    _smallLine('Capacity: ${bus['capacity'] ?? 40} seats'),
                    _smallLine('Registered: $registered'),
                  ],
                ),
              ),
              _StatusBadge(text: active ? 'Active' : 'Maintenance', active: active),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _SquareAction(
                color: AppTheme.orangeStatus,
                icon: Icons.edit_outlined,
                onTap: () => _openForm(bus: bus),
              ),
              const Spacer(),
              _SquareAction(
                color: AppTheme.redStatus,
                icon: Icons.close,
                onTap: () => _removeBus(bus),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _smallLine(String value) {
    return Text(
      value,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: const TextStyle(
        color: AppTheme.textDark,
        fontSize: 10,
        height: 1.25,
        fontWeight: FontWeight.w400,
      ),
    );
  }

  String _formatDate(dynamic value) {
    final parsed = DateTime.tryParse(value?.toString() ?? '');
    if (parsed == null) return 'N/A';
    return DateFormat('MMM d, yyyy').format(parsed);
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

class _BusFormDialog extends StatefulWidget {
  final Map<String, dynamic>? bus;

  const _BusFormDialog({this.bus});

  @override
  State<_BusFormDialog> createState() => _BusFormDialogState();
}

class _BusFormDialogState extends State<_BusFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _busNumberController;
  late final TextEditingController _modelController;
  late final TextEditingController _capacityController;
  String _status = 'Active';
  bool _isSaving = false;

  bool get _isEdit => widget.bus != null;

  @override
  void initState() {
    super.initState();
    final bus = widget.bus;
    _busNumberController = TextEditingController(
      text: bus?['busNumber']?.toString() ?? '',
    );
    _modelController = TextEditingController(
      text: bus?['model']?.toString() ?? 'Electric Bus',
    );
    _capacityController = TextEditingController(
      text: bus?['capacity']?.toString() ?? '40',
    );
    _status = _titleStatus(bus?['status']?.toString() ?? 'Active');
  }

  @override
  void dispose() {
    _busNumberController.dispose();
    _modelController.dispose();
    _capacityController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSaving = true);
    final busId = widget.bus?['busId'] ?? widget.bus?['_id'];
    final editEndpoint = busId == null ? null : '/admin/buses/$busId';
    final payload = {
      'busNumber': _busNumberController.text.trim(),
      'model': _modelController.text.trim(),
      'capacity': int.parse(_capacityController.text.trim()),
      'status': _status,
    };

    try {
      if (_isEdit && editEndpoint == null) {
        setState(() => _isSaving = false);
        _showLocalSnack('Bus ID missing. Refresh buses and try again.');
        return;
      }

      final res = _isEdit
          ? await ApiService.put(editEndpoint!, payload)
          : await ApiService.post('/admin/buses', payload);
      if (!mounted) return;
      if (res['success'] == true) {
        Navigator.pop(context, true);
      } else {
        setState(() => _isSaving = false);
        final message = res['message'] == 'Route not found'
            ? 'Backend update not deployed yet. Deploy backend and try again.'
            : res['message'] ?? 'Could not save bus';
        _showLocalSnack(message);
      }
    } catch (_) {
      if (!mounted) return;
      setState(() => _isSaving = false);
      _showLocalSnack('Connection error. Try again.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEdit ? 'Edit Bus' : 'Add Bus'),
      content: SingleChildScrollView(
        child: SizedBox(
          width: 280,
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _label('Bus Number *'),
                _input(
                  controller: _busNumberController,
                  hint: 'EV1',
                  validator: (value) =>
                      value == null || value.trim().isEmpty ? 'Required' : null,
                ),
                const SizedBox(height: 14),
                _label('Model *'),
                _input(
                  controller: _modelController,
                  hint: 'Electric Bus',
                  validator: (value) =>
                      value == null || value.trim().isEmpty ? 'Required' : null,
                ),
                const SizedBox(height: 14),
                _label('Capacity *'),
                _input(
                  controller: _capacityController,
                  hint: '40',
                  keyboardType: TextInputType.number,
                  validator: (value) {
                    final parsed = int.tryParse(value?.trim() ?? '');
                    if (parsed == null || parsed <= 0) return 'Invalid capacity';
                    return null;
                  },
                ),
                const SizedBox(height: 14),
                _label('Status *'),
                DropdownButtonFormField<String>(
                  initialValue: _status,
                  decoration: _inputDecoration(),
                  items: const [
                    DropdownMenuItem(value: 'Active', child: Text('Active')),
                    DropdownMenuItem(
                      value: 'Maintenance',
                      child: Text('Maintenance'),
                    ),
                  ],
                  onChanged: (value) {
                    if (value != null) setState(() => _status = value);
                  },
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isSaving ? null : () => Navigator.pop(context, false),
          child: const Text('Cancel'),
        ),
        ElevatedButton.icon(
          onPressed: _isSaving ? null : _save,
          icon: _isSaving
              ? const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(
                    color: AppTheme.white,
                    strokeWidth: 2,
                  ),
                )
              : Icon(_isEdit ? Icons.save_outlined : Icons.add, size: 16),
          label: Text(_isEdit ? 'Save' : 'Add'),
        ),
      ],
    );
  }

  Widget _label(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 7),
      child: Text(
        text,
        style: const TextStyle(
          color: AppTheme.textDark,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _input({
    required TextEditingController controller,
    required String hint,
    TextInputType keyboardType = TextInputType.text,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      decoration: _inputDecoration(hint: hint),
      style: const TextStyle(fontSize: 12),
      validator: validator,
    );
  }

  InputDecoration _inputDecoration({String? hint}) {
    return InputDecoration(
      hintText: hint,
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

  String _titleStatus(String value) {
    return value.toLowerCase() == 'maintenance' ? 'Maintenance' : 'Active';
  }

  void _showLocalSnack(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: AppTheme.redStatus),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String text;
  final bool active;

  const _StatusBadge({required this.text, required this.active});

  @override
  Widget build(BuildContext context) {
    final bg = active ? AppTheme.lightGreen : const Color(0xFFFFF2D6);
    final fg = active ? AppTheme.primaryGreen : AppTheme.orangeStatus;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        text,
        style: TextStyle(color: fg, fontSize: 10, fontWeight: FontWeight.w800),
      ),
    );
  }
}

class _SquareAction extends StatelessWidget {
  final Color color;
  final IconData icon;
  final VoidCallback onTap;

  const _SquareAction({
    required this.color,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(7),
      child: Container(
        width: 28,
        height: 28,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(7),
        ),
        child: Icon(icon, color: AppTheme.white, size: 17),
      ),
    );
  }
}
