import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'core/automata_core.dart';

void main() {
  runApp(const AutomataSimulatorApp());
}

enum SimulatorModule { dfa, nfa, output, pda, cfg, tm, glossary }

class ModuleInfo {
  const ModuleInfo(this.module, this.label, this.icon, this.description);

  final SimulatorModule module;
  final String label;
  final IconData icon;
  final String description;
}

const moduleInfo = [
  ModuleInfo(
    SimulatorModule.dfa,
    'DFA',
    Icons.account_tree_outlined,
    'Deterministic finite automata with table, trace, minimization, and JSON.',
  ),
  ModuleInfo(
    SimulatorModule.nfa,
    'NFA / TG',
    Icons.hub_outlined,
    'NFA execution, epsilon-closure, transition graphs, and subset construction.',
  ),
  ModuleInfo(
    SimulatorModule.output,
    'Moore / Mealy',
    Icons.output_outlined,
    'Finite automata with output strings.',
  ),
  ModuleInfo(
    SimulatorModule.pda,
    'PDA',
    Icons.layers_outlined,
    'Pushdown automata with stack visualization.',
  ),
  ModuleInfo(
    SimulatorModule.cfg,
    'CFG',
    Icons.schema_outlined,
    'Grammar editor, derivations, and ambiguity probing.',
  ),
  ModuleInfo(
    SimulatorModule.tm,
    'TM',
    Icons.memory_outlined,
    'Turing machine tape, read/write head, and bounded execution.',
  ),
  ModuleInfo(
    SimulatorModule.glossary,
    'Glossary',
    Icons.menu_book_outlined,
    'CSC-340 quick reference for core notation.',
  ),
];

class AutomataSimulatorApp extends StatefulWidget {
  const AutomataSimulatorApp({super.key});

  @override
  State<AutomataSimulatorApp> createState() => _AutomataSimulatorAppState();
}

class _AutomataSimulatorAppState extends State<AutomataSimulatorApp> {
  ThemeMode _themeMode = ThemeMode.light;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Automata Simulator',
      debugShowCheckedModeBanner: false,
      themeMode: _themeMode,
      theme: _theme(Brightness.light),
      darkTheme: _theme(Brightness.dark),
      home: AppShell(
        themeMode: _themeMode,
        onToggleTheme: () {
          setState(() {
            _themeMode = _themeMode == ThemeMode.dark
                ? ThemeMode.light
                : ThemeMode.dark;
          });
        },
      ),
    );
  }

  ThemeData _theme(Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF0F766E),
      brightness: brightness,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: brightness == Brightness.dark
          ? const Color(0xFF101418)
          : const Color(0xFFF8FAFC),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
        isDense: true,
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: BorderSide(color: scheme.outlineVariant),
        ),
      ),
      chipTheme: ChipThemeData(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
  }
}

class AppShell extends StatefulWidget {
  const AppShell({
    required this.themeMode,
    required this.onToggleTheme,
    super.key,
  });

  final ThemeMode themeMode;
  final VoidCallback onToggleTheme;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  var _selected = SimulatorModule.dfa;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 820;
        return Scaffold(
          appBar: compact
              ? AppBar(
                  title: Text(_title),
                  actions: [
                    IconButton(
                      tooltip: 'Toggle theme',
                      onPressed: widget.onToggleTheme,
                      icon: Icon(
                        widget.themeMode == ThemeMode.dark
                            ? Icons.light_mode_outlined
                            : Icons.dark_mode_outlined,
                      ),
                    ),
                  ],
                )
              : null,
          drawer: compact
              ? _ModuleDrawer(selected: _selected, onSelected: _select)
              : null,
          body: compact
              ? _ModuleBody(module: _selected)
              : Row(
                  children: [
                    NavigationRail(
                      extended: constraints.maxWidth >= 1120,
                      selectedIndex: moduleInfo.indexWhere(
                        (info) => info.module == _selected,
                      ),
                      onDestinationSelected: (index) =>
                          _select(moduleInfo[index].module),
                      leading: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        child: IconButton.filledTonal(
                          tooltip: 'Toggle theme',
                          onPressed: widget.onToggleTheme,
                          icon: Icon(
                            widget.themeMode == ThemeMode.dark
                                ? Icons.light_mode_outlined
                                : Icons.dark_mode_outlined,
                          ),
                        ),
                      ),
                      destinations: [
                        for (final info in moduleInfo)
                          NavigationRailDestination(
                            icon: Icon(info.icon),
                            selectedIcon: Icon(info.icon),
                            label: Text(info.label),
                          ),
                      ],
                    ),
                    const VerticalDivider(width: 1),
                    Expanded(child: _ModuleBody(module: _selected)),
                  ],
                ),
        );
      },
    );
  }

  String get _title {
    return moduleInfo.firstWhere((info) => info.module == _selected).label;
  }

  void _select(SimulatorModule module) {
    setState(() {
      _selected = module;
    });
    if (Navigator.canPop(context)) {
      Navigator.pop(context);
    }
  }
}

class _ModuleDrawer extends StatelessWidget {
  const _ModuleDrawer({required this.selected, required this.onSelected});

  final SimulatorModule selected;
  final ValueChanged<SimulatorModule> onSelected;

  @override
  Widget build(BuildContext context) {
    return NavigationDrawer(
      selectedIndex: moduleInfo.indexWhere((info) => info.module == selected),
      onDestinationSelected: (index) => onSelected(moduleInfo[index].module),
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(24, 28, 24, 12),
          child: Text(
            'Automata Simulator',
            style: TextStyle(fontWeight: FontWeight.w700),
          ),
        ),
        for (final info in moduleInfo)
          NavigationDrawerDestination(
            icon: Icon(info.icon),
            selectedIcon: Icon(info.icon),
            label: Text(info.label),
          ),
      ],
    );
  }
}

class _ModuleBody extends StatelessWidget {
  const _ModuleBody({required this.module});

  final SimulatorModule module;

  @override
  Widget build(BuildContext context) {
    final info = moduleInfo.firstWhere((item) => item.module == module);
    return SafeArea(
      child: Column(
        children: [
          _PageHeader(info: info),
          Expanded(
            child: switch (module) {
              SimulatorModule.dfa => const DfaScreen(),
              SimulatorModule.nfa => const NfaScreen(),
              SimulatorModule.output => const OutputMachinesScreen(),
              SimulatorModule.pda => const PdaScreen(),
              SimulatorModule.cfg => const CfgScreen(),
              SimulatorModule.tm => const TuringMachineScreen(),
              SimulatorModule.glossary => const GlossaryScreen(),
            },
          ),
        ],
      ),
    );
  }
}

class _PageHeader extends StatelessWidget {
  const _PageHeader({required this.info});

