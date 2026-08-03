import 'package:billsplit/main.dart';
import 'package:billsplit/state/app_state.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('app builds and shows empty state', (tester) async {
    // Real file IO never completes inside the fake-async test zone, so skip
    // load() and mark the state ready directly; this is a pure widget smoke
    // test (persistence is exercised by the domain tests / at runtime).
    final state = AppState()..loaded = true;
    await tester.pumpWidget(BillSplitApp(state: state));
    await tester.pump();
    expect(find.text('BillSplit'), findsOneWidget);
    expect(find.textContaining('No receipts yet'), findsOneWidget);
  });
}
