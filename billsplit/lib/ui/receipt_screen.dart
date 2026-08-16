import 'package:billsplit/domain/models.dart';
import 'package:billsplit/domain/split_engine.dart';
import 'package:billsplit/domain/xlsx_export.dart';
import 'package:billsplit/state/app_state.dart';
import 'package:billsplit/ui/assignment_sheet.dart';
import 'package:billsplit/ui/item_edit.dart';
import 'package:file_selector/file_selector.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

part 'receipt_items.dart';

/// Writes exported [bytes] to [path]; the seam the export flow writes through.
///
/// Kept injectable because `file_selector` only returns a destination — the
/// app performs the write itself, where `file_picker` did it inside the
/// plugin. Real `dart:io` futures never complete inside `testWidgets`'
/// fake-async zone, so a widget test that exercised the real write could never
/// observe the resulting snackbar. Tests swap this for an in-memory stub.
typedef ExportWriter = Future<void> Function(
  String path,
  Uint8List bytes,
  String mimeType,
);

/// The active export writer. Replaced in tests via [debugSetExportWriter].
ExportWriter writeExport = _writeExportToDisk;

Future<void> _writeExportToDisk(
  String path,
  Uint8List bytes,
  String mimeType,
) =>
    XFile.fromData(bytes, mimeType: mimeType).saveTo(path);

/// Overrides [writeExport]; pass null to restore the real disk writer.
@visibleForTesting
void debugSetExportWriter(ExportWriter? writer) {
  writeExport = writer ?? _writeExportToDisk;
}

/// One receipt: item list with assignments, totals, participants, export.
class ReceiptScreen extends StatefulWidget {
  /// Creates the screen for the receipt with [receiptId].
  const ReceiptScreen({required this.receiptId, super.key});

  /// Id of the receipt to show; resolved against [AppState.receipts].
  final String receiptId;

  @override
  State<ReceiptScreen> createState() => _ReceiptScreenState();
}

class _ReceiptScreenState extends State<ReceiptScreen> {
  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final receipt =
        state.receipts.where((r) => r.id == widget.receiptId).firstOrNull;
    if (receipt == null) {
      return const Scaffold(body: Center(child: Text('Receipt deleted.')));
    }
    final split = computeSplit(receipt, state.people, state.groups);
    final wide = MediaQuery.of(context).size.width > 800;

    final itemsList = _ItemsList(receipt: receipt, split: split);
    final totals = _TotalsView(receipt: receipt, split: split);

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(receipt.title, overflow: TextOverflow.ellipsis),
          actions: [
            IconButton(
              tooltip: 'Participants',
              icon: const Icon(Icons.group),
              onPressed: () => _editParticipants(context, state, receipt),
            ),
            IconButton(
              tooltip: 'Export .xlsx',
              icon: const Icon(Icons.table_view),
              onPressed: () => _export(context, state, receipt),
            ),
          ],
          bottom: wide
              ? null
              : const TabBar(
                  tabs: [
                    Tab(text: 'Items'),
                    Tab(text: 'Totals'),
                  ],
                ),
        ),
        floatingActionButton: FloatingActionButton(
          tooltip: 'Add item',
          child: const Icon(Icons.add),
          onPressed: () => showItemEditDialog(context, state, receipt, null),
        ),
        body: wide
            ? Row(
                children: [
                  Expanded(flex: 3, child: itemsList),
                  const VerticalDivider(width: 1),
                  Expanded(flex: 2, child: totals),
                ],
              )
            : TabBarView(children: [itemsList, totals]),
      ),
    );
  }

  Future<void> _editParticipants(
    BuildContext context,
    AppState state,
    Receipt receipt,
  ) async {
    if (state.people.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Add people first (People & groups screen).'),
        ),
      );
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, setSheet) => SafeArea(
          child: ListView(
            shrinkWrap: true,
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  'Who is on this receipt?',
                  style: Theme.of(c).textTheme.titleMedium,
                ),
              ),
              for (final p in state.people)
                CheckboxListTile(
                  title: Text(p.name),
                  subtitle: p.drinks ? null : const Text('non-drinker'),
                  value: receipt.participantIds.contains(p.id),
                  onChanged: (v) {
                    state.mutate(() {
                      if (v == true) {
                        receipt.participantIds.add(p.id);
                      } else {
                        receipt.participantIds.remove(p.id);
                      }
                    });
                    setSheet(() {});
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _export(
    BuildContext context,
    AppState state,
    Receipt receipt,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    if (receipt.participantIds.isEmpty) {
      messenger.showSnackBar(
        const SnackBar(content: Text('Add participants before exporting.')),
      );
      return;
    }
    try {
      final bytes = Uint8List.fromList(
        exportXlsx(
          receipt: receipt,
          roster: state.people,
          groups: state.groups,
        ),
      );
      final safe = receipt.title.replaceAll(
        RegExp(r'[^\w\d ąćęłńóśżźĄĆĘŁŃÓŚŻŹ-]'),
        '_',
      );
      const xlsxGroup = XTypeGroup(
        label: 'Excel workbook',
        extensions: ['xlsx'],
        mimeTypes: [
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ],
      );
      final location = await getSaveLocation(
        suggestedName: '$safe split.xlsx',
        acceptedTypeGroups: [xlsxGroup],
      );
      if (location != null) {
        // file_selector hands back a destination and leaves the writing to the
        // caller, unlike file_picker which wrote the bytes inside the plugin.
        await writeExport(location.path, bytes, xlsxGroup.mimeTypes!.first);
        messenger.showSnackBar(
          SnackBar(content: Text('Saved: ${location.path.split('/').last}')),
        );
      }
    } on Exception catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Export failed: $e')));
    }
  }
}
