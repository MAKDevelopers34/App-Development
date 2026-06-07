const epsilon = '\u03B5';

class Grammar {
  Grammar({required this.rules, required this.start});

  final Map<String, List<List<String>>> rules;
  final String start;
}

class ConversionStep {
  const ConversionStep({
    required this.badge,
    required this.title,
    required this.grammar,
    required this.notes,
  });

  final String badge;
  final String title;
  final String grammar;
  final List<String> notes;
}

class GrammarMetrics {
  const GrammarMetrics({
    required this.variables,
    required this.terminals,
    required this.productions,
  });

  final int variables;
  final int terminals;
  final int productions;
}

class ConversionResult {
  const ConversionResult({
    required this.steps,
    required this.finalRules,
    required this.finalStart,
    required this.metrics,
    required this.isValidCnf,
    required this.invalidRules,
    this.error,
  });

  final List<ConversionStep> steps;
  final String finalRules;
  final String finalStart;
  final GrammarMetrics metrics;
  final bool isValidCnf;
  final List<String> invalidRules;
  final String? error;

  bool get hasError => error != null;
}

ConversionResult convertCfgToCnf(String input) {
  try {
    var grammar = parseGrammar(input);
    var rules = grammar.rules;
    var start = grammar.start;
    final steps = <ConversionStep>[
      ConversionStep(
        badge: 'Input',
        title: 'Input grammar',
        grammar: formatRules(rules),
        notes: ['Start symbol: $start'],
      ),
    ];

    final stepOne = addFreshStart(rules, start);
    rules = stepOne.grammar.rules;
    start = stepOne.grammar.start;
    steps.add(
      ConversionStep(
        badge: 'Step 1',
        title: 'Fresh start symbol',
        grammar: formatRules(rules),
        notes: stepOne.notes,
      ),
    );

    final stepTwo = removeEpsilonProductions(rules, start);
    rules = stepTwo.grammar.rules;
    start = stepTwo.grammar.start;
    steps.add(
      ConversionStep(
        badge: 'Step 2',
        title: 'Remove epsilon productions',
        grammar: formatRules(rules),
        notes: stepTwo.notes,
      ),
    );

    final stepThree = removeUnitProductions(rules, start);
    rules = stepThree.grammar.rules;
    start = stepThree.grammar.start;
    steps.add(
      ConversionStep(
        badge: 'Step 3',
        title: 'Remove unit productions',
        grammar: formatRules(rules),
        notes: stepThree.notes,
      ),
    );

    final stepFour = binarizeLongProductions(rules, start);
    rules = stepFour.grammar.rules;
    start = stepFour.grammar.start;
    steps.add(
      ConversionStep(
        badge: 'Step 4',
        title: 'Binarize long productions',
        grammar: formatRules(rules),
        notes: stepFour.notes,
      ),
    );

    final stepFive = replaceMixedTerminals(rules, start);
    rules = stepFive.grammar.rules;
    start = stepFive.grammar.start;
    steps.add(
      ConversionStep(
        badge: 'Step 5',
        title: 'Replace mixed terminals',
        grammar: formatRules(rules),
        notes: stepFive.notes,
      ),
    );

    final invalid = invalidCnfRules(rules, start);
    return ConversionResult(
      steps: steps,
      finalRules: formatRules(rules),
      finalStart: start,
      metrics: metricsFor(rules),
      isValidCnf: invalid.isEmpty,
      invalidRules: invalid,
    );
  } on FormatException catch (error) {
    return ConversionResult(
      steps: const [],
      finalRules: '',
      finalStart: '',
      metrics: const GrammarMetrics(variables: 0, terminals: 0, productions: 0),
      isValidCnf: false,
      invalidRules: const [],
      error: error.message,
    );
  } catch (_) {
    return ConversionResult(
      steps: const [],
      finalRules: '',
      finalStart: '',
      metrics: const GrammarMetrics(variables: 0, terminals: 0, productions: 0),
      isValidCnf: false,
      invalidRules: const [],
      error: 'Could not convert this grammar. Check the production format.',
    );
  }
}

