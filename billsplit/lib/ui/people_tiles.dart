/// Person and group tile widgets.
///
/// Split out of people_screen.dart to keep it under the 250-line cap. A `part`
/// because Dart privates are library-scoped.

part of 'people_screen.dart';

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
