import 'package:meta/meta.dart';

/// A character role in a script.
@immutable
final class Role {
  /// Creates a [Role] with the given [name].
  const Role({required this.name});

  /// The character's name as detected in the script.
  final String name;

  /// Returns a normalized version of the name for comparison.
  String get normalizedName => name.trim().toUpperCase();

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Role && normalizedName == other.normalizedName;

  @override
  int get hashCode => normalizedName.hashCode;

  @override
  String toString() => 'Role($name)';
}
