import 'package:billsplit/domain/models.dart';
import 'package:billsplit/state/app_state.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

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
          const _SectionHeader('People'),
          if (state.people.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('Nobody yet — add people below.'),
            ),
          for (final p in state.people) _PersonTile(person: p),
          const Divider(height: 32),
          const _SectionHeader('Groups'),
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

class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
        child: Text(text, style: Theme.of(context).textTheme.titleMedium),
      );
}

class _PersonTile extends StatelessWidget {
  const _PersonTile({required this.person});
  final Person person;

  @override
  Widget build(BuildContext context) {
    final state = context.read<AppState>();
    return ListTile(
      leading: CircleAvatar(
        child: Text(
          person.name.isEmpty ? '?' : person.name.substring(0, 1).toUpperCase(),
        ),
      ),
      title: Text(person.name),
      subtitle: Wrap(
        spacing: 6,
        children: [
          for (final g in state.groups.where(
            (g) => g.memberIds.contains(person.id),
          ))
            Chip(
              label: Text(g.name, style: const TextStyle(fontSize: 11)),
              visualDensity: VisualDensity.compact,
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
        ],
      ),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Tooltip(
            message: 'Drinks alcohol',
            child: Switch(
              value: person.drinks,
              onChanged: (v) => state.mutate(() => person.drinks = v),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline),
            onPressed: () => _confirmRemove(context, state),
          ),
        ],
      ),
      onTap: () => _editMembership(context, state),
    );
  }

  Future<void> _confirmRemove(BuildContext context, AppState state) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text('Remove ${person.name}?'),
        content: const Text(
          'They will be removed from all receipts and item assignments.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, true),
            child: const Text('Remove'),
          ),
        ],
      ),
    );
    if (ok == true) state.removePerson(person);
  }

  Future<void> _editMembership(BuildContext context, AppState state) async {
    if (state.groups.isEmpty) return;
    await showModalBottomSheet<void>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, setState) => SafeArea(
          child: ListView(
            shrinkWrap: true,
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  '${person.name} — groups',
                  style: Theme.of(c).textTheme.titleMedium,
                ),
              ),
              for (final g in state.groups)
                CheckboxListTile(
                  title: Text(g.name),
                  value: g.memberIds.contains(person.id),
                  onChanged: (v) {
                    state.mutate(() {
                      if (v == true) {
                        g.memberIds.add(person.id);
                      } else {
                        g.memberIds.remove(person.id);
                      }
                    });
                    setState(() {});
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GroupTile extends StatelessWidget {
  const _GroupTile({required this.group});
  final Group group;

  @override
  Widget build(BuildContext context) {
    final state = context.read<AppState>();
    final names = state.people
        .where((p) => group.memberIds.contains(p.id))
        .map((p) => p.name)
        .join(', ');
    return ListTile(
      leading: const Icon(Icons.label_outline),
      title: Text(group.name),
      subtitle:
          Text(names.isEmpty ? 'No members — tap a person to add' : names),
      trailing: IconButton(
        icon: const Icon(Icons.delete_outline),
        onPressed: () => state.removeGroup(group),
      ),
    );
  }
}
