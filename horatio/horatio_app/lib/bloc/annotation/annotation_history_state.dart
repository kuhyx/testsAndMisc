import 'package:equatable/equatable.dart';
import 'package:horatio_core/horatio_core.dart';

/// State for [AnnotationHistoryCubit].
sealed class AnnotationHistoryState extends Equatable {
  const AnnotationHistoryState();
}

/// No snapshots loaded.
final class AnnotationHistoryInitial extends AnnotationHistoryState {
  const AnnotationHistoryInitial();

  @override
  List<Object?> get props => [];
}

/// Snapshots loaded for a script.
final class AnnotationHistoryLoaded extends AnnotationHistoryState {
  const AnnotationHistoryLoaded({
    required this.scriptId,
    required this.snapshots,
  });

  final String scriptId;
  final List<AnnotationSnapshot> snapshots;

  @override
  List<Object?> get props => [scriptId, snapshots];
}
