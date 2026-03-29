import 'dart:ui';

import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_state.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Manages text scale factor with SharedPreferences persistence.
class TextScaleCubit extends Cubit<TextScaleState> {
  /// Creates a [TextScaleCubit].
  TextScaleCubit({required SharedPreferences prefs})
      : _prefs = prefs,
        super(const TextScaleState(scaleFactor: 1));

  final SharedPreferences _prefs;

  static const _key = 'text_scale_factor';

  bool get _hasSavedPreference => _prefs.containsKey(_key);

  /// Loads the saved scale factor from SharedPreferences.
  void loadScale() {
    final saved = _prefs.getDouble(_key);
    if (saved != null) {
      emit(TextScaleState(scaleFactor: saved));
    }
  }

  /// Sets the scale factor, persisting to SharedPreferences.
  Future<void> setScale(double value) async {
    await _prefs.setDouble(_key, value);
    emit(TextScaleState(scaleFactor: value));
  }

  /// Auto-detects scale for 4K displays. Only runs when no preference saved.
  void autoDetect(Size logicalSize, double dpr, {required bool isDesktop}) {
    if (_hasSavedPreference) return;
    final physicalWidth = logicalSize.width * dpr;
    final scale = (physicalWidth >= 3200 && isDesktop) ? 1.5 : 1;
    emit(TextScaleState(scaleFactor: scale.toDouble()));
  }

  /// Clears the saved preference and resets to default 1.0.
  Future<void> resetToAuto() async {
    await _prefs.remove(_key);
    emit(const TextScaleState(scaleFactor: 1));
  }
}