  final ModuleInfo info;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: scheme.outlineVariant)),
      ),
      child: Wrap(
        spacing: 16,
        runSpacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          Icon(info.icon, color: scheme.primary),
          Text(
            info.label,
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
          ),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: Text(
              info.description,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class DfaScreen extends StatefulWidget {
  const DfaScreen({super.key});

  @override
  State<DfaScreen> createState() => _DfaScreenState();
}

class _DfaScreenState extends State<DfaScreen> {
  late DfaDefinition _dfa;
  late SimulationResult _result;
  final _inputController = TextEditingController(text: 'aab');
  final _newStateController = TextEditingController();
  final _transitionSymbolController = TextEditingController(text: 'a');
  final _jsonController = TextEditingController();
  final _positions = <String, Offset>{
    'q0': const Offset(0.18, 0.56),
    'q1': const Offset(0.50, 0.26),
    'q2': const Offset(0.82, 0.56),
  };
  String? _selectedState = 'q0';
  String? _fromState = 'q0';
  String? _toState = 'q1';
  var _stepIndex = 0;

  @override
  void initState() {
    super.initState();
    _dfa = AutomataCatalog.endingInAbDfa();
    _result = _dfa.run(_inputController.text);
    _jsonController.text = _dfa.toPrettyJson();
  }

  @override
  void dispose() {
    _inputController.dispose();
    _newStateController.dispose();
    _transitionSymbolController.dispose();
    _jsonController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final step = _result.steps[_stepIndex.clamp(0, _result.steps.length - 1)];
    return _ScreenScroll(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _RunBar(
            controller: _inputController,
            accepted: _result.accepted,
            summary: _result.summary,
            onRun: _run,
            onStep: _step,
            onReset: _reset,
          ),
          const SizedBox(height: 16),
          _ResponsiveTwoColumn(
            left: _Panel(
              title: 'Visual Construction',
              trailing: Wrap(
                spacing: 8,
                children: [
                  _SmallChip(text: 'Start ${_dfa.startState}'),
                  _SmallChip(text: 'Accept ${_dfa.acceptStates.join(', ')}'),
                ],
              ),
              child: SizedBox(
                height: 390,
                child: AutomataCanvas(
                  states: _dfa.states,
                  acceptStates: _dfa.acceptStates,
                  startState: _dfa.startState,
                  positions: _positions,
                  transitions: _dfaTransitions(_dfa),
                  highlightedStates: step.activeStates.toSet(),
                  selectedState: _selectedState,
                  onPositionsChanged: (positions) => setState(() {
                    _positions
                      ..clear()
                      ..addAll(positions);
                  }),
                  onStateSelected: (state) => setState(() {
                    _selectedState = state;
                    _fromState = state;
                  }),
                ),
              ),
            ),
            right: _Panel(
              title: 'Editor',
              child: _DfaEditor(
                dfa: _dfa,
                selectedState: _selectedState,
                fromState: _fromState,
                toState: _toState,
                newStateController: _newStateController,
                transitionSymbolController: _transitionSymbolController,
                onSelectedChanged: (value) =>
                    setState(() => _selectedState = value),
                onFromChanged: (value) => setState(() => _fromState = value),
                onToChanged: (value) => setState(() => _toState = value),
                onAddState: _addState,
                onDeleteSelected: _deleteSelected,
                onSetStart: _setSelectedStart,
                onToggleAccept: _toggleSelectedAccept,
                onAddTransition: _addTransition,
                onMinimize: _minimize,
              ),
            ),
          ),
          const SizedBox(height: 16),
          _ResponsiveTwoColumn(
            left: _Panel(
              title: 'Transition Table',
              child: _DfaTable(dfa: _dfa),
            ),
            right: _Panel(
              title: 'JSON Save / Load',
              child: Column(
                children: [
                  TextField(
                    controller: _jsonController,
                    minLines: 8,
                    maxLines: 10,
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 12,
                    ),
                    decoration: const InputDecoration(labelText: 'DFA JSON'),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      FilledButton.icon(
                        onPressed: _copyJson,
                        icon: const Icon(Icons.copy_outlined),
                        label: const Text('Copy'),
                      ),
                      OutlinedButton.icon(
                        onPressed: _loadJson,
                        icon: const Icon(Icons.upload_file_outlined),
                        label: const Text('Load'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => setState(
                          () => _jsonController.text = _dfa.toPrettyJson(),
                        ),
                        icon: const Icon(Icons.refresh_outlined),
                        label: const Text('Refresh'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          _Panel(
            title: 'Execution Trace',
            child: TraceView(
              result: _result,
              selectedIndex: _stepIndex,
              onSelected: (index) => setState(() => _stepIndex = index),
            ),
          ),
        ],
      ),
    );
  }

  void _run() {
    setState(() {
      _result = _dfa.run(_inputController.text.trim());
      _stepIndex = _result.steps.length - 1;
    });
  }

  void _step() {
    setState(() {
      _result = _dfa.run(_inputController.text.trim());
      _stepIndex = math.min(_stepIndex + 1, _result.steps.length - 1);
    });
  }

  void _reset() {
    setState(() {
      _result = _dfa.run(_inputController.text.trim());
      _stepIndex = 0;
    });
  }

  void _addState() {
    final name = _newStateController.text.trim();
    if (name.isEmpty || _dfa.states.contains(name)) {
      _message('Use a new state name.');
      return;
    }
    final updatedStates = [..._dfa.states, name]..sort();
    final updatedTransitions = _cloneDfaTransitions(_dfa)..[name] = {};
    setState(() {
      _dfa = DfaDefinition(
        states: updatedStates,
        alphabet: _dfa.alphabet,
        startState: _dfa.startState,
        acceptStates: _dfa.acceptStates,
        transitions: updatedTransitions,
      );
      _positions[name] = Offset(0.22 + (_positions.length % 4) * 0.18, 0.72);
      _selectedState = name;
      _fromState = name;
      _toState ??= name;
      _newStateController.clear();
      _refreshAfterEdit();
    });
  }

  void _deleteSelected() {
    final selected = _selectedState;
    if (selected == null || selected == _dfa.startState) {
      _message('Select a non-start state to delete.');
      return;
    }
    final updatedStates = _dfa.states
        .where((state) => state != selected)
        .toList();
    final updatedTransitions = <String, Map<String, String>>{};
    for (final entry in _dfa.transitions.entries) {
      if (entry.key == selected) {
        continue;
      }
      updatedTransitions[entry.key] = {
        for (final transition in entry.value.entries)
          if (transition.value != selected) transition.key: transition.value,
      };
    }
    setState(() {
      _dfa = DfaDefinition(
        states: updatedStates,
        alphabet: _dfa.alphabet,
        startState: _dfa.startState,
        acceptStates: _dfa.acceptStates.difference({selected}),
        transitions: updatedTransitions,
      );
      _positions.remove(selected);
      _selectedState = updatedStates.isEmpty ? null : updatedStates.first;
      _fromState = _selectedState;
      _toState = _selectedState;
      _refreshAfterEdit();
    });
  }

  void _setSelectedStart() {
    final selected = _selectedState;
    if (selected == null) {
      return;
    }
    setState(() {
      _dfa = DfaDefinition(
        states: _dfa.states,
        alphabet: _dfa.alphabet,
        startState: selected,
        acceptStates: _dfa.acceptStates,
        transitions: _dfa.transitions,
      );
      _refreshAfterEdit();
    });
  }

  void _toggleSelectedAccept() {
    final selected = _selectedState;
    if (selected == null) {
      return;
    }
    final acceptStates = Set<String>.of(_dfa.acceptStates);
    if (!acceptStates.add(selected)) {
      acceptStates.remove(selected);
    }
    setState(() {
      _dfa = DfaDefinition(
        states: _dfa.states,
        alphabet: _dfa.alphabet,
        startState: _dfa.startState,
        acceptStates: acceptStates,
        transitions: _dfa.transitions,
      );
      _refreshAfterEdit();
    });
  }

  void _addTransition() {
    final from = _fromState;
    final to = _toState;
    final symbol = _transitionSymbolController.text.trim();
    if (from == null || to == null || symbol.isEmpty) {
      _message('Choose from/to states and enter a symbol.');
      return;
    }
    final transitions = _cloneDfaTransitions(_dfa);
    transitions.putIfAbsent(from, () => {})[symbol] = to;
    final alphabet = {..._dfa.alphabet, symbol}.toList()..sort();
    setState(() {
      _dfa = DfaDefinition(
        states: _dfa.states,
        alphabet: alphabet,
        startState: _dfa.startState,
        acceptStates: _dfa.acceptStates,
        transitions: transitions,
      );
      _refreshAfterEdit();
    });
  }

  void _minimize() {
    setState(() {
      _dfa = _dfa.minimize();
      _positions
        ..clear()
        ..addAll(_defaultPositions(_dfa.states));
      _selectedState = _dfa.startState;
      _fromState = _dfa.startState;
      _toState = _dfa.states.first;
      _refreshAfterEdit();
    });
  }

  Future<void> _copyJson() async {
    _jsonController.text = _dfa.toPrettyJson();
    await Clipboard.setData(ClipboardData(text: _jsonController.text));
    _message('DFA JSON copied.');
  }

  void _loadJson() {
    try {
      final decoded = jsonDecode(_jsonController.text) as Map<String, dynamic>;
      final loaded = DfaDefinition.fromJson(decoded);
      setState(() {
        _dfa = loaded;
        _positions
          ..clear()
          ..addAll(_defaultPositions(loaded.states));
        _selectedState = loaded.startState;
        _fromState = loaded.startState;
        _toState = loaded.states.isEmpty ? null : loaded.states.first;
        _refreshAfterEdit();
      });
    } catch (error) {
      _message('Could not load JSON: $error');
    }
  }

  void _refreshAfterEdit() {
    _jsonController.text = _dfa.toPrettyJson();
    _result = _dfa.run(_inputController.text.trim());
    _stepIndex = math.min(_stepIndex, _result.steps.length - 1);
  }

  void _message(String text) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }
}

class _DfaEditor extends StatelessWidget {
  const _DfaEditor({
    required this.dfa,
    required this.selectedState,
    required this.fromState,
    required this.toState,
    required this.newStateController,
    required this.transitionSymbolController,
    required this.onSelectedChanged,
    required this.onFromChanged,
    required this.onToChanged,
    required this.onAddState,
    required this.onDeleteSelected,
    required this.onSetStart,
    required this.onToggleAccept,
    required this.onAddTransition,
    required this.onMinimize,
  });

  final DfaDefinition dfa;
  final String? selectedState;
  final String? fromState;
  final String? toState;
  final TextEditingController newStateController;
  final TextEditingController transitionSymbolController;
  final ValueChanged<String?> onSelectedChanged;
  final ValueChanged<String?> onFromChanged;
  final ValueChanged<String?> onToChanged;
  final VoidCallback onAddState;
  final VoidCallback onDeleteSelected;
  final VoidCallback onSetStart;
  final VoidCallback onToggleAccept;
  final VoidCallback onAddTransition;
  final VoidCallback onMinimize;

  @override
  Widget build(BuildContext context) {
    final selectedIsAccept =
        selectedState != null && dfa.acceptStates.contains(selectedState);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          initialValue:
              selectedState != null && dfa.states.contains(selectedState)
              ? selectedState
              : null,
          decoration: const InputDecoration(labelText: 'Selected state'),
          items: [
            for (final state in dfa.states)
              DropdownMenuItem(value: state, child: Text(state)),
          ],
          onChanged: onSelectedChanged,
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            OutlinedButton.icon(
              onPressed: onSetStart,
              icon: const Icon(Icons.flag_outlined),
              label: const Text('Start'),
            ),
            OutlinedButton.icon(
              onPressed: onToggleAccept,
              icon: Icon(
                selectedIsAccept
                    ? Icons.check_circle
                    : Icons.radio_button_unchecked,
              ),
              label: Text(selectedIsAccept ? 'Unaccept' : 'Accept'),
            ),
            OutlinedButton.icon(
              onPressed: onDeleteSelected,
              icon: const Icon(Icons.delete_outline),
              label: const Text('Delete'),
            ),
          ],
        ),
        const Divider(height: 28),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: newStateController,
                decoration: const InputDecoration(labelText: 'New state'),
                onSubmitted: (_) => onAddState(),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filledTonal(
              tooltip: 'Add state',
              onPressed: onAddState,
              icon: const Icon(Icons.add_circle_outline),
            ),
          ],
        ),
        const Divider(height: 28),
        Wrap(
          spacing: 8,
          runSpacing: 10,
          children: [
            SizedBox(
              width: 150,
              child: DropdownButtonFormField<String>(
                initialValue:
                    fromState != null && dfa.states.contains(fromState)
                    ? fromState
                    : null,
                decoration: const InputDecoration(labelText: 'From'),
                items: [
                  for (final state in dfa.states)
                    DropdownMenuItem(value: state, child: Text(state)),
                ],
                onChanged: onFromChanged,
              ),
            ),
            SizedBox(
              width: 110,
              child: TextField(
                controller: transitionSymbolController,
                decoration: const InputDecoration(labelText: 'Symbol'),
              ),
            ),
            SizedBox(
              width: 150,
              child: DropdownButtonFormField<String>(
                initialValue: toState != null && dfa.states.contains(toState)
                    ? toState
                    : null,
                decoration: const InputDecoration(labelText: 'To'),
                items: [
                  for (final state in dfa.states)
                    DropdownMenuItem(value: state, child: Text(state)),
                ],
                onChanged: onToChanged,
              ),
            ),
            FilledButton.icon(
              onPressed: onAddTransition,
              icon: const Icon(Icons.call_split_outlined),
              label: const Text('Add'),
            ),
          ],
        ),
        const Divider(height: 28),
        FilledButton.tonalIcon(
          onPressed: onMinimize,
          icon: const Icon(Icons.compress_outlined),
          label: const Text('Minimize DFA'),
        ),
      ],
    );
  }
}

