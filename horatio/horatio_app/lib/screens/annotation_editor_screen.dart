import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/bloc/annotation/annotation_cubit.dart';
import 'package:horatio_app/bloc/annotation/annotation_history_cubit.dart';
import 'package:horatio_app/bloc/annotation/annotation_state.dart';
import 'package:horatio_app/bloc/recording/recording_cubit.dart';
import 'package:horatio_app/bloc/recording/recording_state.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:horatio_app/services/recording_service.dart';
import 'package:horatio_app/widgets/mark_overlay.dart';
import 'package:horatio_app/widgets/mark_selection_toolbar.dart';
import 'package:horatio_app/widgets/note_chip.dart';
import 'package:horatio_app/widgets/note_editor_sheet.dart';
import 'package:horatio_app/widgets/note_indicator.dart';
import 'package:horatio_app/widgets/recording_action_bar.dart';
import 'package:horatio_app/widgets/recording_badge.dart';
import 'package:horatio_app/widgets/recording_list_sheet.dart';
import 'package:horatio_app/widgets/text_scale_settings_sheet.dart';
import 'package:horatio_core/horatio_core.dart';

/// Screen for editing text marks and line notes on a script.
class AnnotationEditorScreen extends StatelessWidget {
  /// Creates an [AnnotationEditorScreen].
  const AnnotationEditorScreen({required this.script, super.key});

  /// The script to annotate.
  final Script script;

  @override
  Widget build(BuildContext context) {
    final annotationDao = context.read<AnnotationDao>();
    return MultiBlocProvider(
      providers: [
        BlocProvider(
          create: (_) =>
              AnnotationCubit(dao: annotationDao)..loadAnnotations(script.id),
        ),
        BlocProvider(
          create: (_) =>
              AnnotationHistoryCubit(dao: annotationDao)
                ..loadSnapshots(script.id),
        ),
        BlocProvider(
          create: (context) => RecordingCubit(
            dao: context.read<RecordingDao>(),
            recordingService: context.read<RecordingService>(),
            playbackService: context.read<AudioPlaybackService>(),
            recordingsDir: context.read<String>(),
            disposeServicesOnClose: false,
          )..loadRecordings(script.id),
        ),
      ],
      child: _AnnotationEditorBody(script: script),
    );
  }
}

class _AnnotationEditorBody extends StatelessWidget {
  const _AnnotationEditorBody({required this.script});

  final Script script;

  List<ScriptLine> get _allLines =>
      script.scenes.expand((s) => s.lines).toList();

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text('Annotate: ${script.title}'),
      actions: [
        IconButton(
          icon: const Icon(Icons.text_fields),
          tooltip: 'Text Size',
          onPressed: () => showModalBottomSheet<void>(
            context: context,
            builder: (_) => BlocProvider.value(
              value: context.read<TextScaleCubit>(),
              child: const TextScaleSettingsSheet(),
            ),
          ),
        ),
        IconButton(
          icon: const Icon(Icons.history),
          tooltip: 'History',
          onPressed: () =>
              context.push(RoutePaths.annotationHistory, extra: script),
        ),
      ],
    ),
    floatingActionButton: BlocBuilder<AnnotationCubit, AnnotationState>(
      builder: (context, state) {
        if (state is! AnnotationLoaded) {
          return const SizedBox.shrink();
        }
        return FloatingActionButton(
          onPressed: () => _saveSnapshot(context, state),
          tooltip: 'Save Snapshot',
          child: const Icon(Icons.save),
        );
      },
    ),
    body: BlocBuilder<AnnotationCubit, AnnotationState>(
      builder: (context, annotationState) => switch (annotationState) {
        AnnotationInitial() => const Center(child: CircularProgressIndicator()),
        AnnotationLoaded() => Column(
          children: [
            Expanded(child: _buildLineList(context, annotationState)),
            if (annotationState.selectedLineIndex != null)
              BlocBuilder<RecordingCubit, RecordingState>(
                builder: (context, recordingState) {
                  final lineIndex = annotationState.selectedLineIndex!;
                  final recordingsForLine = recordingState.recordings
                      .where((r) => r.lineIndex == lineIndex)
                      .toList();
                  final latestRecording = recordingsForLine.isNotEmpty
                      ? recordingsForLine.last
                      : null;
                  final isRecording =
                      recordingState is RecordingInProgress &&
                      recordingState.lineIndex == lineIndex;
                  final elapsed = isRecording
                      ? recordingState.elapsed
                      : Duration.zero;

                  return RecordingActionBar(
                    isRecording: isRecording,
                    elapsed: elapsed,
                    latestRecording: latestRecording,
                    onRecord: () => context
                        .read<RecordingCubit>()
                        .startRecording(script.id, lineIndex),
                    onStop: () =>
                        context.read<RecordingCubit>().stopRecording(),
                    onPlay: () {
                      if (latestRecording != null) {
                        context.read<RecordingCubit>().playRecording(
                          latestRecording,
                        );
                      }
                    },
                  );
                },
              ),
          ],
        ),
      },
    ),
  );

  Widget _buildLineList(BuildContext context, AnnotationLoaded state) {
    final lines = _allLines;
    return ListView.builder(
      itemCount: lines.length,
      itemBuilder: (context, index) {
        final line = lines[index];
        final lineMarks = state.marks
            .where((m) => m.lineIndex == index)
            .toList();
        final lineNotes = state.notes
            .where((n) => n.lineIndex == index)
            .toList();
        final isSelected = state.selectedLineIndex == index;
        return _LineTile(
          line: line,
          lineIndex: index,
          marks: lineMarks,
          notes: lineNotes,
          isSelected: isSelected,
        );
      },
    );
  }

  void _saveSnapshot(BuildContext context, AnnotationLoaded state) {
    context.read<AnnotationHistoryCubit>().saveSnapshot(
      marks: state.marks,
      notes: state.notes,
    );
  }
}

