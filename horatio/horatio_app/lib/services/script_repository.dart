import 'package:horatio_core/horatio_core.dart';

/// In-memory repository for managing parsed scripts.
///
/// Phase 2 will replace this with drift/SQLite persistence.
class ScriptRepository {
  final List<Script> _scripts = [];

  /// All scripts currently loaded.
  List<Script> get scripts => List.unmodifiable(_scripts);

  /// Adds a parsed [script] to the repository.
  void add(Script script) {
    _scripts.add(script);
  }

  /// Removes a script by [index].
  void removeAt(int index) {
    _scripts.removeAt(index);
  }

  /// Clears all scripts.
  void clear() {
    _scripts.clear();
  }
}
