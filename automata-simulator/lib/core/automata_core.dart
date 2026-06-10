import 'dart:collection';
import 'dart:convert';

class AutomataSymbols {
  static const epsilon = 'eps';
  static const blank = '_';
  static const stackBottom = 'Z0';
}

class SimulationStep {
  const SimulationStep({
    required this.index,
    required this.state,
    this.symbol = '',
    this.remainingInput = '',
    this.note = '',
    this.accepting = false,
    this.activeStates = const [],
    this.stack = const [],
    this.tapeWindow = const [],
    this.headIndex = 0,
    this.output = '',
  });

  final int index;
  final String state;
  final String symbol;
  final String remainingInput;
  final String note;
  final bool accepting;
  final List<String> activeStates;
  final List<String> stack;
  final List<String> tapeWindow;
  final int headIndex;
  final String output;
}

class SimulationResult {
  const SimulationResult({
    required this.accepted,
    required this.steps,
    this.halted = true,
    this.limitHit = false,
    this.output = '',
    this.summary = '',
  });

  final bool accepted;
  final bool halted;
  final bool limitHit;
  final String output;
  final String summary;
  final List<SimulationStep> steps;
}

class DfaDefinition {
  const DfaDefinition({
    required this.states,
    required this.alphabet,
    required this.startState,
    required this.acceptStates,
    required this.transitions,
  });

  final List<String> states;
  final List<String> alphabet;
  final String startState;
  final Set<String> acceptStates;
  final Map<String, Map<String, String>> transitions;

  SimulationResult run(String input) {
    final steps = <SimulationStep>[];
    var current = startState;

    steps.add(
      SimulationStep(
        index: 0,
        state: current,
        remainingInput: input,
        accepting: acceptStates.contains(current),
        activeStates: [current],
        note: 'Start at $current',
      ),
    );

    for (var i = 0; i < input.length; i++) {
      final symbol = input[i];
      final next = transitions[current]?[symbol];
      if (next == null) {
        steps.add(
          SimulationStep(
            index: i + 1,
            state: current,
            symbol: symbol,
            remainingInput: input.substring(i + 1),
            activeStates: [current],
            note: 'No transition from $current on $symbol',
          ),
        );
        return SimulationResult(
          accepted: false,
          steps: steps,
          summary: 'Rejected: missing transition.',
        );
      }

      current = next;
      steps.add(
        SimulationStep(
          index: i + 1,
          state: current,
          symbol: symbol,
          remainingInput: input.substring(i + 1),
          accepting: acceptStates.contains(current),
          activeStates: [current],
          note: 'Read $symbol, moved to $current',
        ),
      );
    }

    final accepted = acceptStates.contains(current);
    return SimulationResult(
      accepted: accepted,
      steps: steps,
      summary: accepted ? 'Accepted in $current.' : 'Rejected in $current.',
    );
  }

  DfaDefinition minimize() {
    final reachable = _reachableStates();
    var partitions = <Set<String>>[
      reachable.where(acceptStates.contains).toSet(),
      reachable.where((state) => !acceptStates.contains(state)).toSet(),
    ].where((part) => part.isNotEmpty).toList();

    var changed = true;
    while (changed) {
      changed = false;
      final nextPartitions = <Set<String>>[];
      for (final partition in partitions) {
        final buckets = <String, Set<String>>{};
        for (final state in partition) {
          final signature = alphabet
              .map(
                (symbol) =>
                    _partitionIndex(partitions, transitions[state]?[symbol]),
              )
              .join(',');
          buckets.putIfAbsent(signature, () => <String>{}).add(state);
        }
        nextPartitions.addAll(buckets.values);
        if (buckets.length > 1) {
          changed = true;
        }
      }
      partitions = nextPartitions;
    }

    final representativeName = <String, String>{};
    for (final partition in partitions) {
      final name = partition.toList()..sort();
      final mergedName = name.join('/');
      for (final state in partition) {
        representativeName[state] = mergedName;
      }
    }

    final minimizedTransitions = <String, Map<String, String>>{};
    for (final partition in partitions) {
      final sorted = partition.toList()..sort();
      final representative = sorted.first;
      final mergedName = representativeName[representative]!;
      minimizedTransitions[mergedName] = {
        for (final symbol in alphabet)
          if (transitions[representative]?[symbol] != null)
            symbol: representativeName[transitions[representative]![symbol]!]!,
      };
    }

    final minimizedStates = representativeName.values.toSet().toList()..sort();
    return DfaDefinition(
      states: minimizedStates,
      alphabet: List.of(alphabet),
      startState: representativeName[startState]!,
      acceptStates: acceptStates
          .map((state) => representativeName[state])
          .whereType<String>()
          .toSet(),
      transitions: minimizedTransitions,
    );
  }

