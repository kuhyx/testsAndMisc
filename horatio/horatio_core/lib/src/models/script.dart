import 'package:horatio_core/src/models/role.dart';
import 'package:horatio_core/src/models/scene.dart';

/// A fully parsed script with metadata, roles, and scenes.
final class Script {
  /// Creates a [Script] from parsed data.
  const Script({
    required this.title,
    required this.roles,
    required this.scenes,
  });

  /// The title of the script.
  final String title;

  /// All character roles detected in the script.
  final List<Role> roles;

  /// Scenes in order.
  final List<Scene> scenes;

  /// Returns all lines in the script across all scenes.
  int get totalLineCount =>
      scenes.fold(0, (sum, scene) => sum + scene.lines.length);

  /// Returns the number of lines for a specific [role].
  int lineCountForRole(Role role) => scenes.fold(
    0,
    (sum, scene) => sum + scene.lines.where((line) => line.role == role).length,
  );

  @override
  String toString() =>
      'Script($title, ${roles.length} roles, ${scenes.length} scenes)';
}
