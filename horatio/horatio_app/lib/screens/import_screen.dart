import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/bloc/script_import/script_import_cubit.dart';
import 'package:horatio_app/bloc/script_import/script_import_state.dart';
import 'package:horatio_app/router.dart';

/// Screen for importing scripts from file or pasting text.
class ImportScreen extends StatefulWidget {
  /// Creates an [ImportScreen].
  const ImportScreen({super.key});

  @override
  State<ImportScreen> createState() => _ImportScreenState();
}

class _ImportScreenState extends State<ImportScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  final _titleController = TextEditingController();
  final _textController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _titleController.dispose();
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) =>
      BlocListener<ScriptImportCubit, ScriptImportState>(
        listener: (context, state) {
          if (state is ScriptImportLoaded && state.scripts.isNotEmpty) {
            // Navigate to role selection with the newly imported script.
            final script = state.scripts.last;
            context.pushReplacement(
              RoutePaths.roleSelection,
              extra: script,
            );
          } else if (state is ScriptImportError) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(state.message),
                backgroundColor: Colors.red,
              ),
            );
          }
        },
        child: Scaffold(
          appBar: AppBar(
            title: const Text('Import Script'),
            bottom: TabBar(
              controller: _tabController,
              tabs: const [
                Tab(icon: Icon(Icons.upload_file), text: 'From File'),
                Tab(icon: Icon(Icons.edit_note), text: 'Paste Text'),
              ],
            ),
          ),
          body: TabBarView(
            controller: _tabController,
            children: [
              _FileImportTab(
                onImport: () =>
                    context.read<ScriptImportCubit>().importFromFile(),
              ),
              _TextImportTab(
                titleController: _titleController,
                textController: _textController,
                onImport: () {
                  final title = _titleController.text.trim();
                  final text = _textController.text.trim();
                  if (title.isEmpty || text.isEmpty) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Title and script text are required.'),
                      ),
                    );
                    return;
                  }
                  context
                      .read<ScriptImportCubit>()
                      .importFromText(text: text, title: title);
                },
              ),
            ],
          ),
        ),
      );
}

class _FileImportTab extends StatelessWidget {
  const _FileImportTab({required this.onImport});

  final VoidCallback onImport;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.upload_file,
                size: 80,
                color:
                    Theme.of(context).colorScheme.primary.withValues(alpha: 0.5),
              ),
              const SizedBox(height: 24),
              const Text(
                'Import a script file (.txt, .docx, .pdf)',
                style: TextStyle(fontSize: 18),
              ),
              const SizedBox(height: 8),
              const Text(
                'Character names should be followed by colons\n'
                'or in UPPERCASE on their own line.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              FilledButton.icon(
                onPressed: onImport,
                icon: const Icon(Icons.folder_open),
                label: const Text('Choose File'),
              ),
            ],
          ),
        ),
      );
}

class _TextImportTab extends StatelessWidget {
  const _TextImportTab({
    required this.titleController,
    required this.textController,
    required this.onImport,
  });

  final TextEditingController titleController;
  final TextEditingController textController;
  final VoidCallback onImport;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: titleController,
              decoration: const InputDecoration(
                labelText: 'Script Title',
                hintText: 'e.g. Hamlet Act 3 Scene 1',
              ),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: TextField(
                controller: textController,
                decoration: const InputDecoration(
                  labelText: 'Script Text',
                  hintText: 'Paste your script here...',
                  alignLabelWithHint: true,
                ),
                maxLines: null,
                expands: true,
                textAlignVertical: TextAlignVertical.top,
              ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onImport,
              icon: const Icon(Icons.check),
              label: const Text('Import'),
            ),
          ],
        ),
      );
}