class _LineTile extends StatefulWidget {
  const _LineTile({
    required this.line,
    required this.lineIndex,
    required this.marks,
    required this.notes,
    required this.isSelected,
  });

  final ScriptLine line;
  final int lineIndex;
  final List<TextMark> marks;
  final List<LineNote> notes;
  final bool isSelected;

  @override
  State<_LineTile> createState() => _LineTileState();
}

class _LineTileState extends State<_LineTile> {
  final LayerLink _layerLink = LayerLink();
  OverlayEntry? _toolbarOverlay;
  TextSelection? _selection;
  final List<TapGestureRecognizer> _recognizers = [];

  @override
  void dispose() {
    _removeToolbar();
    _disposeRecognizers();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant _LineTile oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!widget.isSelected && oldWidget.isSelected) {
      _removeToolbar();
    }
  }

  void _disposeRecognizers() {
    for (final r in _recognizers) {
      r.dispose();
    }
    _recognizers.clear();
  }

  void _removeToolbar() {
    _toolbarOverlay?.remove();
    _toolbarOverlay = null;
  }

  void _onSelectionChanged(
    TextSelection selection,
    SelectionChangedCause? cause,
  ) {
    _removeToolbar();
    if (selection.isCollapsed) {
      _selection = null;
      return;
    }
    _selection = selection;
    _showToolbar();
  }

  void _showToolbar() {
    final overlay = Overlay.of(context);
    _toolbarOverlay = OverlayEntry(
      builder: (context) => Positioned(
        width: MediaQuery.of(context).size.width,
        child: CompositedTransformFollower(
          link: _layerLink,
          showWhenUnlinked: false,
          offset: const Offset(0, -48),
          child: Align(
            alignment: Alignment.centerLeft,
            child: MarkSelectionToolbar(
              onMarkSelected: _applyMark,
              onCancelled: _removeToolbar,
            ),
          ),
        ),
      ),
    );
    overlay.insert(_toolbarOverlay!);
  }

  void _applyMark(MarkType type) {
    final sel = _selection;
    if (sel == null || sel.isCollapsed) return;
    context.read<AnnotationCubit>().addMark(
      lineIndex: widget.lineIndex,
      startOffset: sel.start,
      endOffset: sel.end,
      type: type,
    );
    _removeToolbar();
  }

  void _showRemoveMarkDialog(String markId) {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Remove mark?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('No'),
          ),
          TextButton(
            onPressed: () {
              context.read<AnnotationCubit>().removeMark(markId);
              Navigator.pop(dialogContext);
            },
            child: const Text('Yes'),
          ),
        ],
      ),
    );
  }

  List<TextSpan> _buildSpans() {
    _disposeRecognizers();
    final text = widget.line.text;
    final marks = widget.marks;
    if (marks.isEmpty) return [TextSpan(text: text)];

    final length = text.length;
    final events = <({int offset, bool isStart, MarkType type})>[];
    for (final mark in marks) {
      final s = mark.startOffset.clamp(0, length);
      final e = mark.endOffset.clamp(0, length);
      if (s >= e) continue;
      events
        ..add((offset: s, isStart: true, type: mark.type))
        ..add((offset: e, isStart: false, type: mark.type));
    }
    events.sort((a, b) => a.offset.compareTo(b.offset));

    final spans = <TextSpan>[];
    var cursor = 0;
    final activeTypes = <MarkType>[];
    for (final event in events) {
      final pos = event.offset.clamp(0, length);
      if (pos > cursor) {
        if (activeTypes.isNotEmpty) {
          final markForSpan = marks.firstWhere(
            (m) =>
                m.startOffset <= cursor &&
                m.endOffset >= pos &&
                m.type == activeTypes.last,
          );
          final recognizer = TapGestureRecognizer()
            ..onTap = () => _showRemoveMarkDialog(markForSpan.id);
          _recognizers.add(recognizer);
          spans.add(
            TextSpan(
              text: text.substring(cursor, pos),
              style: TextStyle(backgroundColor: markColors[activeTypes.last]),
              recognizer: recognizer,
            ),
          );
        } else {
          spans.add(TextSpan(text: text.substring(cursor, pos)));
        }
        cursor = pos;
      }
      if (event.isStart) {
        activeTypes.add(event.type);
      } else {
        activeTypes.remove(event.type);
      }
    }
    if (cursor < length) {
      spans.add(TextSpan(text: text.substring(cursor)));
    }
    return spans;
  }

  @override
  Widget build(BuildContext context) => Container(
    color: widget.isSelected
        ? Theme.of(context).colorScheme.primaryContainer.withValues(alpha: 0.3)
        : null,
    child: InkWell(
      onTap: () => context.read<AnnotationCubit>().selectLine(widget.lineIndex),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: widget.isSelected
                      ? CompositedTransformTarget(
                          link: _layerLink,
                          child: SelectableText.rich(
                            TextSpan(
                              style: DefaultTextStyle.of(context).style,
                              children: _buildSpans(),
                            ),
                            onSelectionChanged: _onSelectionChanged,
                          ),
                        )
                      : MarkOverlay(
                          text: widget.line.text,
                          marks: widget.marks,
                        ),
                ),
                BlocBuilder<RecordingCubit, RecordingState>(
                  builder: (context, recordingState) {
                    final recordingsForLine = recordingState.recordings
                        .where((r) => r.lineIndex == widget.lineIndex)
                        .toList();
                    return RecordingBadge(
                      recordingCount: recordingsForLine.length,
                      onTap: () =>
                          _showRecordingList(context, recordingsForLine),
                    );
                  },
                ),
                IconButton(
                  icon: const Icon(Icons.note_add_outlined),
                  tooltip: 'Add Note',
                  onPressed: () => _showNoteEditor(context),
                ),
                NoteIndicator(
                  noteCount: widget.notes.length,
                  onTap: () => _showNoteEditor(context),
                ),
              ],
            ),
            if (widget.isSelected && widget.notes.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Wrap(
                  spacing: 4,
                  runSpacing: 4,
                  children: widget.notes
                      .map(
                        (note) => NoteChip(
                          note: note,
                          onTap: () => _showNoteEditorForEdit(context, note),
                          onDelete: () => context
                              .read<AnnotationCubit>()
                              .removeNote(note.id),
                        ),
                      )
                      .toList(),
                ),
              ),
          ],
        ),
      ),
    ),
  );

  void _showRecordingList(
    BuildContext context,
    List<LineRecording> recordings,
  ) {
    showModalBottomSheet<void>(
      context: context,
      builder: (_) => RecordingListSheet(
        recordings: recordings,
        onPlay: (recording) {
          Navigator.pop(context);
          context.read<RecordingCubit>().playRecording(recording);
        },
        onGrade: (id, grade) {
          context.read<RecordingCubit>().gradeRecording(id, grade);
        },
        onDelete: (id) {
          context.read<RecordingCubit>().deleteRecording(id);
        },
      ),
    );
  }

  void _showNoteEditor(BuildContext context) {
    final cubit = context.read<AnnotationCubit>();
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: NoteEditorSheet(
          onSave: (category, text, {String? noteId}) {
            cubit.addNote(
              lineIndex: widget.lineIndex,
              category: category,
              text: text,
            );
            Navigator.pop(context);
          },
          onCancel: () => Navigator.pop(context),
        ),
      ),
    );
  }

  void _showNoteEditorForEdit(BuildContext context, LineNote note) {
    final cubit = context.read<AnnotationCubit>();
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: NoteEditorSheet(
          initialCategory: note.category,
          initialText: note.text,
          noteId: note.id,
          onSave: (category, text, {String? noteId}) {
            cubit.updateNote(noteId ?? note.id, text: text, category: category);
            Navigator.pop(context);
          },
          onCancel: () => Navigator.pop(context),
        ),
      ),
    );
  }
}
