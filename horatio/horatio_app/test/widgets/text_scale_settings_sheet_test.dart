import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_state.dart';
import 'package:horatio_app/widgets/text_scale_settings_sheet.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  late TextScaleCubit cubit;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    cubit = TextScaleCubit(prefs: prefs);
  });

  tearDown(() => cubit.close());

  Widget buildSheet() => MaterialApp(
        home: BlocProvider<TextScaleCubit>.value(
          value: cubit,
          child: const Scaffold(body: TextScaleSettingsSheet()),
        ),
      );

  group('TextScaleSettingsSheet', () {
    testWidgets('shows slider and preview text', (tester) async {
      await tester.pumpWidget(buildSheet());
      expect(find.byType(Slider), findsOneWidget);
      expect(find.textContaining('1.0x'), findsOneWidget);
    });

    testWidgets('slider changes scale', (tester) async {
      await tester.pumpWidget(buildSheet());
      final slider = find.byType(Slider);
      await tester.drag(slider, const Offset(100, 0));
      await tester.pumpAndSettle();
      expect(cubit.state.scaleFactor, isNot(1));
    });

    testWidgets('reset button resets to default', (tester) async {
      await cubit.setScale(2);
      await tester.pumpWidget(buildSheet());
      await tester.tap(find.text('Reset to auto'));
      await tester.pumpAndSettle();
      expect(cubit.state, const TextScaleState(scaleFactor: 1));
    });

    testWidgets('shows current scale value', (tester) async {
      await cubit.setScale(1.5);
      await tester.pumpWidget(buildSheet());
      expect(find.textContaining('1.5x'), findsOneWidget);
    });
  });
}
