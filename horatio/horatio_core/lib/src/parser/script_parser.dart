import 'package:horatio_core/src/models/script.dart';

/// Abstract interface for parsing script files into structured [Script] objects.
///
/// This is intentionally a single-method interface to allow multiple
/// implementations (text, PDF, DOCX, etc.) behind a common type.
// ignore: one_member_abstracts
abstract interface class ScriptParser {
  /// Parses raw [content] text into a structured [Script].
  ///
  /// The [title] is provided externally (e.g., from the filename).
  Script parse({required String content, required String title});
}
