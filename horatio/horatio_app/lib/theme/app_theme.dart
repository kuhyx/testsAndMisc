import 'package:flutter/material.dart';

/// Theatrical-themed app theme for Horatio.
abstract final class AppTheme {
  // -- Palette --
  static const Color _burgundy = Color(0xFF8B1A3A);
  static const Color _gold = Color(0xFFD4A843);
  static const Color _cream = Color(0xFFFFF8E7);
  static const Color _charcoal = Color(0xFF2C2C2C);
  static const Color _darkBg = Color(0xFF1A1A2E);
  static const Color _darkSurface = Color(0xFF16213E);

  /// Light theme — warm, welcoming stage light aesthetic.
  static final ThemeData light = ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    colorSchemeSeed: _burgundy,
    scaffoldBackgroundColor: _cream,
    appBarTheme: const AppBarTheme(
      backgroundColor: _burgundy,
      foregroundColor: _cream,
      elevation: 2,
      centerTitle: true,
    ),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: _gold,
      foregroundColor: _charcoal,
    ),
    cardTheme: CardThemeData(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: _burgundy, width: 2),
      ),
    ),
    textTheme: const TextTheme(
      headlineLarge: TextStyle(
        fontWeight: FontWeight.bold,
        color: _charcoal,
      ),
      titleMedium: TextStyle(
        fontWeight: FontWeight.w600,
        color: _charcoal,
      ),
    ),
  );

  /// Dark theme — backstage / dramatic feel.
  static final ThemeData dark = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorSchemeSeed: _burgundy,
    scaffoldBackgroundColor: _darkBg,
    appBarTheme: const AppBarTheme(
      backgroundColor: _darkSurface,
      foregroundColor: _gold,
      elevation: 0,
      centerTitle: true,
    ),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: _gold,
      foregroundColor: _charcoal,
    ),
    cardTheme: CardThemeData(
      elevation: 4,
      color: _darkSurface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: _gold, width: 2),
      ),
    ),
    textTheme: const TextTheme(
      headlineLarge: TextStyle(
        fontWeight: FontWeight.bold,
        color: _gold,
      ),
      titleMedium: TextStyle(
        fontWeight: FontWeight.w600,
      ),
    ),
  );
}