  Set<String> _reachableStates() {
    final visited = <String>{startState};
    final queue = Queue<String>()..add(startState);
    while (queue.isNotEmpty) {
      final state = queue.removeFirst();
      for (final next in transitions[state]?.values ?? const <String>[]) {
        if (visited.add(next)) {
          queue.add(next);
        }
      }
    }
    return visited;
  }

  int _partitionIndex(List<Set<String>> partitions, String? state) {
    if (state == null) {
      return -1;
    }
    return partitions.indexWhere((partition) => partition.contains(state));
  }

  Map<String, dynamic> toJson() {
    return {
      'type': 'dfa',
      'states': states,
      'alphabet': alphabet,
      'startState': startState,
      'acceptStates': acceptStates.toList()..sort(),
      'transitions': transitions,
    };
  }

  String toPrettyJson() {
    return const JsonEncoder.withIndent('  ').convert(toJson());
  }

  factory DfaDefinition.fromJson(Map<String, dynamic> json) {
    final rawTransitions = json['transitions'] as Map<String, dynamic>;
    return DfaDefinition(
      states: (json['states'] as List).cast<String>(),
      alphabet: (json['alphabet'] as List).cast<String>(),
      startState: json['startState'] as String,
      acceptStates: (json['acceptStates'] as List).cast<String>().toSet(),
      transitions: rawTransitions.map(
        (state, table) => MapEntry(
          state,
          (table as Map<String, dynamic>).map(
            (symbol, target) => MapEntry(symbol, target as String),
          ),
        ),
      ),
    );
  }
}

class NfaDefinition {
  const NfaDefinition({
    required this.states,
    required this.alphabet,
    required this.startState,
    required this.acceptStates,
    required this.transitions,
  });

  final List<String> states;
  final List<String> alphabet;
  final String startState;
  final Set<String> acceptStates;
  final Map<String, Map<String, Set<String>>> transitions;

  Set<String> epsilonClosure(Set<String> sourceStates) {
    final closure = <String>{...sourceStates};
    final queue = Queue<String>()..addAll(sourceStates);
    while (queue.isNotEmpty) {
      final state = queue.removeFirst();
      for (final next
          in transitions[state]?[AutomataSymbols.epsilon] ?? <String>{}) {
        if (closure.add(next)) {
          queue.add(next);
        }
      }
    }
    return closure;
  }

  Set<String> move(Set<String> sourceStates, String symbol) {
    final moved = <String>{};
    for (final state in sourceStates) {
      moved.addAll(transitions[state]?[symbol] ?? <String>{});
    }
    return moved;
  }

  SimulationResult run(String input) {
    final steps = <SimulationStep>[];
    var active = epsilonClosure({startState});
    steps.add(
      SimulationStep(
        index: 0,
        state: _setName(active),
        remainingInput: input,
        activeStates: _sorted(active),
        accepting: active.any(acceptStates.contains),
        note: 'epsilon-closure($startState) = ${_setName(active)}',
      ),
    );

    for (var i = 0; i < input.length; i++) {
      final symbol = input[i];
      final moved = move(active, symbol);
      active = epsilonClosure(moved);
      steps.add(
        SimulationStep(
          index: i + 1,
          state: _setName(active),
          symbol: symbol,
          remainingInput: input.substring(i + 1),
          activeStates: _sorted(active),
          accepting: active.any(acceptStates.contains),
          note: 'move on $symbol then epsilon-closure',
        ),
      );
    }

    final accepted = active.any(acceptStates.contains);
    return SimulationResult(
      accepted: accepted,
      steps: steps,
      summary: accepted
          ? 'Accepted by ${_setName(active)}.'
          : 'Rejected by ${_setName(active)}.',
    );
  }

