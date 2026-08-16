/// The receipt item list and its row widgets.
///
/// Split out of receipt_screen.dart to keep it under the 250-line cap. A `part`
/// because Dart privates are library-scoped.

part of 'receipt_screen.dart';

class _ItemsList extends StatelessWidget {
  const _ItemsList({required this.receipt, required this.split});
  final Receipt receipt;
  final SplitResult split;

  @override
  Widget build(BuildContext context) {
    final state = context.read<AppState>();
    if (receipt.items.isEmpty) {
      return const Center(child: Text('No items — add with +.'));
    }
    return ListView.builder(
      padding: const EdgeInsets.only(bottom: 96),
      itemCount: receipt.items.length,
      itemBuilder: (context, i) {
        final item = receipt.items[i];
        final people =
            resolveParticipants(item, receipt, state.people, state.groups);
        final unassigned = people.isEmpty;
        return ListTile(
          dense: true,
          leading: _CategoryDot(category: item.category),
          title: Text(item.name),
          subtitle: Text(
            _assignmentLabel(item, people.length, state),
            style: TextStyle(
              color: unassigned ? Theme.of(context).colorScheme.error : null,
              fontWeight: unassigned ? FontWeight.bold : null,
            ),
          ),
          trailing: Text(formatPln(item.totalGr)),
          onTap: () => showAssignmentSheet(context, state, receipt, item),
          onLongPress: () => showItemEditDialog(context, state, receipt, item),
        );
      },
    );
  }

  String _assignmentLabel(Item item, int n, AppState state) {
    switch (item.assignment.mode) {
      case AssignMode.everyone:
        return 'Everyone ($n)';
      case AssignMode.drinkers:
        return 'Drinkers only ($n)';
      case AssignMode.nonDrinkers:
        return 'Non-drinkers ($n)';
      case AssignMode.group:
        final g = state.groups
            .where((g) => g.id == item.assignment.groupId)
            .firstOrNull;
        return 'Group: ${g?.name ?? '?'} ($n)';
      case AssignMode.custom:
        return n == 0 ? 'UNASSIGNED — tap to fix' : 'Selected people ($n)';
    }
  }
}

class _CategoryDot extends StatelessWidget {
  const _CategoryDot({required this.category});
  final String category;

  @override
  Widget build(BuildContext context) {
    final color = switch (category) {
      // Categorical encoding, deliberately NOT mapped onto ColorScheme slots.
      // These four say "which category", not "which theme role", and a
      // single-accent design system has no four distinct hues to lend. Folding
      // them into primary/secondary/tertiary would make the categories stop
      // being distinguishable, which is the only job they have. Tracked in
      // unified-design-system/nielsen-audit.md as needing a categorical ramp.
      Categories.alcohol => Colors.deepOrange,
      Categories.mixer => Colors.amber,
      Categories.deposit => Colors.blueGrey,
      _ => Colors.teal,
    };
    return CircleAvatar(radius: 6, backgroundColor: color);
  }
}

class _TotalsView extends StatelessWidget {
  const _TotalsView({required this.receipt, required this.split});
  final Receipt receipt;
  final SplitResult split;

  @override
  Widget build(BuildContext context) {
    final state = context.read<AppState>();
    final people = receiptParticipants(receipt, state.people)
      ..sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    final itemsTotal = receipt.itemsTotalGr;
    final assigned = split.assignedTotalGr;
    final paid = receipt.paidTotalGr;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (split.unassigned.isNotEmpty)
          Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(
                '${split.unassigned.length} item(s) have nobody assigned and '
                'are excluded from totals:\n'
                '${split.unassigned.map((i) => '· ${i.name}').join('\n')}',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onErrorContainer,
                ),
              ),
            ),
          ),
        for (final p in people)
          _PersonRow(person: p, total: split.perPerson[p.id]),
        const Divider(height: 32),
        _kv(context, 'Items total', formatPln(itemsTotal), bold: true),
        _kv(
          context,
          'Assigned to people',
          formatPln(assigned),
          warn: assigned != itemsTotal,
        ),
        if (paid != null)
          _kv(
            context,
            'Paid (receipt)',
            formatPln(paid),
            warn: paid != itemsTotal,
          ),
        const SizedBox(height: 8),
        Text(
          'Splits are grosz-exact: shares always add up to the item total, '
          'so no fractional grosze are lost.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }

  Widget _kv(
    BuildContext context,
    String k,
    String v, {
    bool bold = false,
    bool warn = false,
  }) {
    final style = TextStyle(
      fontWeight: bold || warn ? FontWeight.bold : null,
      color: warn ? Theme.of(context).colorScheme.error : null,
    );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [Text(k, style: style), Text(v, style: style)],
      ),
    );
  }
}

class _PersonRow extends StatelessWidget {
  const _PersonRow({required this.person, required this.total});
  final Person person;
  final PersonTotal? total;

  @override
  Widget build(BuildContext context) {
    final t = total;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: CircleAvatar(
        child: Text(
          person.name.isEmpty ? '?' : person.name.substring(0, 1).toUpperCase(),
        ),
      ),
      title: Text(person.name),
      subtitle: t == null || t.alcoholGr == 0
          ? null
          : Text(
              'alcohol ${formatPln(t.alcoholGr)} · rest ${formatPln(t.restGr)}',
            ),
      trailing: Text(
        formatPln(t?.totalGr ?? 0),
        style: Theme.of(context).textTheme.titleMedium,
      ),
    );
  }
}

extension<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
