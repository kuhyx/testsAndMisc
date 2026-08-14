import 'package:billsplit/domain/models.dart';
import 'package:billsplit/domain/split_engine.dart';
import 'package:billsplit/state/app_state.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

/// Bottom sheet to assign an item: quick modes (everyone / drinkers /
/// non-drinkers / group) or explicit person selection. Toggling a person
/// checkbox on a non-custom mode first materializes the current selection,
/// then switches to custom.
Future<void> showAssignmentSheet(
  BuildContext context,
  AppState state,
  Receipt receipt,
  Item item,
) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (c) => StatefulBuilder(
      builder: (c, setSheet) {
        final pool = receiptParticipants(receipt, state.people)
          ..sort(
            (a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()),
          );
        final resolved =
            resolveParticipants(item, receipt, state.people, state.groups)
                .map((p) => p.id)
                .toSet();

        void setMode(AssignMode mode, {String? groupId}) {
          state.mutate(() {
            item.assignment
              ..mode = mode
              ..groupId = groupId;
          });
          setSheet(() {});
        }

        void togglePerson(Person p, {required bool selected}) {
          state.mutate(() {
            if (item.assignment.mode != AssignMode.custom) {
              item.assignment
                ..customIds.clear()
                ..customIds.addAll(resolved)
                ..mode = AssignMode.custom
                ..groupId = null;
            }
            if (selected) {
              item.assignment.customIds.add(p.id);
            } else {
              item.assignment.customIds.remove(p.id);
            }
          });
          setSheet(() {});
        }

        final selectedSeg = switch (item.assignment.mode) {
          AssignMode.everyone => 'everyone',
          AssignMode.drinkers => 'drinkers',
          AssignMode.nonDrinkers => 'nonDrinkers',
          AssignMode.group => 'group:${item.assignment.groupId}',
          AssignMode.custom => 'custom',
        };

        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.name, style: Theme.of(c).textTheme.titleMedium),
                Text(
                  '${formatPln(item.totalGr)} · ${item.category}',
                  style: Theme.of(c).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    ChoiceChip(
                      label: const Text('Everyone'),
                      selected: selectedSeg == 'everyone',
                      onSelected: (_) => setMode(AssignMode.everyone),
                    ),
                    ChoiceChip(
                      label: const Text('Drinkers'),
                      selected: selectedSeg == 'drinkers',
                      onSelected: (_) => setMode(AssignMode.drinkers),
                    ),
                    ChoiceChip(
                      label: const Text('Non-drinkers'),
                      selected: selectedSeg == 'nonDrinkers',
                      onSelected: (_) => setMode(AssignMode.nonDrinkers),
                    ),
                    for (final g in state.groups)
                      ChoiceChip(
                        label: Text(g.name),
                        selected: selectedSeg == 'group:${g.id}',
                        onSelected: (_) =>
                            setMode(AssignMode.group, groupId: g.id),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                Flexible(
                  child: ListView(
                    shrinkWrap: true,
                    children: [
                      for (final p in pool)
                        CheckboxListTile(
                          dense: true,
                          title: Text(p.name),
                          subtitle: p.drinks ? null : const Text('non-drinker'),
                          value: resolved.contains(p.id),
                          onChanged: (v) =>
                              togglePerson(p, selected: v ?? false),
                        ),
                    ],
                  ),
                ),
                Text(
                  resolved.isEmpty
                      ? 'Nobody selected — this item will be excluded from '
                          'totals until someone is assigned.'
                      : _eachLabel(resolved.length, item.totalGr),
                  style: TextStyle(
                    color: resolved.isEmpty
                        ? Theme.of(c).colorScheme.error
                        : Theme.of(c).colorScheme.onSurfaceVariant,
                    fontSize: AppTextSize.caption,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    ),
  );
}

String _eachLabel(int n, int totalGr) =>
    '$n people · ~${formatPln((totalGr / n).round())} each';
