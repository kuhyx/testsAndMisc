import 'dart:async';

import 'package:billsplit/state/app_state.dart';
import 'package:billsplit/ui/home_screen.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final state = AppState();
  unawaited(state.load());
  runApp(BillSplitApp(state: state));
}

/// Root widget wiring [AppState] into the tree.
class BillSplitApp extends StatelessWidget {
  /// Creates the app around an existing [state].
  const BillSplitApp({required this.state, super.key});

  /// The single app-wide state instance.
  final AppState state;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: state,
      child: MaterialApp(
        title: 'BillSplit',
        debugShowCheckedModeBanner: false,
        // The shared light theme, replacing a teal-seeded scheme. Light, not
        // dark: the receipt screens carry black-on-white helper text, so
        // switching brightness here would make it unreadable.
        theme: buildLightTheme(),
        home: const HomeScreen(),
      ),
    );
  }
}
