import 'dart:typed_data';

import 'package:desktop_drop/desktop_drop.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/bloc/script_import/script_import_cubit.dart';
import 'package:horatio_app/bloc/script_import/script_import_state.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_app/services/file_import_service.dart';
import 'package:horatio_app/widgets/script_card_widget.dart';

/// Main screen — shows the script library with drag-and-drop import.
class HomeScreen extends StatefulWidget {
  /// Creates a [HomeScreen].
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _isDragging = false;

  @override
  void initState() {
    super.initState();
    context.read<ScriptImportCubit>().loadScripts();
  }

  Future<void> _handleDrop(DropDoneDetails details) async {
    final cubit = context.read<ScriptImportCubit>();
    for (final file in details.files) {
      final ext = file.name.split('.').last.toLowerCase();
      if (!FileImportService.supportedExtensions.contains(ext)) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Unsupported file type: .$ext')),
          );
        }
        continue;
      }
      final bytes = await file.readAsBytes();
      await cubit.importFromBytes(
        bytes: Uint8List.fromList(bytes),
        fileName: file.name,
      );
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Horatio')),
        body: DropTarget(
          onDragDone: _handleDrop,
          onDragEntered: (_) => setState(() => _isDragging = true),
          onDragExited: (_) => setState(() => _isDragging = false),
          child: BlocBuilder<ScriptImportCubit, ScriptImportState>(
            builder: (context, state) => switch (state) {
              ScriptImportLoading() => const Center(
                  child: CircularProgressIndicator(),
                ),
              ScriptImportError(:final message) => Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        Icons.error_outline,
                        size: 48,
                        color: Colors.red,
                      ),
                      const SizedBox(height: 16),
                      Text(message, textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: () => context
                            .read<ScriptImportCubit>()
                            .loadScripts(),
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              ScriptImportLoaded(:final scripts)
                  when scripts.isEmpty =>
                _EmptyLibrary(isDragging: _isDragging),
              ScriptImportLoaded(:final scripts) => Stack(
                  children: [
                    ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: scripts.length,
                      itemBuilder: (context, index) => ScriptCardWidget(
                        script: scripts[index],
                        onTap: () => context.push(
                          RoutePaths.roleSelection,
                          extra: scripts[index],
                        ),
                        onDelete: () => context
                            .read<ScriptImportCubit>()
                            .removeScript(index),
                      ),
                    ),
                    if (_isDragging)
                      Positioned.fill(
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            color: Theme.of(context)
                                .colorScheme
                                .primary
                                .withValues(alpha: 0.1),
                            border: Border.all(
                              color:
                                  Theme.of(context).colorScheme.primary,
                              width: 3,
                            ),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.file_download,
                                  size: 64,
                                  color: Theme.of(context)
                                      .colorScheme
                                      .primary,
                                ),
                                const SizedBox(height: 16),
                                Text(
                                  'Drop script file here',
                                  style: Theme.of(context)
                                      .textTheme
                                      .headlineSmall
                                      ?.copyWith(
                                        color: Theme.of(context)
                                            .colorScheme
                                            .primary,
                                      ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  '.txt  .docx  .pdf',
                                  style: Theme.of(context)
                                      .textTheme
                                      .bodyMedium
                                      ?.copyWith(
                                        color: Theme.of(context)
                                            .colorScheme
                                            .primary
                                            .withValues(alpha: 0.7),
                                      ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ScriptImportInitial() =>
                _EmptyLibrary(isDragging: _isDragging),
            },
          ),
        ),
      );
}

/// Bundled public domain script metadata for the suggestion cards.
class _PublicDomainEntry {
  const _PublicDomainEntry({
    required this.title,
    required this.author,
    required this.assetPath,
  });

  final String title;
  final String author;
  final String assetPath;
}

const _publicDomainScripts = [
  _PublicDomainEntry(
    title: 'Hamlet — Act 3, Scene 1',
    author: 'William Shakespeare',
    assetPath: 'assets/public_domain/hamlet_act3_scene1.json',
  ),
  _PublicDomainEntry(
    title: 'Romeo & Juliet — Act 2, Scene 2',
    author: 'William Shakespeare',
    assetPath: 'assets/public_domain/romeo_juliet_act2_scene2.json',
  ),
  _PublicDomainEntry(
    title: "A Doll's House — Act 3",
    author: 'Henrik Ibsen',
    assetPath: 'assets/public_domain/dolls_house_act3.json',
  ),
  _PublicDomainEntry(
    title: 'The Cherry Orchard — Act 1',
    author: 'Anton Chekhov',
    assetPath: 'assets/public_domain/cherry_orchard_act1.json',
  ),
  _PublicDomainEntry(
    title: 'The Importance of Being Earnest — Act 1',
    author: 'Oscar Wilde',
    assetPath: 'assets/public_domain/importance_of_being_earnest_act1.json',
  ),
];

class _EmptyLibrary extends StatelessWidget {
  const _EmptyLibrary({required this.isDragging});

  final bool isDragging;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final borderColor = isDragging
        ? colorScheme.primary
        : colorScheme.outline.withValues(alpha: 0.5);
    final bgColor = isDragging
        ? colorScheme.primary.withValues(alpha: 0.08)
        : colorScheme.surfaceContainerHighest.withValues(alpha: 0.3);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          const SizedBox(height: 8),
          GestureDetector(
            onTap: () =>
                context.read<ScriptImportCubit>().importFromFile(),
            child: MouseRegion(
              cursor: SystemMouseCursors.click,
              child: CustomPaint(
                painter: _DashedBorderPainter(
                  color: borderColor,
                  strokeWidth: isDragging ? 3.0 : 2.0,
                  dashWidth: 12,
                  dashSpace: 6,
                  borderRadius: 20,
                ),
                child: Container(
                  width: double.infinity,
                  constraints: const BoxConstraints(minHeight: 280),
                  decoration: BoxDecoration(
                    color: bgColor,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  padding: const EdgeInsets.symmetric(
                    vertical: 48,
                    horizontal: 24,
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        isDragging
                            ? Icons.file_download
                            : Icons.upload_file,
                        size: 72,
                        color: isDragging
                            ? colorScheme.primary
                            : colorScheme.primary
                                .withValues(alpha: 0.6),
                      ),
                      const SizedBox(height: 20),
                      Text(
                        isDragging
                            ? 'Drop to import'
                            : 'Drop or click to import file',
                        style: Theme.of(context)
                            .textTheme
                            .headlineSmall
                            ?.copyWith(
                              color: isDragging
                                  ? colorScheme.primary
                                  : colorScheme.onSurface,
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Supports .txt  .docx  .pdf',
                        style: Theme.of(context)
                            .textTheme
                            .bodyMedium
                            ?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                            ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 24),
          Text(
            'or try a classic',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
          ),
          const SizedBox(height: 16),
          Text(
            'Public Domain Scripts',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          ..._publicDomainScripts.map(
            (entry) => Card(
              child: ListTile(
                leading: const Icon(Icons.auto_stories),
                title: Text(entry.title),
                subtitle: Text(entry.author),
                trailing: const Icon(Icons.download),
                onTap: () => context
                    .read<ScriptImportCubit>()
                    .importFromAsset(entry.assetPath),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DashedBorderPainter extends CustomPainter {
  const _DashedBorderPainter({
    required this.color,
    required this.strokeWidth,
    required this.dashWidth,
    required this.dashSpace,
    required this.borderRadius,
  });

  final Color color;
  final double strokeWidth;
  final double dashWidth;
  final double dashSpace;
  final double borderRadius;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke;

    final path = Path()
      ..addRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(0, 0, size.width, size.height),
          Radius.circular(borderRadius),
        ),
      );

    final dashedPath = Path();
    for (final metric in path.computeMetrics()) {
      var distance = 0.0;
      while (distance < metric.length) {
        final end = (distance + dashWidth).clamp(0.0, metric.length);
        dashedPath.addPath(
          metric.extractPath(distance, end),
          Offset.zero,
        );
        distance += dashWidth + dashSpace;
      }
    }

    canvas.drawPath(dashedPath, paint);
  }

  @override
  bool shouldRepaint(_DashedBorderPainter oldDelegate) =>
      color != oldDelegate.color ||
      strokeWidth != oldDelegate.strokeWidth ||
      dashWidth != oldDelegate.dashWidth ||
      dashSpace != oldDelegate.dashSpace ||
      borderRadius != oldDelegate.borderRadius;
}
