import 'dart:async';

import 'package:billsplit/state/app_state.dart';
import 'package:billsplit/ui/home_screen.dart';
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
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        ),
        home: const HomeScreen(),
      ),
    );
  }
}
