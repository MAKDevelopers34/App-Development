import 'dart:io';

import '../lib/core/automata_core.dart';

void main() {
  final dfa = AutomataCatalog.endingInAbDfa();
  assert(dfa.run('aab').accepted);
  assert(!dfa.run('abba').accepted);

  final minimized = dfa.minimize();
  assert(minimized.states.length == 3);

  final nfa = AutomataCatalog.substringAbNfa();
  assert(nfa.run('baba').accepted);
  assert(!nfa.run('bbb').accepted);
  assert(nfa.toDfa().run('baba').accepted);

  final moore = AutomataCatalog.parityMoore();
  assert(moore.run('101').output == 'EOOE');

  final mealy = AutomataCatalog.parityMealy();
  assert(mealy.run('101').output == 'OOE');

  final pda = AutomataCatalog.anBnPda();
  assert(pda.run('aaabbb').accepted);
  assert(!pda.run('aab').accepted);

  final cfg = AutomataCatalog.balancedCfg();
  final derivation = cfg.derive(maxSteps: 3);
  assert(
    derivation.last.join('') == 'aaSbb' || derivation.last.join('') == 'aabb',
  );

  final tm = AutomataCatalog.binaryIncrementTm();
  final tmResult = tm.run('111');
  assert(tmResult.accepted);
  assert(tmResult.steps.last.tapeWindow.join('').contains('1000'));

  stdout.writeln('Automata core smoke test passed.');
}
