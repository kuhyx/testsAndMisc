import 'package:billsplit/domain/models.dart';
import 'package:billsplit/state/app_state.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

/// Add ([item] == null) or edit an item. The user types amounts in złoty
/// ("12,34" or "12.34"); they are stored as int grosze.
Future<void> showItemEditDialog(
  BuildContext context,
  AppState state,
  Receipt receipt,
  Item? item,
) async {
  final name = TextEditingController(text: item?.name ?? '');
  final total = TextEditingController(
    text: item == null ? '' : _zl(item.totalGr),
  );
  final qty = TextEditingController(text: (item?.qty ?? 1).toString());
  var category = item?.category ?? Categories.general;
  final categories = <String>{
    Categories.general,
    Categories.alcohol,
    Categories.mixer,
    Categories.deposit,
    ...receipt.items.map((i) => i.category),
  }.toList();

  await showDialog<void>(
    context: context,
    builder: (c) => StatefulBuilder(
      builder: (c, setState) => AlertDialog(
        title: Text(item == null ? 'Add item' : 'Edit item'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: name,
                autofocus: item == null,
                decoration: const InputDecoration(labelText: 'Name'),
              ),
              TextField(
                controller: total,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  labelText: 'Total (zł)',
                  hintText: 'e.g. 12,34',
                ),
              ),
              TextField(
                controller: qty,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Quantity'),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: category,
                decoration: const InputDecoration(labelText: 'Category'),
                items: [
                  for (final cat in categories)
                    DropdownMenuItem(value: cat, child: Text(cat)),
                ],
                onChanged: (v) =>
                    setState(() => category = v ?? Categories.general),
              ),
              const SizedBox(height: 4),
              Text(
                'Alcohol items default to drinkers only; everything else to '
                'everyone. Fine-tune by tapping the item afterwards.',
                style: TextStyle(
                  fontSize: AppTextSize.caption,
                  color: Theme.of(c).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        actions: [
          if (item != null)
            TextButton(
              onPressed: () {
                state.mutate(() => receipt.items.remove(item));
                Navigator.pop(c);
              },
              child: Text(
                'Delete',
                style: TextStyle(color: Theme.of(c).colorScheme.error),
              ),
            ),
          TextButton(
            onPressed: () => Navigator.pop(c),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final gr = _parseZl(total.text);
              if (name.text.trim().isEmpty || gr == null) return;
              state.mutate(() {
                if (item == null) {
                  final it = Item(
                    id: Ids.next(),
                    name: name.text.trim(),
                    totalGr: gr,
                    qty: double.tryParse(qty.text.replaceAll(',', '.')) ?? 1,
                    category: category,
                    assignment: category == Categories.alcohol
                        ? Assignment(mode: AssignMode.drinkers)
                        : Assignment(),
                  );
                  receipt.items.add(it);
                } else {
                  item
                    ..name = name.text.trim()
                    ..totalGr = gr
                    ..qty = double.tryParse(qty.text.replaceAll(',', '.')) ?? 1
                    ..category = category;
                }
              });
              Navigator.pop(c);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    ),
  );
}

String _zl(int gr) => (gr / 100).toStringAsFixed(2);

int? _parseZl(String s) {
  final v = double.tryParse(s.replaceAll(',', '.').replaceAll(' ', ''));
  if (v == null) return null;
  return (v * 100).round();
}