  DfaDefinition toDfa() {
    final dfaTransitions = <String, Map<String, String>>{};
    final dfaStates = <String>{};
    final dfaAcceptStates = <String>{};
    final startSet = epsilonClosure({startState});
    final startName = _setName(startSet);
    final queue = Queue<Set<String>>()..add(startSet);
    final seen = <String>{startName};

    while (queue.isNotEmpty) {
      final currentSet = queue.removeFirst();
      final currentName = _setName(currentSet);
      dfaStates.add(currentName);
      if (currentSet.any(acceptStates.contains)) {
        dfaAcceptStates.add(currentName);
      }

      final table = <String, String>{};
      for (final symbol in alphabet.where(
        (item) => item != AutomataSymbols.epsilon,
      )) {
        final nextSet = epsilonClosure(move(currentSet, symbol));
        final nextName = _setName(nextSet);
        table[symbol] = nextName;
        if (seen.add(nextName)) {
          queue.add(nextSet);
        }
      }
      dfaTransitions[currentName] = table;
    }

    return DfaDefinition(
      states: dfaStates.toList()..sort(),
      alphabet: alphabet
          .where((item) => item != AutomataSymbols.epsilon)
          .toList(),
      startState: startName,
      acceptStates: dfaAcceptStates,
      transitions: dfaTransitions,
    );
  }
}

class MooreDefinition {
  const MooreDefinition({
    required this.states,
    required this.alphabet,
    required this.startState,
    required this.outputs,
    required this.transitions,
  });

  final List<String> states;
  final List<String> alphabet;
  final String startState;
  final Map<String, String> outputs;
  final Map<String, Map<String, String>> transitions;

  SimulationResult run(String input) {
    final steps = <SimulationStep>[];
    var current = startState;
    final buffer = StringBuffer(outputs[current] ?? '');
    steps.add(
      SimulationStep(
        index: 0,
        state: current,
        remainingInput: input,
        activeStates: [current],
        output: buffer.toString(),
        note: 'Output ${outputs[current] ?? ''} from $current',
      ),
    );

    for (var i = 0; i < input.length; i++) {
      final symbol = input[i];
      final next = transitions[current]?[symbol];
      if (next == null) {
        return SimulationResult(
          accepted: false,
          steps: steps,
          halted: true,
          output: buffer.toString(),
          summary: 'Stopped: missing transition from $current on $symbol.',
        );
      }
      current = next;
      buffer.write(outputs[current] ?? '');
      steps.add(
        SimulationStep(
          index: i + 1,
          state: current,
          symbol: symbol,
          remainingInput: input.substring(i + 1),
          activeStates: [current],
          output: buffer.toString(),
          note: 'Read $symbol, output ${outputs[current] ?? ''}',
        ),
      );
    }

    return SimulationResult(
      accepted: true,
      steps: steps,
      output: buffer.toString(),
      summary: 'Produced ${buffer.toString()}.',
    );
  }
}

class MealyMove {
  const MealyMove(this.nextState, this.output);

  final String nextState;
  final String output;
}

class MealyDefinition {
  const MealyDefinition({
    required this.states,
    required this.alphabet,
    required this.startState,
    required this.transitions,
  });

  final List<String> states;
  final List<String> alphabet;
  final String startState;
  final Map<String, Map<String, MealyMove>> transitions;