Grammar parseGrammar(String source) {
  final rules = <String, List<List<String>>>{};
  final lines = source
      .split(RegExp(r'\r?\n'))
      .map((line) => line.split('#').first.trim())
      .where((line) => line.isNotEmpty)
      .toList();

  if (lines.isEmpty) {
    throw const FormatException('Enter at least one production.');
  }

  final productionPattern = RegExp(r'^\s*(\S+)\s*(?:->|=>|\u2192)\s*(.+)$');
  for (final line in lines) {
    final match = productionPattern.firstMatch(line);
    if (match == null) {
      throw FormatException('Invalid production: "$line"');
    }

    final lhs = match.group(1)!.trim();
    final rhs = match.group(2)!.trim();
    if (lhs.isEmpty || _isEpsilonToken(lhs)) {
      throw FormatException('Invalid left-hand side: "$lhs"');
    }

    final productions = rhs
        .split('|')
        .map((alternative) => _tokenizeProduction(alternative.trim()))
        .toList();
    rules.putIfAbsent(lhs, () => <List<String>>[]).addAll(productions);
  }

  for (final entry in rules.entries) {
    rules[entry.key] = _dedupeProductions(entry.value);
  }

  return Grammar(rules: rules, start: rules.keys.first);
}

({Grammar grammar, List<String> notes}) addFreshStart(
  Map<String, List<List<String>>> rules,
  String start,
) {
  final appearsOnRight = rules.values.any(
    (productions) =>
        productions.any((production) => production.contains(start)),
  );

  if (!appearsOnRight) {
    return (
      grammar: Grammar(rules: _cloneRules(rules), start: start),
      notes: [
        'The start symbol $start does not appear on any right-hand side.',
      ],
    );
  }

  final used = rules.keys.toSet();
  final freshStart = _freshVariable('${start}0', used);
  return (
    grammar: Grammar(
      rules: <String, List<List<String>>>{
        freshStart: [
          [start],
        ],
        ..._cloneRules(rules),
      },
      start: freshStart,
    ),
    notes: [
      '$start appears on a right-hand side.',
      'Added $freshStart -> $start to protect the original start symbol.',
    ],
  );
}

({Grammar grammar, List<String> notes}) removeEpsilonProductions(
  Map<String, List<List<String>>> rules,
  String start,
) {
  final nullable = <String>{};
  var changed = true;

  while (changed) {
    changed = false;
    for (final entry in rules.entries) {
      final variable = entry.key;
      for (final production in entry.value) {
        final isNullableProduction =
            _isEpsilonProduction(production) ||
            production.every((symbol) => nullable.contains(symbol));
        if (isNullableProduction && nullable.add(variable)) {
          changed = true;
        }
      }
    }
  }

  final nextRules = <String, List<List<String>>>{};
  for (final entry in rules.entries) {
    final variable = entry.key;
    final nextProductions = <List<String>>[];

    for (final production in entry.value) {
      if (_isEpsilonProduction(production)) {
        if (variable == start) {
          nextProductions.add([epsilon]);
        }
        continue;
      }

      final nullableIndexes = <int>[];
      for (var index = 0; index < production.length; index++) {
        if (nullable.contains(production[index])) {
          nullableIndexes.add(index);
        }
      }

      final variants = 1 << nullableIndexes.length;
      for (var mask = 0; mask < variants; mask++) {
        final omitted = <int>{};
        for (var bit = 0; bit < nullableIndexes.length; bit++) {
          if ((mask & (1 << bit)) != 0) {
            omitted.add(nullableIndexes[bit]);
          }
        }
        final generated = <String>[];
        for (var index = 0; index < production.length; index++) {
          if (!omitted.contains(index)) {
            generated.add(production[index]);
          }
        }

        if (generated.isEmpty) {
          if (variable == start) {
            nextProductions.add([epsilon]);
          }
        } else {
          nextProductions.add(generated);
        }
      }
    }

    if (variable == start && nullable.contains(start)) {
      nextProductions.add([epsilon]);
    }
    nextRules[variable] = _dedupeProductions(nextProductions);
  }

  final nullableText = nullable.isEmpty ? 'none' : nullable.join(', ');
  return (
    grammar: Grammar(rules: nextRules, start: start),
    notes: [
      'Nullable variables: {$nullableText}.',
      if (nullable.contains(start))
        'Kept $start -> $epsilon because CNF allows only the start symbol to produce epsilon.',
      'Removed all other epsilon productions and added the required alternatives.',
    ],
  );
}

