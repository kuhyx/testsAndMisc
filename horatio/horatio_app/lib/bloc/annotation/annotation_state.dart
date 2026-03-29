import 'package:equatable/equatable.dart';
import 'package:flutter/foundation.dart';
import 'package:horatio_core/horatio_core.dart';

/// State for [AnnotationCubit].
///
/// Does not extend [Equatable] because [TextMark] and [LineNote] use
/// id-only equality.  Extending [Equatable] would cause [Cubit.emit]
/// to silently drop state updates when only non-id fields change
/// (e.g. after [AnnotationDao.updateNoteText]).
sealed class AnnotationState {
  const AnnotationState();
}

/// No annotations loaded.
final class AnnotationInitial extends AnnotationState {
  const AnnotationInitial();
}

/// Annotations loaded for a script.
final class AnnotationLoaded extends AnnotationState {
  const AnnotationLoaded({
    required this.scriptId,
    required this.marks,
    required this.notes,
    this.selectedLineIndex,
    this.editing,
  });

  /// The script these annotations belong to.
  final String scriptId;

  /// All text marks for this script.
  final List<TextMark> marks;

  /// All line notes for this script.
  final List<LineNote> notes;

  /// Currently selected line index (nullable).
  final int? selectedLineIndex;

  /// Non-null when actively editing.
  final EditingContext? editing;

  /// Creates a copy with specified fields replaced.
  AnnotationLoaded copyWith({
    List<TextMark>? marks,
    List<LineNote>? notes,
    int? Function()? selectedLineIndex,
    EditingContext? Function()? editing,
  }) => AnnotationLoaded(
    scriptId: scriptId,
    marks: marks ?? this.marks,
    notes: notes ?? this.notes,
    selectedLineIndex: selectedLineIndex != null
        ? selectedLineIndex()
        : this.selectedLineIndex,
    editing: editing != null ? editing() : this.editing,
  );
}

/// Context for an active annotation edit.
@immutable
final class EditingContext extends Equatable {
  const EditingContext({
    required this.lineIndex,
    required this.isAddingMark,
  });

  /// The line being edited.
  final int lineIndex;

  /// Whether placing a mark (true) or writing a note (false).
  final bool isAddingMark;

  @override
  List<Object?> get props => [lineIndex, isAddingMark];
}
