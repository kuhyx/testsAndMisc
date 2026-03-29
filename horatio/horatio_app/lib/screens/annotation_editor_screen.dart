import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/bloc/annotation/annotation_cubit.dart';
import 'package:horatio_app/bloc/annotation/annotation_history_cubit.dart';
import 'package:horatio_app/bloc/annotation/annotation_state.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_app/widgets/mark_overlay.dart';
import 'package:horatio_app/widgets/mark_type_picker.dart';
import 'package:horatio_app/widgets/note_editor_sheet.dart';
import 'package:horatio_app/widgets/note_indicator.dart';
import 'package:horatio_core/horatio_core.dart';

/// Screen for editing text marks and line notes on a script.
class AnnotationEditorScreen extends StatelessWidget {
  /// Creates an [AnnotationEditorScreen].
  const AnnotationEditorScreen({required this.script, super.key});

  /// The script to annotate.
  final Script script;

  @override
  Widget build(BuildContext context) {
    final dao = context.read<AnnotationDao>();
    return MultiBlocProvider(
      providers: [
        BlocProvider(
          create: (_) =>
              AnnotationCubit(dao: dao)..loadAnnotations(script.id),
        ),
        BlocProvider(
          create: (_) =>
              AnnotationHistoryCubit(dao: dao)..loadSnapshots(script.id),
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
              icon: const Icon(Icons.history),
              tooltip: 'History',
              onPressed: () =>
                  context.push(RoutePaths.annotationHistory, extra: script),
            ),
          ],
        ),
        floatingActionButton:
            BlocBuilder<AnnotationCubit, AnnotationState>(
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
          builder: (context, state) => switch (state) {
            AnnotationInitial() =>
              const Center(child: CircularProgressIndicator()),
            AnnotationLoaded() => _buildLineList(context, state),
          },
        ),
      );

  Widget _buildLineList(BuildContext context, AnnotationLoaded state) {
    final lines = _allLines;
    return ListView.builder(
      itemCount: lines.length,
      itemBuilder: (context, index) {
        final line = lines[index];
        final lineMarks =
            state.marks.where((m) => m.lineIndex == index).toList();
        final lineNotes =
            state.notes.where((n) => n.lineIndex == index).toList();
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

class _LineTile extends StatelessWidget {
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
  Widget build(BuildContext context) => Container(
        color: isSelected
            ? Theme.of(context).colorScheme.primaryContainer.withValues(
                  alpha: 0.3,
                )
            : null,
        child: InkWell(
          onTap: () =>
              context.read<AnnotationCubit>().selectLine(lineIndex),
          onLongPress: () => _showMarkPicker(context),
          child: Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                Expanded(
                  child: MarkOverlay(text: line.text, marks: marks),
                ),
                NoteIndicator(
                  noteCount: notes.length,
                  onTap: () => _showNoteEditor(context),
                ),
              ],
            ),
          ),
        ),
      );

  void _showMarkPicker(BuildContext context) {
    final cubit = context.read<AnnotationCubit>();
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Add Mark'),
        content: MarkTypePicker(
          onSelected: (type) {
            cubit.addMark(
              lineIndex: lineIndex,
              startOffset: 0,
              endOffset: line.text.length,
              type: type,
            );
            Navigator.pop(context);
          },
          onCancelled: () => Navigator.pop(context),
        ),
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
          onSave: (category, text) {
            cubit.addNote(
              lineIndex: lineIndex,
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
}
