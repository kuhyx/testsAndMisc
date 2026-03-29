import 'package:horatio_core/src/models/models.dart';
import 'package:horatio_core/src/parser/role_detector.dart';
import 'package:horatio_core/src/parser/script_parser.dart';

/// Parses plain text scripts into structured [Script] objects.
///
/// Handles multiple common script formats by delegating character detection
/// to [RoleDetector].
final class TextParser implements ScriptParser {
  /// Creates a [TextParser] with an optional custom [roleDetector].
  TextParser({RoleDetector? roleDetector})
    : _roleDetector = roleDetector ?? const RoleDetector();

  final RoleDetector _roleDetector;

  /// Scene heading pattern (e.g., "ACT I", "SCENE 2", "Act 1, Scene 3").
  static final RegExp _sceneHeadingPattern = RegExp(
    r'^(ACT|SCENE|Act|Scene)\s+[\dIVXLCDMivxlcdm]+',
  );

  @override
  Script parse({required String content, required String title}) {
    final lines = content.split('\n');
    final roles = <String, Role>{};
    final scenes = <Scene>[];
    var currentSceneLines = <ScriptLine>[];
    var currentSceneTitle = '';
    var globalLineIndex = 0;
    var sceneIndex = 0;

    Role? lastSpeaker;
    var continuationBuffer = StringBuffer();

    for (final rawLine in lines) {
      final line = rawLine.trimRight();

      // Check for scene headings.
      if (_sceneHeadingPattern.hasMatch(line.trim())) {
        // Save current scene if it has content.
        if (currentSceneLines.isNotEmpty) {
          _flushContinuation(
            continuationBuffer,
            lastSpeaker,
            currentSceneLines,
            sceneIndex,
            globalLineIndex,
          );
          scenes.add(
            Scene(
              title: currentSceneTitle,
              lines: List.unmodifiable(currentSceneLines),
              index: sceneIndex,
            ),
          );
          sceneIndex++;
          currentSceneLines = <ScriptLine>[];
        }
        currentSceneTitle = line.trim();
        lastSpeaker = null;
        continuationBuffer = StringBuffer();
        continue;
      }

      // Blank line: flush continuation.
      if (line.trim().isEmpty) {
        globalLineIndex = _flushContinuation(
          continuationBuffer,
          lastSpeaker,
          currentSceneLines,
          sceneIndex,
          globalLineIndex,
        );
        lastSpeaker = null;
        continue;
      }

      // Check for pure stage direction.
      final direction = _roleDetector.detectStageDirection(line);
      if (direction != null) {
        globalLineIndex = _flushContinuation(
          continuationBuffer,
          lastSpeaker,
          currentSceneLines,
          sceneIndex,
          globalLineIndex,
        );
        lastSpeaker = null;
        currentSceneLines.add(
          ScriptLine.direction(
            text: direction.text,
            sceneIndex: sceneIndex,
            lineIndex: globalLineIndex,
          ),
        );
        globalLineIndex++;
        continue;
      }

      // Try to detect a role.
      final detected = _roleDetector.detectRole(line);
      if (detected != null) {
        globalLineIndex = _flushContinuation(
          continuationBuffer,
          lastSpeaker,
          currentSceneLines,
          sceneIndex,
          globalLineIndex,
        );

        final roleName = detected.role.normalizedName;
        roles.putIfAbsent(roleName, () => detected.role);
        lastSpeaker = roles[roleName];

        if (detected.dialogue.isNotEmpty) {
          continuationBuffer = StringBuffer(detected.dialogue);
        } else {
          continuationBuffer = StringBuffer();
        }
        continue;
      }

      // Continuation line: append to current speaker's dialogue.
      if (lastSpeaker != null) {
        if (continuationBuffer.isNotEmpty) {
          continuationBuffer.write(' ');
        }
        continuationBuffer.write(line.trim());
      }
    }

    // Flush remaining content.
    globalLineIndex = _flushContinuation(
      continuationBuffer,
      lastSpeaker,
      currentSceneLines,
      sceneIndex,
      globalLineIndex,
    );

    // Save final scene.
    if (currentSceneLines.isNotEmpty) {
      scenes.add(
        Scene(
          title: currentSceneTitle,
          lines: List.unmodifiable(currentSceneLines),
          index: sceneIndex,
        ),
      );
    }

    // If no scenes were created, wrap everything in one scene.
    if (scenes.isEmpty && currentSceneLines.isEmpty) {
      scenes.add(const Scene(lines: []));
    }

    return Script(
      title: title,
      roles: List.unmodifiable(roles.values.toList()),
      scenes: List.unmodifiable(scenes),
    );
  }

  /// Flushes accumulated dialogue into a [ScriptLine] and returns the
  /// updated global line index.
  int _flushContinuation(
    StringBuffer buffer,
    Role? speaker,
    List<ScriptLine> lines,
    int sceneIndex,
    int globalLineIndex,
  ) {
    if (buffer.isEmpty || speaker == null) {
      buffer.clear();
      return globalLineIndex;
    }

    lines.add(
      ScriptLine(
        text: buffer.toString(),
        role: speaker,
        sceneIndex: sceneIndex,
        lineIndex: globalLineIndex,
      ),
    );
    buffer.clear();
    return globalLineIndex + 1;
  }
}
