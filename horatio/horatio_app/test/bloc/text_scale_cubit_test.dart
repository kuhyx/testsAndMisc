import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_state.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  group('TextScaleCubit', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('initial state has scaleFactor 1.0', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs);
      expect(cubit.state, const TextScaleState(scaleFactor: 1));
      await cubit.close();
    });

    test('loadScale reads saved value', () async {
      SharedPreferences.setMockInitialValues({'text_scale_factor': 2.0});
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs)..loadScale();
      await Future<void>.delayed(Duration.zero);
      expect(cubit.state, const TextScaleState(scaleFactor: 2));
      await cubit.close();
    });

    test('loadScale uses 1.0 when no saved value', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs)..loadScale();
      await Future<void>.delayed(Duration.zero);
      expect(cubit.state, const TextScaleState(scaleFactor: 1));
      await cubit.close();
    });

    test('setScale persists and emits', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs);
      await cubit.setScale(1.8);
      expect(cubit.state, const TextScaleState(scaleFactor: 1.8));
      expect(prefs.getDouble('text_scale_factor'), 1.8);
      await cubit.close();
    });

    test('autoDetect sets 1.5 for 4K desktop', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs)
        ..autoDetect(const Size(1920, 1080), 2, isDesktop: true);
      expect(cubit.state, const TextScaleState(scaleFactor: 1.5));
      await cubit.close();
    });

    test('autoDetect sets 1.0 for non-4K', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs)
        ..autoDetect(const Size(1920, 1080), 1, isDesktop: true);
      expect(cubit.state, const TextScaleState(scaleFactor: 1));
      await cubit.close();
    });

    test('autoDetect sets 1.0 for mobile even at high resolution', () async {
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs)
        ..autoDetect(const Size(1920, 1080), 2, isDesktop: false);
      expect(cubit.state, const TextScaleState(scaleFactor: 1));
      await cubit.close();
    });

    test('autoDetect skips when preference already saved', () async {
      SharedPreferences.setMockInitialValues({'text_scale_factor': 2.5});
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs)..loadScale();
      await Future<void>.delayed(Duration.zero);
      cubit.autoDetect(const Size(1920, 1080), 2, isDesktop: true);
      expect(cubit.state, const TextScaleState(scaleFactor: 2.5));
      await cubit.close();
    });

    test('resetToAuto clears preference and resets to default', () async {
      SharedPreferences.setMockInitialValues({'text_scale_factor': 2.5});
      final prefs = await SharedPreferences.getInstance();
      final cubit = TextScaleCubit(prefs: prefs)..loadScale();
      await Future<void>.delayed(Duration.zero);
      await cubit.resetToAuto();
      expect(prefs.containsKey('text_scale_factor'), isFalse);
      expect(cubit.state, const TextScaleState(scaleFactor: 1));
      await cubit.close();
    });

    test('TextScaleState equality', () {
      const a = TextScaleState(scaleFactor: 1);
      const b = TextScaleState(scaleFactor: 1);
      const c = TextScaleState(scaleFactor: 2);
      expect(a, equals(b));
      expect(a, isNot(equals(c)));
    });
  });
}
