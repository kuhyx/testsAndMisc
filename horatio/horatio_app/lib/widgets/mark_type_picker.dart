import 'package:flutter/material.dart';
import 'package:horatio_app/widgets/mark_overlay.dart';
import 'package:horatio_core/horatio_core.dart';

/// User-facing label for each [MarkType].
String markTypeLabel(MarkType type) => switch (type) {
      MarkType.stress => 'Stress',
      MarkType.pause => 'Pause',
      MarkType.breath => 'Breath',
      MarkType.emphasis => 'Emphasis',
      MarkType.slowDown => 'Slow Down',
      MarkType.speedUp => 'Speed Up',
    };

/// A picker displaying all [MarkType] options as colored chips.
class MarkTypePicker extends StatelessWidget {
  /// Creates a [MarkTypePicker].
  const MarkTypePicker({
    required this.onSelected,
    required this.onCancelled,
    super.key,
  });

  /// Called when a mark type is tapped.
  final ValueChanged<MarkType> onSelected;

  /// Called when the picker is dismissed.
  final VoidCallback onCancelled;

  @override
  Widget build(BuildContext context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: MarkType.values.map((type) {
              final color = markColors[type]!;
              return ActionChip(
                label: Text(markTypeLabel(type)),
                backgroundColor: color,
                onPressed: () => onSelected(type),
              );
            }).toList(),
          ),
          const SizedBox(height: 16),
          TextButton(
            onPressed: onCancelled,
            child: const Text('Cancel'),
          ),
        ],
      );
}
