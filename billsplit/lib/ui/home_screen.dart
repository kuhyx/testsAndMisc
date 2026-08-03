import 'dart:async';
import 'dart:convert';

import 'package:billsplit/domain/eparagon_parser.dart';
import 'package:billsplit/domain/models.dart';
import 'package:billsplit/state/app_state.dart';
import 'package:billsplit/ui/people_screen.dart';
import 'package:billsplit/ui/receipt_screen.dart';
import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

/// Receipt list plus entry points for import / manual creation.
class HomeScreen extends StatelessWidget {
  /// Creates the home screen.
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('BillSplit'),
        actions: [
          IconButton(
            tooltip: 'People & groups',
            icon: const Icon(Icons.group),
            onPressed: () => unawaited(
              Navigator.push(
                context,
                MaterialPageRoute<void>(builder: (_) => const PeopleScreen()),
              ),
            ),
          ),
        ],
      ),
      body: !state.loaded
          ? const Center(child: CircularProgressIndicator())
          : state.receipts.isEmpty
              ? const _EmptyHint()
              : ListView.builder(
                  itemCount: state.receipts.length,
                  itemBuilder: (context, i) {
                    final r = state.receipts[i];
                    return Dismissible(
                      key: ValueKey(r.id),
                      direction: DismissDirection.endToStart,
                      background: Container(
                        color: Colors.red.shade300,
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: 16),
                        child: const Icon(Icons.delete, color: Colors.white),
                      ),
                      confirmDismiss: (_) => _confirmDelete(context, r),
                      onDismissed: (_) => state.removeReceipt(r),
                      child: ListTile(
                        title: Text(r.title),
                        subtitle: Text(
                          '${r.items.length} items · '
                          '${r.participantIds.length} people',
                        ),
                        trailing: Text(
                          formatPln(r.itemsTotalGr),
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        onTap: () => unawaited(
                          Navigator.push(
                            context,
                            MaterialPageRoute<void>(
                              builder: (_) => ReceiptScreen(receiptId: r.id),
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          FloatingActionButton.extended(
            heroTag: 'import',
            icon: const Icon(Icons.file_download),
            label: const Text('Import e-paragon'),
            onPressed: () => _import(context),
          ),
          const SizedBox(height: 12),
          FloatingActionButton.extended(
            heroTag: 'new',
            icon: const Icon(Icons.add),
            label: const Text('New receipt'),
            onPressed: () => _createManual(context),
          ),
        ],
      ),
    );
  }

  Future<bool> _confirmDelete(BuildContext context, Receipt r) async {
    return await showDialog<bool>(
          context: context,
          builder: (c) => AlertDialog(
            title: const Text('Delete receipt?'),
            content: Text('"${r.title}" will be removed permanently.'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(c, false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(c, true),
                child: const Text('Delete'),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _import(BuildContext context) async {
    final state = context.read<AppState>();
    final messenger = ScaffoldMessenger.of(context);
    final nav = Navigator.of(context);
    const jsonGroup = XTypeGroup(
      label: 'e-paragon',
      extensions: ['json'],
      // Android matches on MIME rather than extension; without this the
      // picker greys out every file.
      mimeTypes: ['application/json'],
      uniformTypeIdentifiers: ['public.json'],
    );
    final picked = await openFile(acceptedTypeGroups: [jsonGroup]);
    if (picked == null) return;
    final data = await picked.readAsBytes();
    try {
      final result = parseEParagonDetailed(utf8.decode(data));
      state.addReceipt(result.receipt);
      for (final w in result.warnings) {
        messenger.showSnackBar(SnackBar(content: Text(w)));
      }
      unawaited(
        nav.push(
          MaterialPageRoute<void>(
            builder: (_) => ReceiptScreen(receiptId: result.receipt.id),
          ),
        ),
      );
    } on EParagonParseException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(e.message)));
    } on Exception catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Import failed: $e')));
    }
  }

  Future<void> _createManual(BuildContext context) async {
    final state = context.read<AppState>();
    final nav = Navigator.of(context);
    final controller = TextEditingController();
    final title = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('New receipt'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Title'),
          onSubmitted: (v) => Navigator.pop(c, v),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, controller.text),
            child: const Text('Create'),
          ),
        ],
      ),
    );
    if (title == null || title.trim().isEmpty) return;
    final r = Receipt(id: Ids.next(), title: title.trim());
    state.addReceipt(r);
    unawaited(
      nav.push(
        MaterialPageRoute<void>(
          builder: (_) => ReceiptScreen(receiptId: r.id),
        ),
      ),
    );
  }
}

class _EmptyHint extends StatelessWidget {
  const _EmptyHint();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Text(
          'No receipts yet.\n\nAdd people first (top right), then import a '
          'Biedronka e-paragon JSON or create a receipt manually.',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ),
    );
  }
}
