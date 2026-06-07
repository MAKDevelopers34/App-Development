import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'cnf_converter.dart';

void main() {
  runApp(const CfgCnfApp());
}

const _ink = Color(0xFF17212B);
const _paper = Color(0xFFF8F4EC);
const _surface = Color(0xFFFFFCF7);
const _border = Color(0xFFE4D9C8);
const _teal = Color(0xFF0F766E);
const _coral = Color(0xFFBE4B49);
const _gold = Color(0xFFC58B27);
const _mono = 'Consolas';

const _defaultGrammar = '''
S -> A B | B C
A -> B A | a
B -> C C | b
C -> A B | a
''';

const _examples = [
  ExampleGrammar('Classic', _defaultGrammar),
  ExampleGrammar('Epsilon', '''
S -> A B
A -> a | epsilon
B -> b | epsilon
'''),
  ExampleGrammar('Unit Rules', '''
S -> A | a b
A -> B
B -> c
'''),
  ExampleGrammar('Long RHS', '''
S -> a b c d
A -> B C D
B -> b
C -> c
D -> d
'''),
  ExampleGrammar('Start on RHS', '''
S -> A S | b
A -> a | epsilon
'''),
];

class ExampleGrammar {
  const ExampleGrammar(this.name, this.grammar);

  final String name;
  final String grammar;
}

class CfgCnfApp extends StatelessWidget {
  const CfgCnfApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CFG to CNF Converter',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: _paper,
        colorScheme: ColorScheme.fromSeed(
          seedColor: _teal,
          brightness: Brightness.light,
          surface: _surface,
        ),
        textTheme: const TextTheme(
          headlineSmall: TextStyle(fontWeight: FontWeight.w800, color: _ink),
          titleMedium: TextStyle(fontWeight: FontWeight.w800, color: _ink),
          bodyMedium: TextStyle(color: _ink, height: 1.35),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: _border),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: _border),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: _teal, width: 1.6),
          ),
        ),
      ),
      home: const ConverterScreen(),
    );
  }
}

class ConverterScreen extends StatefulWidget {
  const ConverterScreen({super.key});

  @override
  State<ConverterScreen> createState() => _ConverterScreenState();
}

class _ConverterScreenState extends State<ConverterScreen> {
  late final TextEditingController _controller;
  late ConversionResult _result;
  final Set<int> _expandedSteps = {5};

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: _defaultGrammar.trim());
    _result = convertCfgToCnf(_controller.text);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _convert() {
    final result = convertCfgToCnf(_controller.text);
    setState(() {
      _result = result;
      _expandedSteps
        ..clear()
        ..add(result.steps.isEmpty ? 0 : result.steps.length - 1);
    });
  }

  void _loadExample(ExampleGrammar example) {
    _controller.text = example.grammar.trim();
    _convert();
  }

  void _clear() {
    _controller.clear();
    setState(() {
      _result = convertCfgToCnf('');
      _expandedSteps.clear();
    });
  }

  Future<void> _copyFinalGrammar() async {
    if (_result.finalRules.isEmpty) {
      return;
    }

    await Clipboard.setData(ClipboardData(text: _result.finalRules));
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Final CNF grammar copied')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SelectionArea(
        child: SingleChildScrollView(
          child: Column(
            children: [
              _Header(result: _result),
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 18, 18, 28),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1240),
                    child: LayoutBuilder(
                      builder: (context, constraints) {
                        final wide = constraints.maxWidth >= 980;
                        final editor = _EditorPanel(
                          controller: _controller,
                          onConvert: _convert,
                          onClear: _clear,
                          onExampleSelected: _loadExample,
                        );
                        final summary = _SummaryPanel(result: _result);

                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            if (wide)
                              IntrinsicHeight(
                                child: Row(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: [
                                    Expanded(flex: 6, child: editor),
                                    const SizedBox(width: 16),
                                    Expanded(flex: 4, child: summary),
                                  ],
                                ),
                              )
                            else ...[
                              editor,
                              const SizedBox(height: 14),
                              summary,
                            ],
                            const SizedBox(height: 16),
                            _ResultsPanel(
                              result: _result,
                              expandedSteps: _expandedSteps,
                              onStepToggled: (index, open) {
                                setState(() {
                                  if (open) {
                                    _expandedSteps.add(index);
                                  } else {
                                    _expandedSteps.remove(index);
                                  }
                                });
                              },
                              onCopyFinal: _copyFinalGrammar,
                            ),
                          ],
                        );
                      },
                    ),
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

class _Header extends StatelessWidget {
  const _Header({required this.result});

