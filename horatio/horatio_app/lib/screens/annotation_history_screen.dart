import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/annotation/annotation_history_cubit.dart';
import 'package:horatio_app/bloc/annotation/annotation_history_state.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:intl/intl.dart';

/// Screen for browsing and restoring annotation snapshots.
class AnnotationHistoryScreen extends StatelessWidget {
  /// Creates an [AnnotationHistoryScreen].
  const AnnotationHistoryScreen({required this.script, super.key});

  /// The script whose history to browse.
  final Script script;

  @override
  Widget build(BuildContext context) => BlocProvider(
        create: (_) =>
            AnnotationHistoryCubit(dao: context.read<AnnotationDao>())
              ..loadSnapshots(script.id),
        child: _AnnotationHistoryBody(script: script),
      );
}

class _AnnotationHistoryBody extends StatelessWidget {
  const _AnnotationHistoryBody({required this.script});

  final Script script;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('History: ${script.title}')),
        body: BlocBuilder<AnnotationHistoryCubit, AnnotationHistoryState>(
          builder: (context, state) => switch (state) {
            AnnotationHistoryInitial() =>
              const Center(child: CircularProgressIndicator()),
            AnnotationHistoryLoaded(snapshots: final snapshots) =>
              snapshots.isEmpty
                  ? const Center(child: Text('No history yet'))
                  : ListView.builder(
                      itemCount: snapshots.length,
                      itemBuilder: (context, index) => _SnapshotCard(
                        snapshot: snapshots[index],
                      ),
                    ),
          },
        ),
      );
}

class _SnapshotCard extends StatelessWidget {
  const _SnapshotCard({required this.snapshot});

  final AnnotationSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final formatted =
        DateFormat.yMMMd().add_Hm().format(snapshot.timestamp.toLocal());
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ListTile(
        title: Text(formatted),
        subtitle: Text(
          '${snapshot.marks.length} marks · '
          '${snapshot.notes.length} notes',
        ),
        trailing: TextButton(
          onPressed: () => _confirmRestore(context),
          child: const Text('Restore'),
        ),
      ),
    );
  }

  void _confirmRestore(BuildContext context) {
    final cubit = context.read<AnnotationHistoryCubit>();
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Restore Snapshot?'),
        content: const Text(
          'This will replace all current annotations with the snapshot.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              cubit.restoreSnapshot(snapshot);
              Navigator.pop(context);
            },
            child: const Text('Restore'),
          ),
        ],
      ),
    );
  }
}