({Grammar grammar, List<String> notes}) removeUnitProductions(
  Map<String, List<List<String>>> rules,
  String start,
) {
  final variables = rules.keys.toSet();
  final closures = <String, Set<String>>{};
  final notes = <String>[];

  for (final variable in rules.keys) {
    final reached = <String>{variable};
    final queue = <String>[variable];
    while (queue.isNotEmpty) {
      final current = queue.removeAt(0);
      for (final production in rules[current] ?? const <List<String>>[]) {
        if (_isUnitProduction(production, variables) &&
            reached.add(production.single)) {
          queue.add(production.single);
        }
      }
    }
    closures[variable] = reached;
    notes.add('Unit closure($variable) = {${reached.join(', ')}}.');
  }

  final nextRules = <String, List<List<String>>>{};
  for (final variable in rules.keys) {
    final productions = <List<String>>[];
    for (final reachable in closures[variable]!) {
      for (final production in rules[reachable] ?? const <List<String>>[]) {
        if (_isUnitProduction(production, variables)) {
          continue;
        }
        if (_isEpsilonProduction(production) && variable != start) {
          continue;
        }
        productions.add(List<String>.of(production));
      }
    }
    nextRules[variable] = _dedupeProductions(productions);
  }

  notes.add('Removed every A -> B unit production.');
  return (grammar: Grammar(rules: nextRules, start: start), notes: notes);
}

({Grammar grammar, List<String> notes}) binarizeLongProductions(
  Map<String, List<List<String>>> rules,
  String start,
) {
  final nextRules = _cloneRules(rules);
  final used = nextRules.keys.toSet();
  final pairVariables = <String, String>{};
  final notes = <String>[];

  String variableForPair(List<String> pair) {
    final key = pair.join(' ');
    final existing = pairVariables[key];
    if (existing != null) {
      return existing;
    }

    final variable = _freshVariable('X', used);
    pairVariables[key] = variable;
    nextRules[variable] = [List<String>.of(pair)];
    notes.add('Introduced $variable -> ${pair.join(' ')}.');
    return variable;
  }

  for (final variable in rules.keys) {
    final converted = <List<String>>[];
    for (final production in rules[variable]!) {
      if (production.length <= 2) {
        converted.add(List<String>.of(production));
        continue;
      }

      final current = List<String>.of(production);
      while (current.length > 2) {
        final pair = current.sublist(current.length - 2);
        final helper = variableForPair(pair);
        current.removeRange(current.length - 2, current.length);
        current.add(helper);
      }
      converted.add(current);
    }
    nextRules[variable] = _dedupeProductions(converted);
  }

  if (notes.isEmpty) {
    notes.add('No productions longer than two symbols were found.');
  } else {
    notes.add('All long right-hand sides are now binary.');
  }

  return (grammar: Grammar(rules: nextRules, start: start), notes: notes);
}

({Grammar grammar, List<String> notes}) replaceMixedTerminals(
  Map<String, List<List<String>>> rules,
  String start,
) {
  final nextRules = _cloneRules(rules);
  final variables = nextRules.keys.toSet();
  final terminalVariables = <String, String>{};
  final notes = <String>[];

  String variableForTerminal(String terminal) {
    final existing = terminalVariables[terminal];
    if (existing != null) {
      return existing;
    }

    final variable = _freshVariable('T', variables);
    terminalVariables[terminal] = variable;
    nextRules[variable] = [
      [terminal],
    ];
    notes.add('Introduced $variable -> $terminal.');
    return variable;
  }

  for (final variable in rules.keys) {
    final converted = <List<String>>[];
    for (final production in rules[variable]!) {
      if (production.length <= 1) {
        converted.add(List<String>.of(production));
        continue;
      }

      converted.add([
        for (final symbol in production)
          if (variables.contains(symbol))
            symbol
          else
            variableForTerminal(symbol),
      ]);
    }
    nextRules[variable] = _dedupeProductions(converted);
  }

  if (notes.isEmpty) {
    notes.add('No terminals appeared inside mixed productions.');
  } else {
    notes.add('Every mixed production now uses variables only.');
  }

  return (grammar: Grammar(rules: nextRules, start: start), notes: notes);
}

