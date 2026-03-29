import 'package:flutter/material.dart';
import 'package:horatio_core/horatio_core.dart';

/// User-facing label for each [NoteCategory].
String noteCategoryLabel(NoteCategory category) => switch (category) {
      NoteCategory.intention => 'Intention',
      NoteCategory.subtext => 'Subtext',
      NoteCategory.blocking => 'Blocking',
      NoteCategory.emotion => 'Emotion',
      NoteCategory.delivery => 'Delivery',
      NoteCategory.general => 'General',
    };

/// A bottom-sheet widget for creating or editing a [LineNote].
class NoteEditorSheet extends StatefulWidget {
  /// Creates a [NoteEditorSheet].
  const NoteEditorSheet({
    required this.onSave,
    required this.onCancel,
    this.initialCategory,
    this.initialText,
    super.key,
  });

  /// Called with the chosen category and text on save.
  final void Function(NoteCategory category, String text) onSave;

  /// Called when the user cancels editing.
  final VoidCallback onCancel;

  /// Pre-selected category when editing an existing note.
  final NoteCategory? initialCategory;

  /// Pre-filled text when editing an existing note.
  final String? initialText;

  @override
  State<NoteEditorSheet> createState() => _NoteEditorSheetState();
}

class _NoteEditorSheetState extends State<NoteEditorSheet> {
  late NoteCategory _category;
  late TextEditingController _textController;
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    _category = widget.initialCategory ?? NoteCategory.general;
    _textController = TextEditingController(text: widget.initialText ?? '');
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              DropdownButtonFormField<NoteCategory>(
                initialValue: _category,
                decoration: const InputDecoration(labelText: 'Category'),
                items: NoteCategory.values
                    .map(
                      (c) => DropdownMenuItem(
                        value: c,
                        child: Text(noteCategoryLabel(c)),
                      ),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value != null) {
                    setState(() => _category = value);
                  }
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _textController,
                decoration: const InputDecoration(
                  labelText: 'Note',
                  hintText: 'Enter your note...',
                ),
                maxLines: 3,
                validator: (value) =>
                    value == null || value.trim().isEmpty ? 'Note cannot be empty' : null,
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: widget.onCancel,
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: _submit,
                    child: const Text('Save'),
                  ),
                ],
              ),
            ],
          ),
        ),
      );

  void _submit() {
    if (_formKey.currentState!.validate()) {
      widget.onSave(_category, _textController.text.trim());
    }
  }
}