  SimulationResult run(String input) {
    final steps = <SimulationStep>[];
    var current = startState;
    final buffer = StringBuffer();
    steps.add(
      SimulationStep(
        index: 0,
        state: current,
        remainingInput: input,
        activeStates: [current],
        output: '',
        note: 'Start at $current',
      ),
    );

    for (var i = 0; i < input.length; i++) {
      final symbol = input[i];
      final move = transitions[current]?[symbol];
      if (move == null) {
        return SimulationResult(
          accepted: false,
          steps: steps,
          halted: true,
          output: buffer.toString(),
          summary: 'Stopped: missing transition from $current on $symbol.',
        );
      }
      current = move.nextState;
      buffer.write(move.output);
      steps.add(
        SimulationStep(
          index: i + 1,
          state: current,
          symbol: symbol,
          remainingInput: input.substring(i + 1),
          activeStates: [current],
          output: buffer.toString(),
          note: 'Read $symbol, emitted ${move.output}',
        ),
      );
    }

    return SimulationResult(
      accepted: true,
      steps: steps,
      output: buffer.toString(),
      summary: 'Produced ${buffer.toString()}.',
    );
  }
}

class PdaTransition {
  const PdaTransition({
    required this.from,
    required this.to,
    this.inputSymbol,
    this.stackTop,
    this.pushSymbols = const [],
  });

  final String from;
  final String to;
  final String? inputSymbol;
  final String? stackTop;
  final List<String> pushSymbols;

  String get label {
    final input = inputSymbol ?? AutomataSymbols.epsilon;
    final pop = stackTop ?? AutomataSymbols.epsilon;
    final push = pushSymbols.isEmpty
        ? AutomataSymbols.epsilon
        : pushSymbols.join('');
    return '$input, $pop -> $push';
  }
}

class PdaDefinition {
  const PdaDefinition({
    required this.states,
    required this.inputAlphabet,
    required this.stackAlphabet,
    required this.startState,
    required this.acceptStates,
    required this.transitions,
    this.acceptByEmptyStack = false,
  });

  final List<String> states;
  final List<String> inputAlphabet;
  final List<String> stackAlphabet;
  final String startState;
  final Set<String> acceptStates;
  final List<PdaTransition> transitions;
  final bool acceptByEmptyStack;

  SimulationResult run(String input, {int maxSteps = 200}) {
    final steps = <SimulationStep>[];
    var current = startState;
    var index = 0;
    final stack = <String>[AutomataSymbols.stackBottom];

    steps.add(
      SimulationStep(
        index: 0,
        state: current,
        remainingInput: input,
        activeStates: [current],
        stack: List.of(stack),
        note: 'Initial stack ${stack.join(', ')}',
      ),
    );

    for (var step = 1; step <= maxSteps; step++) {
      final inputSymbol = index < input.length ? input[index] : null;
      final top = stack.isNotEmpty ? stack.last : null;
      final transition = transitions.cast<PdaTransition?>().firstWhere(
        (candidate) =>
            candidate!.from == current &&
            (candidate.inputSymbol == null ||
                candidate.inputSymbol == inputSymbol) &&
            (candidate.stackTop == null || candidate.stackTop == top),
        orElse: () => null,
      );

      final acceptedByState =
          index == input.length && acceptStates.contains(current);
      final acceptedByEmpty =
          index == input.length && acceptByEmptyStack && stack.isEmpty;
      if (transition == null) {
        final accepted = acceptedByState || acceptedByEmpty;
        return SimulationResult(
          accepted: accepted,
          steps: steps,
          summary: accepted
              ? 'Accepted.'
              : 'Rejected: no available PDA transition.',
        );
      }

      if (transition.inputSymbol != null) {
        index++;
      }
      if (transition.stackTop != null && stack.isNotEmpty) {
        stack.removeLast();
      }
      for (final symbol in transition.pushSymbols) {
        stack.add(symbol);
      }
      current = transition.to;

      steps.add(
        SimulationStep(
          index: step,
          state: current,
          symbol: transition.inputSymbol ?? AutomataSymbols.epsilon,
          remainingInput: input.substring(index),
          activeStates: [current],
          stack: List.of(stack),
          accepting: index == input.length && acceptStates.contains(current),
          note: transition.label,
        ),
      );
    }

    return SimulationResult(
      accepted: false,
      halted: false,
      limitHit: true,
      steps: steps,
      summary: 'Stopped after $maxSteps PDA steps.',
    );
  }
}

