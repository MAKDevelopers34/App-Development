import 'package:cfg_cnf/cnf_converter.dart';
import 'package:cfg_cnf/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('converts a grammar with epsilon and mixed terminals to CNF', () {
    final result = convertCfgToCnf('''
S -> A B | a B
A -> a | epsilon
B -> b
''');

    expect(result.hasError, isFalse);
    expect(result.isValidCnf, isTrue);
    expect(result.finalRules, contains('T1 -> a'));
    expect(result.finalRules, contains('S -> A B'));
  });

  testWidgets('renders the converter workspace', (tester) async {
    await tester.pumpWidget(const CfgCnfApp());

    expect(find.text('CFG to CNF Converter'), findsOneWidget);
    expect(find.text('Grammar Editor'), findsOneWidget);
    expect(find.text('Final CNF Grammar'), findsOneWidget);
  });
}
