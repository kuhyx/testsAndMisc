import 'package:flutter/material.dart';
import 'package:horatio_app/widgets/mark_overlay.dart';
import 'package:horatio_app/widgets/mark_type_picker.dart';
import 'package:horatio_core/horatio_core.dart';

/// Floating toolbar showing mark type chips for text selection annotation.
class MarkSelectionToolbar extends StatelessWidget {
  /// Creates a [MarkSelectionToolbar].
  const MarkSelectionToolbar({
    required this.onMarkSelected,
    required this.onCancelled,
    super.key,
  });

  /// Called when a mark type chip is tapped.
  final ValueChanged<MarkType> onMarkSelected;

  /// Called when the action is cancelled.
  final VoidCallback onCancelled;

  @override
  Widget build(BuildContext context) => Material(
        elevation: 4,
        borderRadius: BorderRadius.circular(8),
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              ...MarkType.values.map(
                (type) => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: ActionChip(
                    label: Text(markTypeLabel(type)),
                    backgroundColor: markColors[type],
                    onPressed: () => onMarkSelected(type),
                  ),
                ),
              ),
              const SizedBox(width: 4),
              TextButton(
                onPressed: onCancelled,
                child: const Text('Cancel'),
              ),
            ],
          ),
        ),
      );
}