class CfgProduction {
  const CfgProduction(this.left, this.right);

  final String left;
  final List<String> right;

  @override
  String toString() =>
      '$left -> ${right.isEmpty ? AutomataSymbols.epsilon : right.join(' ')}';
}

class CfgDefinition {
  const CfgDefinition({required this.startSymbol, required this.productions});

  final String startSymbol;
  final List<CfgProduction> productions;

  static CfgDefinition parse(String source, {String startSymbol = 'S'}) {
    final productions = <CfgProduction>[];
    for (final rawLine in const LineSplitter().convert(source)) {
      final line = rawLine.trim();
      if (line.isEmpty || line.startsWith('#')) {
        continue;
      }
      final pieces = line.split(RegExp(r'\s*->\s*'));
      if (pieces.length != 2) {
        continue;
      }
      final left = pieces.first.trim();
      for (final alternative in pieces.last.split('|')) {
        final body = alternative.trim();
        final symbols = body == AutomataSymbols.epsilon || body.isEmpty
            ? <String>[]
            : body
                  .split(RegExp(r'\s+'))
                  .where((token) => token.isNotEmpty)
                  .toList();
        productions.add(CfgProduction(left, symbols));
      }
    }
    return CfgDefinition(startSymbol: startSymbol, productions: productions);
  }

  List<List<String>> derive({bool leftmost = true, int maxSteps = 8}) {
    final forms = <List<String>>[
      [startSymbol],
    ];
    var current = <String>[startSymbol];
    for (var step = 0; step < maxSteps; step++) {
      final index = leftmost
          ? _leftmostNonTerminal(current)
          : _rightmostNonTerminal(current);
      if (index == -1) {
        break;
      }
      final production = productions.firstWhere(
        (item) => item.left == current[index],
        orElse: () => CfgProduction(current[index], const []),
      );
      current = [
        ...current.take(index),
        ...production.right,
        ...current.skip(index + 1),
      ];
      forms.add(current);
    }
    return forms;
  }

  Map<String, int> generateTerminalStrings({
    int maxDepth = 7,
    int maxLength = 8,
  }) {
    final counts = <String, int>{};
    final queue = Queue<List<String>>()..add([startSymbol]);
    final depth = <String, int>{
      _formKey([startSymbol]): 0,
    };

    while (queue.isNotEmpty) {
      final form = queue.removeFirst();
      final key = _formKey(form);
      final currentDepth = depth[key] ?? 0;
      if (currentDepth > maxDepth) {
        continue;
      }
      if (form.every((symbol) => !_isNonTerminal(symbol))) {
        final word = form.join('');
        if (word.length <= maxLength) {
          counts[word] = (counts[word] ?? 0) + 1;
        }
        continue;
      }
      if (form.where((symbol) => !_isNonTerminal(symbol)).join('').length >
          maxLength) {
        continue;
      }

      final index = _leftmostNonTerminal(form);
      if (index == -1) {
        continue;
      }
      final left = form[index];
      for (final production in productions.where((item) => item.left == left)) {
        final next = [
          ...form.take(index),
          ...production.right,
          ...form.skip(index + 1),
        ];
        final nextKey = _formKey(next);
        if ((depth[nextKey] ?? 999) > currentDepth + 1) {
          depth[nextKey] = currentDepth + 1;
          queue.add(next);
        } else if (next.every((symbol) => !_isNonTerminal(symbol))) {
          queue.add(next);
        }
      }
    }
    return counts;
  }

  bool get hasAmbiguityCandidate {
    return generateTerminalStrings().values.any((count) => count > 1);
  }

  int _leftmostNonTerminal(List<String> form) {
    return form.indexWhere(_isNonTerminal);
  }