  final ConversionResult result;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: _ink,
      padding: const EdgeInsets.fromLTRB(18, 22, 18, 18),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1240),
          child: Wrap(
            runSpacing: 16,
            spacing: 16,
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 620),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.schema_rounded, color: Color(0xFF8FD6CB)),
                        SizedBox(width: 10),
                        Flexible(
                          child: Text(
                            'CFG to CNF Converter',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 28,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 6),
                    Text(
                      'Theory of Automata assignment workspace',
                      style: TextStyle(color: Color(0xFFC9D4D1), fontSize: 14),
                    ),
                  ],
                ),
              ),
              if (!result.hasError)
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    _HeaderPill(
                      icon: Icons.account_tree_rounded,
                      label: '${result.metrics.variables} variables',
                    ),
                    _HeaderPill(
                      icon: Icons.functions_rounded,
                      label: '${result.metrics.productions} productions',
                    ),
                    _HeaderPill(
                      icon: result.isValidCnf
                          ? Icons.verified_rounded
                          : Icons.warning_rounded,
                      label: result.isValidCnf
                          ? 'CNF verified'
                          : 'Needs review',
                      color: result.isValidCnf ? _teal : _coral,
                    ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HeaderPill extends StatelessWidget {
  const _HeaderPill({
    required this.icon,
    required this.label,
    this.color = _gold,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _EditorPanel extends StatelessWidget {
  const _EditorPanel({
    required this.controller,
    required this.onConvert,
    required this.onClear,
    required this.onExampleSelected,
  });

  final TextEditingController controller;
  final VoidCallback onConvert;
  final VoidCallback onClear;
  final ValueChanged<ExampleGrammar> onExampleSelected;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      title: 'Grammar Editor',
      icon: Icons.edit_note_rounded,
      accent: _teal,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: controller,
            minLines: 12,
            maxLines: 18,
            autocorrect: false,
            enableSuggestions: false,
            style: const TextStyle(
              fontFamily: _mono,
              fontSize: 15,
              height: 1.45,
              color: _ink,
            ),
            decoration: const InputDecoration(
              hintText: 'S -> A B | a\nA -> epsilon | b',
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final example in _examples)
                ActionChip(
                  avatar: const Icon(
                    Icons.auto_awesome_motion_rounded,
                    size: 17,
                  ),
                  label: Text(example.name),
                  onPressed: () => onExampleSelected(example),
                  visualDensity: VisualDensity.compact,
                ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            alignment: WrapAlignment.end,
            spacing: 10,
            runSpacing: 10,
            children: [
              OutlinedButton.icon(
                onPressed: onClear,
                icon: const Icon(Icons.delete_outline_rounded),
                label: const Text('Clear'),
              ),
              FilledButton.icon(
                onPressed: onConvert,
                icon: const Icon(Icons.play_arrow_rounded),
                label: const Text('Convert'),
                style: FilledButton.styleFrom(
                  backgroundColor: _teal,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 18,
                    vertical: 13,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SummaryPanel extends StatelessWidget {
  const _SummaryPanel({required this.result});

  final ConversionResult result;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      title: 'Conversion Pipeline',
      icon: Icons.route_rounded,
      accent: _gold,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (!result.hasError) ...[
            Row(
              children: [
                Expanded(
                  child: _MetricBox(
                    label: 'Variables',
                    value: '${result.metrics.variables}',
                    icon: Icons.hub_rounded,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _MetricBox(
                    label: 'Terminals',
                    value: '${result.metrics.terminals}',
                    icon: Icons.text_fields_rounded,
                    color: _coral,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            _MetricBox(
              label: 'Final productions',
              value: '${result.metrics.productions}',
              icon: Icons.rule_rounded,
              color: _teal,
              wide: true,
            ),
            const SizedBox(height: 18),
          ],
          ...const [
            _PipelineRow('1', 'Protect start symbol', Icons.flag_rounded),
            _PipelineRow('2', 'Remove epsilon rules', Icons.filter_alt_rounded),
            _PipelineRow('3', 'Remove unit rules', Icons.link_off_rounded),
            _PipelineRow('4', 'Make binary rules', Icons.call_split_rounded),
            _PipelineRow(
              '5',
              'Replace mixed terminals',
              Icons.swap_horiz_rounded,
            ),
          ],
        ],
      ),
    );
  }
}

class _ResultsPanel extends StatelessWidget {
  const _ResultsPanel({
    required this.result,
    required this.expandedSteps,
    required this.onStepToggled,
    required this.onCopyFinal,
  });

  final ConversionResult result;
  final Set<int> expandedSteps;
  final void Function(int index, bool open) onStepToggled;
  final VoidCallback onCopyFinal;

  @override
  Widget build(BuildContext context) {
    if (result.hasError) {
      return _Panel(
        title: 'Input Check',
        icon: Icons.error_outline_rounded,
        accent: _coral,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.warning_amber_rounded, color: _coral),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                result.error!,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
          ],
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 980;
        final finalPanel = _FinalGrammarPanel(
          result: result,
          onCopy: onCopyFinal,
        );
        final stepsPanel = _StepTimelinePanel(
          steps: result.steps,
          expandedSteps: expandedSteps,
          onStepToggled: onStepToggled,
        );

        if (wide) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 4, child: finalPanel),
              const SizedBox(width: 16),
              Expanded(flex: 6, child: stepsPanel),
            ],
          );
        }

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [finalPanel, const SizedBox(height: 14), stepsPanel],
        );
      },
    );
  }
}

class _FinalGrammarPanel extends StatelessWidget {
  const _FinalGrammarPanel({required this.result, required this.onCopy});

  final ConversionResult result;
  final VoidCallback onCopy;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      title: 'Final CNF Grammar',
      icon: Icons.verified_rounded,
      accent: result.isValidCnf ? _teal : _coral,
      trailing: IconButton(
        tooltip: 'Copy final grammar',
        onPressed: onCopy,
        icon: const Icon(Icons.copy_rounded),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _StatusStrip(result: result),
          const SizedBox(height: 12),
          _GrammarBlock(text: result.finalRules),
          if (result.invalidRules.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              result.invalidRules.join('\n'),
              style: const TextStyle(
                color: _coral,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _StepTimelinePanel extends StatelessWidget {
  const _StepTimelinePanel({
    required this.steps,
    required this.expandedSteps,
    required this.onStepToggled,
  });

  final List<ConversionStep> steps;
  final Set<int> expandedSteps;
  final void Function(int index, bool open) onStepToggled;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      title: 'Step Trace',
      icon: Icons.timeline_rounded,
      accent: _coral,
      child: Column(
        children: [
          for (var index = 0; index < steps.length; index++) ...[
            _StepTile(
              step: steps[index],
              expanded: expandedSteps.contains(index),
              onExpansionChanged: (open) => onStepToggled(index, open),
            ),
            if (index != steps.length - 1) const SizedBox(height: 9),
          ],
        ],
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({
    required this.title,
    required this.icon,
    required this.accent,
    required this.child,
    this.trailing,
  });

  final String title;
  final IconData icon;
  final Color accent;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, color: accent, size: 20),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              ...?(trailing == null ? null : [trailing!]),
            ],
          ),
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }
}

class _MetricBox extends StatelessWidget {
  const _MetricBox({
    required this.label,
    required this.value,
    required this.icon,
    this.color = _gold,
    this.wide = false,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color color;
  final bool wide;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      child: Row(
        mainAxisSize: wide ? MainAxisSize.max : MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 21),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              label,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 20,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _PipelineRow extends StatelessWidget {
  const _PipelineRow(this.number, this.label, this.icon);

  final String number;
  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: _ink,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              number,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Icon(icon, color: _teal, size: 20),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusStrip extends StatelessWidget {
  const _StatusStrip({required this.result});

  final ConversionResult result;

  @override
  Widget build(BuildContext context) {
    final color = result.isValidCnf ? _teal : _coral;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.09),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Icon(
            result.isValidCnf
                ? Icons.check_circle_rounded
                : Icons.report_rounded,
            color: color,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              result.isValidCnf
                  ? 'Every production matches CNF form.'
                  : 'Some productions need review.',
              style: TextStyle(color: color, fontWeight: FontWeight.w800),
            ),
          ),
        ],
      ),
    );
  }
}

class _StepTile extends StatelessWidget {
  const _StepTile({
    required this.step,
    required this.expanded,
    required this.onExpansionChanged,
  });

  final ConversionStep step;
  final bool expanded;
  final ValueChanged<bool> onExpansionChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: expanded ? _teal.withValues(alpha: 0.5) : _border,
        ),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: expanded,
          maintainState: true,
          onExpansionChanged: onExpansionChanged,
          tilePadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
          childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
          leading: Container(
            width: 46,
            height: 28,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: _ink,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              step.badge.replaceAll('Step ', ''),
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
                fontSize: 12,
              ),
            ),
          ),
          title: Text(
            step.title,
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final note in step.notes)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.arrow_right_rounded,
                          color: _gold,
                          size: 19,
                        ),
                        const SizedBox(width: 4),
                        Expanded(child: Text(note)),
                      ],
                    ),
                  ),
                const SizedBox(height: 4),
                _GrammarBlock(text: step.grammar),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _GrammarBlock extends StatelessWidget {
  const _GrammarBlock({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: const Color(0xFF111820),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF26313D)),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: SelectableText(
          text,
          style: const TextStyle(
            color: Color(0xFFF4F7F6),
            fontFamily: _mono,
            fontSize: 14,
            height: 1.55,
          ),
        ),
      ),
    );
  }
}
