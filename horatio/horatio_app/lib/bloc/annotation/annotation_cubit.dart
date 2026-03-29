import 'dart:async';

import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/annotation/annotation_state.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:uuid/uuid.dart';

/// Manages annotation CRUD for a script.
class AnnotationCubit extends Cubit<AnnotationState> {
  /// Creates an [AnnotationCubit].
  AnnotationCubit({required AnnotationDao dao})
      : _dao = dao,
        super(const AnnotationInitial());

  final AnnotationDao _dao;
  StreamSubscription<List<TextMark>>? _marksSub;
  StreamSubscription<List<LineNote>>? _notesSub;
  String? _scriptId;

  static const _uuid = Uuid();

  /// Subscribes to annotation streams for a script.
  void loadAnnotations(String scriptId) {
    _scriptId = scriptId;
    _marksSub?.cancel();
    _notesSub?.cancel();

    var latestMarks = <TextMark>[];
    var latestNotes = <LineNote>[];

    _marksSub = _dao.watchMarksForScript(scriptId).listen((marks) {
      latestMarks = marks;
      _emitLoaded(scriptId, latestMarks, latestNotes);
    });

    _notesSub = _dao.watchNotesForScript(scriptId).listen((notes) {
      latestNotes = notes;
      _emitLoaded(scriptId, latestMarks, latestNotes);
    });
  }

  void _emitLoaded(
    String scriptId,
    List<TextMark> marks,
    List<LineNote> notes,
  ) {
    final current = state;
    emit(AnnotationLoaded(
      scriptId: scriptId,
      marks: marks,
      notes: notes,
      selectedLineIndex:
          current is AnnotationLoaded ? current.selectedLineIndex : null,
      editing: current is AnnotationLoaded ? current.editing : null,
    ));
  }

  /// Focuses a line for annotation.
  void selectLine(int? lineIndex) {
    final current = state;
    if (current is AnnotationLoaded) {
      emit(current.copyWith(selectedLineIndex: () => lineIndex));
    }
  }

  /// Enters editing mode.
  void startEditing({required int lineIndex, required bool isAddingMark}) {
    final current = state;
    if (current is AnnotationLoaded) {
      emit(current.copyWith(
        selectedLineIndex: () => lineIndex,
        editing: () => EditingContext(
          lineIndex: lineIndex,
          isAddingMark: isAddingMark,
        ),
      ));
    }
  }

  /// Exits editing mode.
  void cancelEditing() {
    final current = state;
    if (current is AnnotationLoaded) {
      emit(current.copyWith(editing: () => null));
    }
  }

  /// Adds a text mark.
  Future<void> addMark({
    required int lineIndex,
    required int startOffset,
    required int endOffset,
    required MarkType type,
  }) async {
    final scriptId = _scriptId;
    if (scriptId == null) return;
    final mark = TextMark(
      id: _uuid.v4(),
      lineIndex: lineIndex,
      startOffset: startOffset,
      endOffset: endOffset,
      type: type,
      createdAt: DateTime.now().toUtc(),
    );
    await _dao.insertMark(scriptId, mark);
  }

  /// Removes a text mark.
  Future<void> removeMark(String id) => _dao.deleteMark(id);

  /// Adds a line note.
  Future<void> addNote({
    required int lineIndex,
    required NoteCategory category,
    required String text,
  }) async {
    final scriptId = _scriptId;
    if (scriptId == null) return;
    final note = LineNote(
      id: _uuid.v4(),
      lineIndex: lineIndex,
      category: category,
      text: text,
      createdAt: DateTime.now().toUtc(),
    );
    await _dao.insertNote(scriptId, note);
  }

  /// Updates a note's text.
  Future<void> updateNote(String id, String text) =>
      _dao.updateNoteText(id, text);

  /// Removes a note.
  Future<void> removeNote(String id) => _dao.deleteNote(id);

  @override
  Future<void> close() {
    _marksSub?.cancel();
    _notesSub?.cancel();
    return super.close();
  }
}