class NfaScreen extends StatefulWidget {
  const NfaScreen({super.key});

  @override
  State<NfaScreen> createState() => _NfaScreenState();
}

class _NfaScreenState extends State<NfaScreen> {
  final _nfa = AutomataCatalog.substringAbNfa();
  final _inputController = TextEditingController(text: 'baba');
  final _positions = <String, Offset>{
    'q0': const Offset(0.18, 0.56),
    'q1': const Offset(0.50, 0.26),
    'q2': const Offset(0.82, 0.56),
  };
  late SimulationResult _result;
  var _stepIndex = 0;
  String _converted = '';

  @override
  void initState() {
    super.initState();
    _result = _nfa.run(_inputController.text);
  }

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final step = _result.steps[_stepIndex.clamp(0, _result.steps.length - 1)];
    return _ScreenScroll(
      child: Column(
        children: [
          _RunBar(
            controller: _inputController,
            accepted: _result.accepted,
            summary: _result.summary,
            onRun: _run,
            onStep: _step,
            onReset: _reset,
          ),
          const SizedBox(height: 16),
          _ResponsiveTwoColumn(
            left: _Panel(
              title: 'NFA / Transition Graph',
              trailing: _SmallChip(
                text: 'epsilon = ${AutomataSymbols.epsilon}',
              ),
              child: SizedBox(
                height: 390,
                child: AutomataCanvas(
                  states: _nfa.states,
                  acceptStates: _nfa.acceptStates,
                  startState: _nfa.startState,
                  positions: _positions,
                  transitions: _nfaTransitions(_nfa),
                  highlightedStates: step.activeStates.toSet(),
                  onPositionsChanged: (positions) => setState(() {
                    _positions
                      ..clear()
                      ..addAll(positions);
                  }),
                ),
              ),
            ),
            right: _Panel(
              title: 'Subset Construction',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Current active set: ${step.state}'),
                  const SizedBox(height: 8),
                  Text('Closure note: ${step.note}'),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: _convert,
                    icon: const Icon(Icons.transform_outlined),
                    label: const Text('Convert to DFA'),
                  ),
                  const SizedBox(height: 12),
                  if (_converted.isNotEmpty)
                    SelectableText(
                      _converted,
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 12,
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          _Panel(
            title: 'Parallel Execution Trace',
            child: TraceView(
              result: _result,
              selectedIndex: _stepIndex,
              onSelected: (index) => setState(() => _stepIndex = index),
            ),
          ),
        ],
      ),
    );
  }

  void _run() {
    setState(() {
      _result = _nfa.run(_inputController.text.trim());
      _stepIndex = _result.steps.length - 1;
    });
  }

  void _step() {
    setState(() {
      _result = _nfa.run(_inputController.text.trim());
      _stepIndex = math.min(_stepIndex + 1, _result.steps.length - 1);
    });
  }

  void _reset() {
    setState(() {
      _result = _nfa.run(_inputController.text.trim());
      _stepIndex = 0;
    });
  }

  void _convert() {
    final converted = _nfa.toDfa();
    setState(() {
      _converted = converted.toPrettyJson();
    });
  }
}

enum OutputMachineKind { moore, mealy }

class OutputMachinesScreen extends StatefulWidget {
  const OutputMachinesScreen({super.key});

