import 'package:billsplit/domain/models.dart';
import 'package:billsplit/state/app_state.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

part 'people_tiles.dart';

/// Roster management: people with a drinks toggle, plus custom groups.
class PeopleScreen extends StatelessWidget {
  /// Creates the people screen.
  const PeopleScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(title: const Text('People & groups')),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 96),
        children: [
          const SectionHeader('People', padding: SectionHeader.defaultPadding),
          if (state.people.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('Nobody yet — add people below.'),
            ),
          for (final p in state.people) _PersonTile(person: p),
          const Divider(height: 32),
          const SectionHeader('Groups', padding: SectionHeader.defaultPadding),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Text(
              'Drinkers / non-drinkers are built in (the toggle on each '
              'person). Groups below are extra tags, e.g. "meat eaters".',
              style: TextStyle(
                fontSize: AppTextSize.caption,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          for (final g in state.groups) _GroupTile(group: g),
          Padding(
            padding: const EdgeInsets.all(16),
            child: OutlinedButton.icon(
              icon: const Icon(Icons.add),
              label: const Text('Add group'),
              onPressed: () => _addGroup(context),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        icon: const Icon(Icons.person_add),
        label: const Text('Add person'),
        onPressed: () => _addPerson(context),
      ),
    );
  }

  Future<void> _addPerson(BuildContext context) async {
    final state = context.read<AppState>();
    final controller = TextEditingController();
    var drinks = true;
    await showDialog<void>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, setState) => AlertDialog(
          title: const Text('Add person'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: controller,
                autofocus: true,
                decoration: const InputDecoration(labelText: 'Name'),
              ),
              SwitchListTile(
                title: const Text('Drinks alcohol'),
                value: drinks,
                onChanged: (v) => setState(() => drinks = v),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                if (controller.text.trim().isNotEmpty) {
                  state.addPerson(controller.text.trim(), drinks: drinks);
                }
                Navigator.pop(c);
              },
              child: const Text('Add'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _addGroup(BuildContext context) async {
    final state = context.read<AppState>();
    final controller = TextEditingController();
    await showDialog<void>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Add group'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Group name'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              if (controller.text.trim().isNotEmpty) {
                state.addGroup(controller.text.trim());
              }
              Navigator.pop(c);
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }
}