String formatRules(Map<String, List<List<String>>> rules) {
  return rules.entries
      .map((entry) {
        final right = entry.value
            .map((production) => production.join(' '))
            .join(' | ');
        return '${entry.key} -> $right';
      })
      .join('\n');
}

GrammarMetrics metricsFor(Map<String, List<List<String>>> rules) {
  final variables = rules.keys.toSet();
  final terminals = <String>{};
  var productions = 0;

  for (final productionList in rules.values) {
    productions += productionList.length;
    for (final production in productionList) {
      for (final symbol in production) {
        if (symbol != epsilon && !variables.contains(symbol)) {
          terminals.add(symbol);
        }
      }
    }
  }

  return GrammarMetrics(
    variables: variables.length,
    terminals: terminals.length,
    productions: productions,
  );
}

List<String> invalidCnfRules(
  Map<String, List<List<String>>> rules,
  String start,
) {
  final variables = rules.keys.toSet();
  final invalid = <String>[];

  for (final entry in rules.entries) {
    for (final production in entry.value) {
      final validStartEpsilon =
          entry.key == start && _isEpsilonProduction(production);
      final validTerminal =
          production.length == 1 &&
          production.single != epsilon &&
          !variables.contains(production.single);
      final validPair =
          production.length == 2 &&
          variables.contains(production[0]) &&
          variables.contains(production[1]);

      if (!validStartEpsilon && !validTerminal && !validPair) {
        invalid.add('${entry.key} -> ${production.join(' ')}');
      }
    }
  }

  return invalid;
}

Map<String, List<List<String>>> _cloneRules(
  Map<String, List<List<String>>> rules,
) {
  return <String, List<List<String>>>{
    for (final entry in rules.entries)
      entry.key: [
        for (final production in entry.value) List<String>.of(production),
      ],
  };
}

List<List<String>> _dedupeProductions(List<List<String>> productions) {
  final seen = <String>{};
  final output = <List<String>>[];
  for (final production in productions) {
    final key = production.join('\u0001');
    if (seen.add(key)) {
      output.add(List<String>.of(production));
    }
  }
  return output;
}

List<String> _tokenizeProduction(String alternative) {
  if (alternative.isEmpty || _isEpsilonToken(alternative)) {
    return [epsilon];
  }

  if (RegExp(r'\s').hasMatch(alternative)) {
    return alternative
        .split(RegExp(r'\s+'))
        .where((symbol) => symbol.isNotEmpty)
        .map((symbol) => _isEpsilonToken(symbol) ? epsilon : symbol)
        .toList();
  }

  final tokens = <String>[];
  var index = 0;
  while (index < alternative.length) {
    final code = alternative.codeUnitAt(index);
    final char = alternative[index];
    if (_isAsciiUppercase(code)) {
      final buffer = StringBuffer(char);
      index++;
      while (index < alternative.length) {
        final nextCode = alternative.codeUnitAt(index);
        final next = alternative[index];
        if (_isAsciiDigit(nextCode) || next == "'") {
          buffer.write(next);
          index++;
        } else {
          break;
        }
      }
      tokens.add(buffer.toString());
    } else {
      tokens.add(_isEpsilonToken(char) ? epsilon : char);
      index++;
    }
  }

  return tokens;
}

String _freshVariable(String base, Set<String> used) {
  var index = 0;
  while (true) {
    final candidate = index == 0 && base.length > 1
        ? base
        : '$base${index + 1}';
    if (used.add(candidate)) {
      return candidate;
    }
    index++;
  }
}

bool _isUnitProduction(List<String> production, Set<String> variables) {
  return production.length == 1 && variables.contains(production.single);
}

bool _isEpsilonProduction(List<String> production) {
  return production.length == 1 && production.single == epsilon;
}

bool _isEpsilonToken(String token) {
  final value = token.trim().toLowerCase();
  return value == epsilon ||
      value == r'\epsilon' ||
      value == 'epsilon' ||
      value == 'eps' ||
      value == 'lambda' ||
      value == '\u03BB';
}

bool _isAsciiUppercase(int codeUnit) => codeUnit >= 65 && codeUnit <= 90;

bool _isAsciiDigit(int codeUnit) => codeUnit >= 48 && codeUnit <= 57;