  int _rightmostNonTerminal(List<String> form) {
    for (var i = form.length - 1; i >= 0; i--) {
      if (_isNonTerminal(form[i])) {
        return i;
      }
    }
    return -1;
  }

  static bool _isNonTerminal(String symbol) {
    return RegExp(r'^[A-Z][A-Za-z0-9_]*$').hasMatch(symbol);
  }

  String _formKey(List<String> form) => form.join(' ');
}

enum TapeMove { left, right, stay }

class TuringTransition {
  const TuringTransition({
    required this.from,
    required this.read,
    required this.to,
    required this.write,
    required this.move,
  });

  final String from;
  final String read;
  final String to;
  final String write;
  final TapeMove move;

  String get key => '$from|$read';

  String get label {
    final movement = switch (move) {
      TapeMove.left => 'L',
      TapeMove.right => 'R',
      TapeMove.stay => 'S',
    };
    return '$read -> $write, $movement';
  }
}

class TuringMachineDefinition {
  const TuringMachineDefinition({
    required this.states,
    required this.inputAlphabet,
    required this.tapeAlphabet,
    required this.startState,
    required this.acceptStates,
    required this.rejectStates,
    required this.transitions,
    this.blank = AutomataSymbols.blank,
  });

  final List<String> states;
  final List<String> inputAlphabet;
  final List<String> tapeAlphabet;
  final String startState;
  final Set<String> acceptStates;
  final Set<String> rejectStates;
  final List<TuringTransition> transitions;
  final String blank;

  SimulationResult run(String input, {int maxSteps = 150}) {
    final transitionMap = {for (final item in transitions) item.key: item};
    final tape = <int, String>{};
    for (var i = 0; i < input.length; i++) {
      tape[i] = input[i];
    }
    var head = 0;
    var state = startState;
    final steps = <SimulationStep>[
      SimulationStep(
        index: 0,
        state: state,
        activeStates: [state],
        tapeWindow: _window(tape, head, blank),
        headIndex: 5,
        note: 'Start at $state',
      ),
    ];

    for (var step = 1; step <= maxSteps; step++) {
      if (acceptStates.contains(state) || rejectStates.contains(state)) {
        break;
      }
      final read = tape[head] ?? blank;
      final transition = transitionMap['$state|$read'];
      if (transition == null) {
        return SimulationResult(
          accepted: acceptStates.contains(state),
          steps: steps,
          summary: 'Halted: no TM transition for ($state, $read).',
        );
      }
      tape[head] = transition.write;
      state = transition.to;
      switch (transition.move) {
        case TapeMove.left:
          head--;
        case TapeMove.right:
          head++;
        case TapeMove.stay:
          break;
      }
      steps.add(
        SimulationStep(
          index: step,
          state: state,
          symbol: read,
          activeStates: [state],
          tapeWindow: _window(tape, head, blank),
          headIndex: 5,
          accepting: acceptStates.contains(state),
          note: transition.label,
        ),
      );
    }

    final accepted = acceptStates.contains(state);
    return SimulationResult(
      accepted: accepted,
      halted: acceptStates.contains(state) || rejectStates.contains(state),
      limitHit: !(acceptStates.contains(state) || rejectStates.contains(state)),
      steps: steps,
      summary: accepted
          ? 'Accepted in $state.'
          : rejectStates.contains(state)
          ? 'Rejected in $state.'
          : 'Stopped after $maxSteps TM steps.',
    );
  }

  static List<String> _window(Map<int, String> tape, int head, String blank) {
    return [
      for (var position = head - 5; position <= head + 5; position++)
        tape[position] ?? blank,
    ];
  }
}

class AutomataCatalog {
  static DfaDefinition endingInAbDfa() {
    return const DfaDefinition(
      states: ['q0', 'q1', 'q2'],
      alphabet: ['a', 'b'],
      startState: 'q0',
      acceptStates: {'q2'},
      transitions: {
        'q0': {'a': 'q1', 'b': 'q0'},
        'q1': {'a': 'q1', 'b': 'q2'},
        'q2': {'a': 'q1', 'b': 'q0'},
      },
    );
  }