  @override
  State<OutputMachinesScreen> createState() => _OutputMachinesScreenState();
}

class _OutputMachinesScreenState extends State<OutputMachinesScreen> {
  final _moore = AutomataCatalog.parityMoore();
  final _mealy = AutomataCatalog.parityMealy();
  final _inputController = TextEditingController(text: '10101');
  final _positions = <String, Offset>{
    'even': const Offset(0.28, 0.50),
    'odd': const Offset(0.72, 0.50),
  };
  var _kind = OutputMachineKind.moore;
  late SimulationResult _result;
  var _stepIndex = 0;

  @override
  void initState() {
    super.initState();
    _result = _moore.run(_inputController.text);
  }

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final step = _result.steps[_stepIndex.clamp(0, _result.steps.length - 1)];
    final isMoore = _kind == OutputMachineKind.moore;
    return _ScreenScroll(
      child: Column(
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 12,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              SegmentedButton<OutputMachineKind>(
                segments: const [
                  ButtonSegment(
                    value: OutputMachineKind.moore,
                    icon: Icon(Icons.radio_button_checked),
                    label: Text('Moore'),
                  ),
                  ButtonSegment(
                    value: OutputMachineKind.mealy,
                    icon: Icon(Icons.route_outlined),
                    label: Text('Mealy'),
                  ),
                ],
                selected: {_kind},
                onSelectionChanged: (selection) {
                  setState(() {
                    _kind = selection.first;
                    _recompute(lastStep: false);
                  });
                },
              ),
              SizedBox(
                width: 260,
                child: TextField(
                  controller: _inputController,
                  decoration: const InputDecoration(labelText: 'Input string'),
                  onSubmitted: (_) => _run(),
                ),
              ),
              IconButton.filled(
                tooltip: 'Run',
                onPressed: _run,
                icon: const Icon(Icons.play_arrow),
              ),
              IconButton.filledTonal(
                tooltip: 'Step',
                onPressed: _step,
                icon: const Icon(Icons.skip_next_outlined),
              ),
              IconButton.outlined(
                tooltip: 'Reset',
                onPressed: _reset,
                icon: const Icon(Icons.restart_alt_outlined),
              ),
              _StatusPill(accepted: true, text: 'Output ${_result.output}'),
            ],
          ),
          const SizedBox(height: 16),
          _ResponsiveTwoColumn(
            left: _Panel(
              title: isMoore ? 'Moore Machine' : 'Mealy Machine',
              child: SizedBox(
                height: 360,
                child: AutomataCanvas(
                  states: isMoore ? _moore.states : _mealy.states,
                  acceptStates: const {},
                  startState: isMoore ? _moore.startState : _mealy.startState,
                  positions: _positions,
                  transitions: isMoore
                      ? _mooreTransitions(_moore)
                      : _mealyTransitions(_mealy),
                  highlightedStates: step.activeStates.toSet(),
                  nodeLabels: isMoore ? _moore.outputs : const {},
                  onPositionsChanged: (positions) => setState(() {
                    _positions
                      ..clear()
                      ..addAll(positions);
                  }),
                ),
              ),
            ),
            right: _Panel(
              title: 'Output Trace',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Current state: ${step.state}'),
                  const SizedBox(height: 8),
                  Text(
                    'Produced so far: ${step.output.isEmpty ? '-' : step.output}',
                  ),
                  const SizedBox(height: 8),
                  Text(step.note),
                  const SizedBox(height: 16),
                  TraceView(
                    result: _result,
                    selectedIndex: _stepIndex,
                    onSelected: (index) => setState(() => _stepIndex = index),
                    compact: true,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _run() {
    setState(() => _recompute(lastStep: true));
  }

  void _step() {
    setState(() {
      _recompute(lastStep: false);
      _stepIndex = math.min(_stepIndex + 1, _result.steps.length - 1);
    });
  }

  void _reset() {
    setState(() => _recompute(lastStep: false));
  }

  void _recompute({required bool lastStep}) {
    _result = _kind == OutputMachineKind.moore
        ? _moore.run(_inputController.text.trim())
        : _mealy.run(_inputController.text.trim());
    _stepIndex = lastStep ? _result.steps.length - 1 : 0;
  }
}

class PdaScreen extends StatefulWidget {
  const PdaScreen({super.key});

  @override
  State<PdaScreen> createState() => _PdaScreenState();
}

class _PdaScreenState extends State<PdaScreen> {
  final _pda = AutomataCatalog.anBnPda();
  final _inputController = TextEditingController(text: 'aaabbb');
  final _positions = <String, Offset>{
    'q0': const Offset(0.18, 0.56),
    'q1': const Offset(0.52, 0.28),
    'q2': const Offset(0.82, 0.56),
  };
  late SimulationResult _result;
  var _stepIndex = 0;

  @override
  void initState() {
    super.initState();
    _result = _pda.run(_inputController.text);
  }

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final step = _result.steps[_stepIndex.clamp(0, _result.steps.length - 1)];
    return _ScreenScroll(
      child: Column(
        children: [
          _RunBar(
            controller: _inputController,
            accepted: _result.accepted,
            summary: _result.summary,
            onRun: _run,
            onStep: _step,
            onReset: _reset,
          ),
          const SizedBox(height: 16),
          _ResponsiveTwoColumn(
            left: _Panel(
              title: 'PDA for a^n b^n',
              trailing: const _SmallChip(text: 'Accept by final state'),
              child: SizedBox(
                height: 390,
                child: AutomataCanvas(
                  states: _pda.states,
                  acceptStates: _pda.acceptStates,
                  startState: _pda.startState,
                  positions: _positions,
                  transitions: _pdaTransitions(_pda),
                  highlightedStates: step.activeStates.toSet(),
                  onPositionsChanged: (positions) => setState(() {
                    _positions
                      ..clear()
                      ..addAll(positions);
                  }),
                ),
              ),
            ),
            right: _Panel(
              title: 'Animated Stack',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Current transition: ${step.note}'),
                  const SizedBox(height: 12),
                  StackView(stack: step.stack),
                  const SizedBox(height: 16),
                  Text(
                    '7-tuple: Q=${_pda.states}, Sigma=${_pda.inputAlphabet}, Gamma=${_pda.stackAlphabet}, q0=${_pda.startState}, F=${_pda.acceptStates}',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          _Panel(
            title: 'PDA Trace',
            child: TraceView(
              result: _result,
              selectedIndex: _stepIndex,
              onSelected: (index) => setState(() => _stepIndex = index),
            ),
          ),
        ],
      ),
    );
  }

  void _run() {
    setState(() {
      _result = _pda.run(_inputController.text.trim());
      _stepIndex = _result.steps.length - 1;
    });
  }

  void _step() {
    setState(() {
      _result = _pda.run(_inputController.text.trim());
      _stepIndex = math.min(_stepIndex + 1, _result.steps.length - 1);
    });
  }

  void _reset() {
    setState(() {
      _result = _pda.run(_inputController.text.trim());
      _stepIndex = 0;
    });
  }
}

class CfgScreen extends StatefulWidget {
  const CfgScreen({super.key});

  @override
  State<CfgScreen> createState() => _CfgScreenState();
}

class _CfgScreenState extends State<CfgScreen> {
  final _grammarController = TextEditingController(text: 'S -> a S b | a b');
  final _startController = TextEditingController(text: 'S');
  List<List<String>> _derivation = const [
    ['S'],
  ];
  Map<String, int> _generated = const {};
  var _leftmost = true;

  @override
  void initState() {
    super.initState();
    _derive(leftmost: true);
  }

  @override
  void dispose() {
    _grammarController.dispose();
    _startController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final grammar = _parseGrammar();
    return _ScreenScroll(
      child: _ResponsiveTwoColumn(
        left: _Panel(
          title: 'CFG Editor',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  SizedBox(
                    width: 120,
                    child: TextField(
                      controller: _startController,
                      decoration: const InputDecoration(labelText: 'Start'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  SegmentedButton<bool>(
                    segments: const [
                      ButtonSegment(
                        value: true,
                        icon: Icon(Icons.keyboard_double_arrow_left),
                        label: Text('Leftmost'),
                      ),
                      ButtonSegment(
                        value: false,
                        icon: Icon(Icons.keyboard_double_arrow_right),
                        label: Text('Rightmost'),
                      ),
                    ],
                    selected: {_leftmost},
                    onSelectionChanged: (value) =>
                        _derive(leftmost: value.first),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _grammarController,
                minLines: 8,
                maxLines: 12,
                style: const TextStyle(fontFamily: 'monospace'),
                decoration: const InputDecoration(
                  labelText: 'Productions',
                  hintText: 'S -> a S b | a b',
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilledButton.icon(
                    onPressed: () => _derive(leftmost: _leftmost),
                    icon: const Icon(Icons.account_tree_outlined),
                    label: const Text('Derive'),
                  ),
                  OutlinedButton.icon(
                    onPressed: _probeAmbiguity,
                    icon: const Icon(Icons.travel_explore_outlined),
                    label: const Text('Probe Ambiguity'),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text('Productions loaded: ${grammar.productions.length}'),
            ],
          ),
        ),
        right: _Panel(
          title: 'Derivation and Parse Frontier',
          trailing: _SmallChip(text: _leftmost ? 'Leftmost' : 'Rightmost'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (var i = 0; i < _derivation.length; i++)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    '${i + 1}. ${_formText(_derivation[i])}',
                    style: const TextStyle(fontFamily: 'monospace'),
                  ),
                ),
              const SizedBox(height: 12),
              FrontierView(
                symbols: _derivation.isEmpty ? const [] : _derivation.last,
              ),
              if (_generated.isNotEmpty) ...[
                const Divider(height: 28),
                Text(
                  _generated.values.any((count) => count > 1)
                      ? 'Ambiguity candidate found in bounded search.'
                      : 'No ambiguity found in bounded search.',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final entry in _generated.entries.take(12))
                      _SmallChip(
                        text:
                            '${entry.key.isEmpty ? AutomataSymbols.epsilon : entry.key}: ${entry.value}',
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  CfgDefinition _parseGrammar() {
    return CfgDefinition.parse(
      _grammarController.text,
      startSymbol: _startController.text.trim().isEmpty
          ? 'S'
          : _startController.text.trim(),
    );
  }

  void _derive({required bool leftmost}) {
    final grammar = _parseGrammar();
    setState(() {
      _leftmost = leftmost;
      _derivation = grammar.derive(leftmost: leftmost, maxSteps: 7);
    });
  }

  void _probeAmbiguity() {
    final grammar = _parseGrammar();
    setState(() {
      _generated = grammar.generateTerminalStrings(maxDepth: 7, maxLength: 8);
    });
  }
}

class TuringMachineScreen extends StatefulWidget {
  const TuringMachineScreen({super.key});

  @override
  State<TuringMachineScreen> createState() => _TuringMachineScreenState();
}

class _TuringMachineScreenState extends State<TuringMachineScreen> {
  final _tm = AutomataCatalog.binaryIncrementTm();
  final _inputController = TextEditingController(text: '111');
  final _positions = <String, Offset>{
    'scan': const Offset(0.18, 0.55),
    'carry': const Offset(0.52, 0.25),
    'accept': const Offset(0.82, 0.55),
  };
  late SimulationResult _result;
  var _stepIndex = 0;

  @override
  void initState() {
    super.initState();
    _result = _tm.run(_inputController.text);
  }

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final step = _result.steps[_stepIndex.clamp(0, _result.steps.length - 1)];
    return _ScreenScroll(
      child: Column(
        children: [
          _RunBar(
            controller: _inputController,
            accepted: _result.accepted,
            summary: _result.summary,
            onRun: _run,
            onStep: _step,
            onReset: _reset,
          ),
          const SizedBox(height: 16),
          _ResponsiveTwoColumn(
            left: _Panel(
              title: 'Binary Increment Turing Machine',
              trailing: const _SmallChip(text: 'Blank = _'),
              child: SizedBox(
                height: 390,
                child: AutomataCanvas(
                  states: _tm.states,
                  acceptStates: _tm.acceptStates,
                  startState: _tm.startState,
                  positions: _positions,
                  transitions: _tmTransitions(_tm),
                  highlightedStates: step.activeStates.toSet(),
                  onPositionsChanged: (positions) => setState(() {
                    _positions
                      ..clear()
                      ..addAll(positions);
                  }),
                ),
              ),
            ),
            right: _Panel(
              title: 'Tape',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('State: ${step.state}'),
                  const SizedBox(height: 8),
                  Text('Transition: ${step.note}'),
                  const SizedBox(height: 14),
                  TapeView(cells: step.tapeWindow, headIndex: step.headIndex),
                  const SizedBox(height: 16),
                  TraceView(
                    result: _result,
                    selectedIndex: _stepIndex,
                    onSelected: (index) => setState(() => _stepIndex = index),
                    compact: true,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _run() {
    setState(() {
      _result = _tm.run(_inputController.text.trim());
      _stepIndex = _result.steps.length - 1;
    });
  }

  void _step() {
    setState(() {
      _result = _tm.run(_inputController.text.trim());
      _stepIndex = math.min(_stepIndex + 1, _result.steps.length - 1);
    });
  }

  void _reset() {
    setState(() {
      _result = _tm.run(_inputController.text.trim());
      _stepIndex = 0;
    });
  }
}

class GlossaryScreen extends StatelessWidget {
  const GlossaryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final terms = {
      'Alphabet': 'A finite set of symbols, usually written as Sigma.',
      'String': 'A finite sequence of symbols over an alphabet.',
      'Kleene closure':
          'All finite strings over an alphabet, including epsilon.',
      'DFA': 'A 5-tuple with exactly one transition for each state and symbol.',
      'NFA': 'A finite automaton that may branch or use epsilon moves.',
      'PDA': 'An automaton with a stack, used for context-free languages.',
      'CFG':
          'A grammar with variables, terminals, productions, and a start symbol.',
      'Turing Machine':
          'A tape-based model of computation with read/write head movement.',
    };
    return _ScreenScroll(
      child: Wrap(
        spacing: 12,
        runSpacing: 12,
        children: [
          for (final entry in terms.entries)
            SizedBox(
              width: 320,
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        entry.key,
                        style: Theme.of(context).textTheme.titleMedium
                            ?.copyWith(fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 8),
                      Text(entry.value),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _ScreenScroll extends StatelessWidget {
  const _ScreenScroll({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: child,
    );
  }
}

class _ResponsiveTwoColumn extends StatelessWidget {
  const _ResponsiveTwoColumn({required this.left, required this.right});

  final Widget left;
  final Widget right;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 900) {
          return Column(children: [left, const SizedBox(height: 16), right]);
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 7, child: left),
            const SizedBox(width: 16),
            Expanded(flex: 4, child: right),
          ],
        );
      },
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.title, required this.child, this.trailing});

  final String title;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                if (trailing != null) trailing!,
              ],
            ),
            const SizedBox(height: 14),
            child,
          ],
        ),
      ),
    );
  }
}

class _RunBar extends StatelessWidget {
  const _RunBar({
    required this.controller,
    required this.accepted,
    required this.summary,
    required this.onRun,
    required this.onStep,
    required this.onReset,
  });

  final TextEditingController controller;
  final bool accepted;
  final String summary;
  final VoidCallback onRun;
  final VoidCallback onStep;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        SizedBox(
          width: 300,
          child: TextField(
            controller: controller,
            decoration: const InputDecoration(labelText: 'Input string'),
            onSubmitted: (_) => onRun(),
          ),
        ),
        IconButton.filled(
          tooltip: 'Run',
          onPressed: onRun,
          icon: const Icon(Icons.play_arrow),
        ),
        IconButton.filledTonal(
          tooltip: 'Step',
          onPressed: onStep,
          icon: const Icon(Icons.skip_next_outlined),
        ),
        IconButton.outlined(
          tooltip: 'Reset',
          onPressed: onReset,
          icon: const Icon(Icons.restart_alt_outlined),
        ),
        _StatusPill(accepted: accepted, text: summary),
      ],
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.accepted, required this.text});

  final bool accepted;
  final String text;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final color = accepted ? const Color(0xFF0F766E) : scheme.error;
    return Container(
      constraints: const BoxConstraints(maxWidth: 460),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.38)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            accepted ? Icons.check_circle_outline : Icons.cancel_outlined,
            color: color,
            size: 18,
          ),
          const SizedBox(width: 8),
          Flexible(child: Text(text, overflow: TextOverflow.ellipsis)),
        ],
      ),
    );
  }
}

class _SmallChip extends StatelessWidget {
  const _SmallChip({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text(text),
      visualDensity: VisualDensity.compact,
      padding: EdgeInsets.zero,
    );
  }
}

class TraceView extends StatelessWidget {
  const TraceView({
    required this.result,
    required this.selectedIndex,
    required this.onSelected,
    this.compact = false,
    super.key,
  });

  final SimulationResult result;
  final int selectedIndex;
  final ValueChanged<int> onSelected;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final height = compact ? 220.0 : 280.0;
    return SizedBox(
      height: height,
      child: ListView.separated(
        itemCount: result.steps.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (context, index) {
          final step = result.steps[index];
          final selected = selectedIndex == index;
          return InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: () => onSelected(index),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: selected
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(context).colorScheme.outlineVariant,
                ),
                color: selected
                    ? Theme.of(
                        context,
                      ).colorScheme.primary.withValues(alpha: 0.08)
                    : Colors.transparent,
              ),
              child: Wrap(
                spacing: 12,
                runSpacing: 6,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  _SmallChip(text: '#${step.index}'),
                  Text(
                    'State ${step.state}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  if (step.symbol.isNotEmpty) Text('Read ${step.symbol}'),
                  if (step.remainingInput.isNotEmpty)
                    Text('Remaining ${step.remainingInput}'),
                  if (step.output.isNotEmpty) Text('Output ${step.output}'),
                  Text(step.note),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _DfaTable extends StatelessWidget {
  const _DfaTable({required this.dfa});

  final DfaDefinition dfa;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        headingRowHeight: 44,
        dataRowMinHeight: 42,
        dataRowMaxHeight: 48,
        columns: [
          const DataColumn(label: Text('State')),
          for (final symbol in dfa.alphabet) DataColumn(label: Text(symbol)),
        ],
        rows: [
          for (final state in dfa.states)
            DataRow(
              cells: [
                DataCell(
                  Text(
                    '${state == dfa.startState ? '-> ' : ''}${dfa.acceptStates.contains(state) ? '* ' : ''}$state',
                  ),
                ),
                for (final symbol in dfa.alphabet)
                  DataCell(Text(dfa.transitions[state]?[symbol] ?? '-')),
              ],
            ),
        ],
      ),
    );
  }
}

class StackView extends StatelessWidget {
  const StackView({required this.stack, super.key});

  final List<String> stack;

  @override
  Widget build(BuildContext context) {
    final cells = stack.reversed.toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < math.max(cells.length, 1); i++)
          Container(
            width: 130,
            height: 34,
            alignment: Alignment.center,
            margin: const EdgeInsets.only(bottom: 6),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Theme.of(context).colorScheme.outline),
              color: i == 0
                  ? Theme.of(
                      context,
                    ).colorScheme.primary.withValues(alpha: 0.12)
                  : null,
            ),
            child: Text(cells.isEmpty ? 'empty' : cells[i]),
          ),
      ],
    );
  }
}

class TapeView extends StatelessWidget {
  const TapeView({required this.cells, required this.headIndex, super.key});

