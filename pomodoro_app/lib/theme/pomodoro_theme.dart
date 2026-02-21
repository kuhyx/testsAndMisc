import 'package:flutter/material.dart';

import '../models/pomodoro_state.dart';

/// Provides consistent theming for the Pomodoro app across platforms.
class PomodoroTheme {
  PomodoroTheme._();

  // Brand colors per mode.
  static const Color workColor = Color(0xFFE74C3C);
  static const Color shortBreakColor = Color(0xFF2ECC71);
  static const Color longBreakColor = Color(0xFF3498DB);

  static const Color _darkSurface = Color(0xFF1A1A2E);
  static const Color _darkBackground = Color(0xFF16213E);
  static const Color _textLight = Color(0xFFF5F5F5);
  static const Color _textMuted = Color(0xFFB0B0B0);

  /// Returns the accent color for the given [mode].
  static Color colorForMode(PomodoroMode mode) {
    switch (mode) {
      case PomodoroMode.work:
        return workColor;
      case PomodoroMode.shortBreak:
        return shortBreakColor;
      case PomodoroMode.longBreak:
        return longBreakColor;
    }
  }

  /// The app's dark theme.
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: _darkBackground,
      colorScheme: const ColorScheme.dark(
        primary: workColor,
        surface: _darkSurface,
        onSurface: _textLight,
      ),
      textTheme: const TextTheme(
        displayLarge: TextStyle(
          fontSize: 72,
          fontWeight: FontWeight.w300,
          color: _textLight,
          letterSpacing: 4,
        ),
        headlineMedium: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w500,
          color: _textLight,
        ),
        bodyLarge: TextStyle(
          fontSize: 16,
          color: _textMuted,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(30),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}