  static NfaDefinition substringAbNfa() {
    return const NfaDefinition(
      states: ['q0', 'q1', 'q2'],
      alphabet: ['a', 'b', AutomataSymbols.epsilon],
      startState: 'q0',
      acceptStates: {'q2'},
      transitions: {
        'q0': {
          'a': {'q0', 'q1'},
          'b': {'q0'},
        },
        'q1': {
          'b': {'q2'},
        },
        'q2': {
          'a': {'q2'},
          'b': {'q2'},
        },
      },
    );
  }

  static MooreDefinition parityMoore() {
    return const MooreDefinition(
      states: ['even', 'odd'],
      alphabet: ['0', '1'],
      startState: 'even',
      outputs: {'even': 'E', 'odd': 'O'},
      transitions: {
        'even': {'0': 'even', '1': 'odd'},
        'odd': {'0': 'odd', '1': 'even'},
      },
    );
  }

  static MealyDefinition parityMealy() {
    return const MealyDefinition(
      states: ['even', 'odd'],
      alphabet: ['0', '1'],
      startState: 'even',
      transitions: {
        'even': {'0': MealyMove('even', 'E'), '1': MealyMove('odd', 'O')},
        'odd': {'0': MealyMove('odd', 'O'), '1': MealyMove('even', 'E')},
      },
    );
  }

  static PdaDefinition anBnPda() {
    return const PdaDefinition(
      states: ['q0', 'q1', 'q2'],
      inputAlphabet: ['a', 'b'],
      stackAlphabet: [AutomataSymbols.stackBottom, 'A'],
      startState: 'q0',
      acceptStates: {'q2'},
      transitions: [
        PdaTransition(
          from: 'q0',
          to: 'q0',
          inputSymbol: 'a',
          stackTop: null,
          pushSymbols: ['A'],
        ),
        PdaTransition(from: 'q0', to: 'q1', inputSymbol: 'b', stackTop: 'A'),
        PdaTransition(from: 'q1', to: 'q1', inputSymbol: 'b', stackTop: 'A'),
        PdaTransition(
          from: 'q1',
          to: 'q2',
          stackTop: AutomataSymbols.stackBottom,
        ),
      ],
    );
  }

  static CfgDefinition balancedCfg() {
    return CfgDefinition.parse('''
S -> a S b | a b
''');
  }

  static TuringMachineDefinition binaryIncrementTm() {
    return const TuringMachineDefinition(
      states: ['scan', 'carry', 'accept'],
      inputAlphabet: ['0', '1'],
      tapeAlphabet: ['0', '1', AutomataSymbols.blank],
      startState: 'scan',
      acceptStates: {'accept'},
      rejectStates: {},
      transitions: [
        TuringTransition(
          from: 'scan',
          read: '0',
          to: 'scan',
          write: '0',
          move: TapeMove.right,
        ),
        TuringTransition(
          from: 'scan',
          read: '1',
          to: 'scan',
          write: '1',
          move: TapeMove.right,
        ),
        TuringTransition(
          from: 'scan',
          read: AutomataSymbols.blank,
          to: 'carry',
          write: AutomataSymbols.blank,
          move: TapeMove.left,
        ),
        TuringTransition(
          from: 'carry',
          read: '1',
          to: 'carry',
          write: '0',
          move: TapeMove.left,
        ),
        TuringTransition(
          from: 'carry',
          read: '0',
          to: 'accept',
          write: '1',
          move: TapeMove.stay,
        ),
        TuringTransition(
          from: 'carry',
          read: AutomataSymbols.blank,
          to: 'accept',
          write: '1',
          move: TapeMove.stay,
        ),
      ],
    );
  }
}

String setName(Set<String> states) => _setName(states);

String _setName(Set<String> states) {
  if (states.isEmpty) {
    return '{}';
  }
  return '{${_sorted(states).join(',')}}';
}

List<String> _sorted(Iterable<String> values) {
  return values.toList()..sort();
}