  final List<String> cells;
  final int headIndex;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (var i = 0; i < cells.length; i++)
            Container(
              width: 42,
              height: 52,
              alignment: Alignment.center,
              margin: const EdgeInsets.only(right: 6),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: i == headIndex
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(context).colorScheme.outlineVariant,
                  width: i == headIndex ? 2 : 1,
                ),
                color: i == headIndex
                    ? Theme.of(
                        context,
                      ).colorScheme.primary.withValues(alpha: 0.12)
                    : null,
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    cells[i],
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  if (i == headIndex)
                    Icon(
                      Icons.arrow_upward,
                      size: 14,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class FrontierView extends StatelessWidget {
  const FrontierView({required this.symbols, super.key});

  final List<String> symbols;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final symbol in symbols)
          Container(
            width: 48,
            height: 40,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: Theme.of(context).colorScheme.outlineVariant,
              ),
              color: RegExp(r'^[A-Z]').hasMatch(symbol)
                  ? Theme.of(context).colorScheme.tertiaryContainer
                  : Theme.of(context).colorScheme.surfaceContainerHighest,
            ),
            child: Text(symbol),
          ),
      ],
    );
  }
}

class VisualTransition {
  const VisualTransition({
    required this.from,
    required this.to,
    required this.label,
  });

  final String from;
  final String to;
  final String label;
}

