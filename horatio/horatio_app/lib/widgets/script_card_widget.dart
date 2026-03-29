import 'package:flutter/material.dart';
import 'package:horatio_core/horatio_core.dart';

/// A card widget showing script summary info.
class ScriptCardWidget extends StatelessWidget {
  /// Creates a [ScriptCardWidget].
  const ScriptCardWidget({
    required this.script,
    required this.onTap,
    this.onDelete,
    super.key,
  });

  /// The script to display.
  final Script script;

  /// Called when the card is tapped.
  final VoidCallback onTap;

  /// Called when the delete action is triggered.
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          leading: const Icon(Icons.theater_comedy, size: 40),
          title: Text(
            script.title,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          subtitle: Text(
            '${script.roles.length} roles · '
            '${script.scenes.length} scenes · '
            '${script.totalLineCount} lines',
          ),
          trailing: onDelete != null
              ? IconButton(
                  icon: const Icon(Icons.delete_outline),
                  onPressed: onDelete,
                )
              : const Icon(Icons.chevron_right),
          onTap: onTap,
        ),
      );
}
