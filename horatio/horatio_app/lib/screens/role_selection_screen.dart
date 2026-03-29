import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_core/horatio_core.dart';

/// Screen for choosing which role the actor wants to play.
class RoleSelectionScreen extends StatelessWidget {
  /// Creates a [RoleSelectionScreen].
  const RoleSelectionScreen({required this.script, super.key});

  /// The parsed script.
  final Script script;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(script.title),
        ),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Choose Your Role',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                '${script.scenes.length} scenes · '
                '${script.totalLineCount} lines total',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              Expanded(
                child: ListView.builder(
                  itemCount: script.roles.length,
                  itemBuilder: (context, index) {
                    final role = script.roles[index];
                    final lineCount = script.lineCountForRole(role);
                    return Card(
                      child: ListTile(
                        leading: CircleAvatar(
                          child: Text(
                            role.name.isNotEmpty
                                ? role.name[0].toUpperCase()
                                : '?',
                          ),
                        ),
                        title: Text(role.name),
                        subtitle: Text('$lineCount lines'),
                        trailing: const Icon(Icons.arrow_forward),
                        onTap: () => _navigateWithRole(context, role),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      );

  void _navigateWithRole(BuildContext context, Role role) {
    showModalBottomSheet<void>(
      context: context,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Practice "${role.name}"',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 24),
              ListTile(
                leading: const Icon(Icons.play_circle_outline),
                title: const Text('Rehearsal Mode'),
                subtitle: const Text('Practice dialogue with cue lines'),
                onTap: () {
                  Navigator.pop(context);
                  context.push(
                    RoutePaths.rehearsal,
                    extra: {'script': script, 'role': role},
                  );
                },
              ),
              ListTile(
                leading: const Icon(Icons.calendar_today),
                title: const Text('Memorization Schedule'),
                subtitle: const Text('Plan your memorization over days'),
                onTap: () {
                  Navigator.pop(context);
                  context.push(
                    RoutePaths.schedule,
                    extra: {'script': script, 'role': role},
                  );
                },
              ),
              ListTile(
                leading: const Icon(Icons.edit_note),
                title: const Text('Annotate Script'),
                subtitle: const Text('Add delivery marks and notes'),
                onTap: () {
                  Navigator.pop(context);
                  context.push(RoutePaths.annotations, extra: script);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