class AutomataCanvas extends StatefulWidget {
  const AutomataCanvas({
    required this.states,
    required this.acceptStates,
    required this.startState,
    required this.positions,
    required this.transitions,
    required this.highlightedStates,
    required this.onPositionsChanged,
    this.selectedState,
    this.onStateSelected,
    this.nodeLabels = const {},
    super.key,
  });

  final List<String> states;
  final Set<String> acceptStates;
  final String startState;
  final Map<String, Offset> positions;
  final List<VisualTransition> transitions;
  final Set<String> highlightedStates;
  final ValueChanged<Map<String, Offset>> onPositionsChanged;
  final String? selectedState;
  final ValueChanged<String>? onStateSelected;
  final Map<String, String> nodeLabels;

  @override
  State<AutomataCanvas> createState() => _AutomataCanvasState();
}

class _AutomataCanvasState extends State<AutomataCanvas> {
  String? _draggingState;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final size = Size(constraints.maxWidth, constraints.maxHeight);
        return GestureDetector(
          onTapDown: (details) {
            final state = _hitTest(details.localPosition, size);
            if (state != null) {
              widget.onStateSelected?.call(state);
            }
          },
          onPanStart: (details) {
            _draggingState = _hitTest(details.localPosition, size);
            if (_draggingState != null) {
              widget.onStateSelected?.call(_draggingState!);
            }
          },
          onPanUpdate: (details) {
            final state = _draggingState;
            if (state == null) {
              return;
            }
            final positions = Map<String, Offset>.of(widget.positions);
            positions[state] = Offset(
              (details.localPosition.dx / size.width).clamp(0.08, 0.92),
              (details.localPosition.dy / size.height).clamp(0.12, 0.88),
            );
            widget.onPositionsChanged(positions);
          },
          onPanEnd: (_) => _draggingState = null,
          child: CustomPaint(
            painter: AutomataPainter(
              states: widget.states,
              acceptStates: widget.acceptStates,
              startState: widget.startState,
              positions: widget.positions,
              transitions: widget.transitions,
              highlightedStates: widget.highlightedStates,
              selectedState: widget.selectedState,
              nodeLabels: widget.nodeLabels,
              colorScheme: Theme.of(context).colorScheme,
              textColor: Theme.of(context).colorScheme.onSurface,
            ),
            child: const SizedBox.expand(),
          ),
        );
      },
    );
  }

  String? _hitTest(Offset point, Size size) {
    for (final state in widget.states.reversed) {
      final normalized = widget.positions[state] ?? const Offset(0.5, 0.5);
      final center = Offset(
        normalized.dx * size.width,
        normalized.dy * size.height,
      );
      if ((center - point).distance <= 34) {
        return state;
      }
    }
    return null;
  }
}

