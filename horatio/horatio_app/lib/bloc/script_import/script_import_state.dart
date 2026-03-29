import 'package:equatable/equatable.dart';
import 'package:horatio_core/horatio_core.dart';

/// State for [ScriptImportCubit].
sealed class ScriptImportState extends Equatable {
  const ScriptImportState();
}

/// Initial state — no scripts loaded yet.
final class ScriptImportInitial extends ScriptImportState {
  const ScriptImportInitial();

  @override
  List<Object?> get props => [];
}

/// Scripts are loaded and available.
final class ScriptImportLoaded extends ScriptImportState {
  const ScriptImportLoaded({required this.scripts});

  /// The list of imported scripts.
  final List<Script> scripts;

  @override
  List<Object?> get props => [scripts];
}

/// An import operation is in progress.
final class ScriptImportLoading extends ScriptImportState {
  const ScriptImportLoading();

  @override
  List<Object?> get props => [];
}

/// Import failed with an error.
final class ScriptImportError extends ScriptImportState {
  const ScriptImportError({required this.message});

  /// Human-readable error description.
  final String message;

  @override
  List<Object?> get props => [message];
}
