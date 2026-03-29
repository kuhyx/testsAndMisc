import 'dart:async';

import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/annotation/annotation_history_state.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:uuid/uuid.dart';

/// Manages annotation snapshot history for a script.
class AnnotationHistoryCubit extends Cubit<AnnotationHistoryState> {
  /// Creates an [AnnotationHistoryCubit].
  AnnotationHistoryCubit({required AnnotationDao dao})
      : _dao = dao,
        super(const AnnotationHistoryInitial());

  final AnnotationDao _dao;
  StreamSubscription<List<AnnotationSnapshot>>? _sub;
  String? _scriptId;

  static const _uuid = Uuid();

  /// Subscribes to snapshots for a script.
  void loadSnapshots(String scriptId) {
    _scriptId = scriptId;
    _sub?.cancel();
    _sub = _dao.watchSnapshotsForScript(scriptId).listen((snapshots) {
      emit(AnnotationHistoryLoaded(
        scriptId: scriptId,
        snapshots: snapshots,
      ));
    });
  }

  /// Saves current annotations as a snapshot.
  Future<void> saveSnapshot({
    required List<TextMark> marks,
    required List<LineNote> notes,
  }) async {
    final scriptId = _scriptId;
    if (scriptId == null) return;
    final snapshot = AnnotationSnapshot(
      id: _uuid.v4(),
      scriptId: scriptId,
      timestamp: DateTime.now().toUtc(),
      marks: marks,
      notes: notes,
    );
    await _dao.insertSnapshot(snapshot);
  }

  /// Restores annotations from a snapshot (destructive replace).
  Future<void> restoreSnapshot(AnnotationSnapshot snapshot) async {
    final scriptId = _scriptId;
    if (scriptId == null) return;
    await _dao.replaceAllAnnotations(
      scriptId: scriptId,
      marks: snapshot.marks,
      notes: snapshot.notes,
    );
  }

  @override
  Future<void> close() {
    _sub?.cancel();
    return super.close();
  }
}