class AutomataPainter extends CustomPainter {
  AutomataPainter({
    required this.states,
    required this.acceptStates,
    required this.startState,
    required this.positions,
    required this.transitions,
    required this.highlightedStates,
    required this.selectedState,
    required this.nodeLabels,
    required this.colorScheme,
    required this.textColor,
  });

  final List<String> states;
  final Set<String> acceptStates;
  final String startState;
  final Map<String, Offset> positions;
  final List<VisualTransition> transitions;
  final Set<String> highlightedStates;
  final String? selectedState;
  final Map<String, String> nodeLabels;
  final ColorScheme colorScheme;
  final Color textColor;

  static const radius = 30.0;

  @override
  void paint(Canvas canvas, Size size) {
    final background = Paint()..color = colorScheme.surface;
    canvas.drawRRect(
      RRect.fromRectAndRadius(Offset.zero & size, const Radius.circular(8)),
      background,
    );

    final gridPaint = Paint()
      ..color = colorScheme.outlineVariant.withValues(alpha: 0.35)
      ..strokeWidth = 1;
    for (var x = 32.0; x < size.width; x += 32) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (var y = 32.0; y < size.height; y += 32) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    for (final transition in transitions) {
      _drawTransition(canvas, size, transition);
    }
    _drawStartArrow(canvas, size);
    for (final state in states) {
      _drawState(canvas, size, state);
    }
  }

  void _drawTransition(Canvas canvas, Size size, VisualTransition transition) {
    final from = _point(size, transition.from);
    final to = _point(size, transition.to);
    final paint = Paint()
      ..color = colorScheme.onSurface.withValues(alpha: 0.74)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    if (transition.from == transition.to) {
      final rect = Rect.fromCircle(
        center: from.translate(0, -radius),
        radius: 24,
      );
      canvas.drawArc(rect, math.pi * 0.10, math.pi * 1.75, false, paint);
      _drawArrowHead(
        canvas,
        from.translate(22, -radius + 14),
        -0.35,
        paint.color,
      );
      _drawLabel(canvas, transition.label, from.translate(0, -72));
      return;
    }

    final direction = to - from;
    final distance = direction.distance;
    if (distance == 0) {
      return;
    }
    final unit = direction / distance;
    final start = from + unit * radius;
    final end = to - unit * radius;
    final normal = Offset(-unit.dy, unit.dx);
    final curve = normal * math.min(46, distance * 0.22);
    final control = Offset.lerp(start, end, 0.5)! + curve;
    final path = Path()
      ..moveTo(start.dx, start.dy)
      ..quadraticBezierTo(control.dx, control.dy, end.dx, end.dy);
    canvas.drawPath(path, paint);
    final tangent = (end - control);
    _drawArrowHead(
      canvas,
      end,
      math.atan2(tangent.dy, tangent.dx),
      paint.color,
    );
    _drawLabel(canvas, transition.label, control);
  }

