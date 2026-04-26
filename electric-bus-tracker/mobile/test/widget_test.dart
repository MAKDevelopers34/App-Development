import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/main.dart';

void main() {
  testWidgets('App launches successfully', (WidgetTester tester) async {
    await tester.pumpWidget(const ElectricBusTrackerApp());
    expect(find.byType(ElectricBusTrackerApp), findsOneWidget);
  });
}