  void _drawStartArrow(Canvas canvas, Size size) {
    if (!states.contains(startState)) {
      return;
    }
    final center = _point(size, startState);
    final start = center.translate(-76, 0);
    final end = center.translate(-radius, 0);
    final paint = Paint()
      ..color = colorScheme.primary
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;
    canvas.drawLine(start, end, paint);
    _drawArrowHead(canvas, end, 0, colorScheme.primary);
  }

  void _drawState(Canvas canvas, Size size, String state) {
    final center = _point(size, state);
    final highlighted = highlightedStates.contains(state);
    final selected = selectedState == state;
    final fill = Paint()
      ..color = highlighted
          ? colorScheme.primaryContainer
          : selected
          ? colorScheme.secondaryContainer
          : colorScheme.surface;
    final border = Paint()
      ..color = highlighted
          ? colorScheme.primary
          : selected
          ? colorScheme.secondary
          : colorScheme.onSurface
      ..strokeWidth = highlighted || selected ? 3 : 2
      ..style = PaintingStyle.stroke;

    canvas.drawCircle(center, radius, fill);
    canvas.drawCircle(center, radius, border);
    if (acceptStates.contains(state)) {
      canvas.drawCircle(center, radius - 6, border..strokeWidth = 1.5);
    }

    final label = nodeLabels[state] == null
        ? state
        : '$state/${nodeLabels[state]}';
    _drawText(canvas, label, center, maxWidth: 84, align: TextAlign.center);
  }

  void _drawArrowHead(Canvas canvas, Offset tip, double angle, Color color) {
    const arrowLength = 12.0;
    const spread = 0.48;
    final path = Path()
      ..moveTo(tip.dx, tip.dy)
      ..lineTo(
        tip.dx - arrowLength * math.cos(angle - spread),
        tip.dy - arrowLength * math.sin(angle - spread),
      )
      ..moveTo(tip.dx, tip.dy)
      ..lineTo(
        tip.dx - arrowLength * math.cos(angle + spread),
        tip.dy - arrowLength * math.sin(angle + spread),
      );
    canvas.drawPath(
      path,
      Paint()
        ..color = color
        ..strokeWidth = 2
        ..style = PaintingStyle.stroke,
    );
  }

  void _drawLabel(Canvas canvas, String label, Offset center) {
    final painter = TextPainter(
      text: TextSpan(
        text: label,
        style: TextStyle(
          color: textColor,
          fontSize: 12,
          fontWeight: FontWeight.w700,
        ),
      ),
      textAlign: TextAlign.center,
      textDirection: TextDirection.ltr,
      maxLines: 2,
      ellipsis: '...',
    )..layout(maxWidth: 120);
    final rect = Rect.fromCenter(
      center: center,
      width: painter.width + 12,
      height: painter.height + 6,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(6)),
      Paint()..color = colorScheme.surface.withValues(alpha: 0.94),
    );
    painter.paint(canvas, rect.topLeft + const Offset(6, 3));
  }

  void _drawText(
    Canvas canvas,
    String text,
    Offset center, {
    double maxWidth = 72,
    TextAlign align = TextAlign.center,
  }) {
    final painter = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          color: textColor,
          fontSize: 13,
          fontWeight: FontWeight.w800,
        ),
      ),
      textAlign: align,
      textDirection: TextDirection.ltr,
      maxLines: 2,
      ellipsis: '...',
    )..layout(maxWidth: maxWidth);
    painter.paint(
      canvas,
      center - Offset(painter.width / 2, painter.height / 2),
    );
  }

  Offset _point(Size size, String state) {
    final normalized = positions[state] ?? const Offset(0.5, 0.5);
    return Offset(normalized.dx * size.width, normalized.dy * size.height);
  }

  @override
  bool shouldRepaint(covariant AutomataPainter oldDelegate) {
    return oldDelegate.positions != positions ||
        oldDelegate.highlightedStates != highlightedStates ||
        oldDelegate.selectedState != selectedState ||
        oldDelegate.transitions != transitions ||
        oldDelegate.colorScheme != colorScheme;
  }
}

List<VisualTransition> _dfaTransitions(DfaDefinition dfa) {
  final grouped = <String, List<String>>{};
  for (final from in dfa.transitions.entries) {
    for (final transition in from.value.entries) {
      grouped
          .putIfAbsent('${from.key}->${transition.value}', () => [])
          .add(transition.key);
    }
  }
  return grouped.entries.map((entry) {
    final parts = entry.key.split('->');
    return VisualTransition(
      from: parts[0],
      to: parts[1],
      label: entry.value.join(', '),
    );
  }).toList();
}

List<VisualTransition> _nfaTransitions(NfaDefinition nfa) {
  final grouped = <String, List<String>>{};
  for (final from in nfa.transitions.entries) {
    for (final transition in from.value.entries) {
      for (final target in transition.value) {
        grouped
            .putIfAbsent('${from.key}->$target', () => [])
            .add(transition.key);
      }
    }
  }
  return grouped.entries.map((entry) {
    final parts = entry.key.split('->');
    return VisualTransition(
      from: parts[0],
      to: parts[1],
      label: entry.value.join(', '),
    );
  }).toList();
}

List<VisualTransition> _mooreTransitions(MooreDefinition machine) {
  final grouped = <String, List<String>>{};
  for (final from in machine.transitions.entries) {
    for (final transition in from.value.entries) {
      grouped
          .putIfAbsent('${from.key}->${transition.value}', () => [])
          .add(transition.key);
    }
  }
  return grouped.entries.map((entry) {
    final parts = entry.key.split('->');
    return VisualTransition(
      from: parts[0],
      to: parts[1],
      label: entry.value.join(', '),
    );
  }).toList();
}

List<VisualTransition> _mealyTransitions(MealyDefinition machine) {
  final transitions = <VisualTransition>[];
  for (final from in machine.transitions.entries) {
    for (final transition in from.value.entries) {
      transitions.add(
        VisualTransition(
          from: from.key,
          to: transition.value.nextState,
          label: '${transition.key}/${transition.value.output}',
        ),
      );
    }
  }
  return transitions;
}

List<VisualTransition> _pdaTransitions(PdaDefinition pda) {
  return [
    for (final transition in pda.transitions)
      VisualTransition(
        from: transition.from,
        to: transition.to,
        label: transition.label,
      ),
  ];
}

List<VisualTransition> _tmTransitions(TuringMachineDefinition tm) {
  return [
    for (final transition in tm.transitions)
      VisualTransition(
        from: transition.from,
        to: transition.to,
        label: transition.label,
      ),
  ];
}

Map<String, Offset> _defaultPositions(List<String> states) {
  if (states.isEmpty) {
    return {};
  }
  final positions = <String, Offset>{};
  for (var i = 0; i < states.length; i++) {
    final angle = -math.pi / 2 + (2 * math.pi * i / states.length);
    positions[states[i]] = Offset(
      0.5 + math.cos(angle) * 0.32,
      0.5 + math.sin(angle) * 0.30,
    );
  }
  return positions;
}

Map<String, Map<String, String>> _cloneDfaTransitions(DfaDefinition dfa) {
  return {
    for (final entry in dfa.transitions.entries)
      entry.key: Map<String, String>.of(entry.value),
  };
}

String _formText(List<String> form) {
  if (form.isEmpty) {
    return AutomataSymbols.epsilon;
  }
  return form.join(' ');
}
