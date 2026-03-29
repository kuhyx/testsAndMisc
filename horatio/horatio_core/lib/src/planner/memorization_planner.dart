import 'package:horatio_core/src/models/models.dart';
import 'package:horatio_core/src/planner/daily_session.dart';

/// Generates a memorization schedule for a chosen role within a deadline.
final class MemorizationPlanner {
  /// Creates a [MemorizationPlanner].
  const MemorizationPlanner();

  /// Creates SRS cards from a [script] for the given [role].
  ///
  /// Each card pairs a cue (the preceding line) with the actor's response.
  /// Long monologues are split into sentence-pair cards.
  List<SrsCard> createCards({required Script script, required Role role}) {
    final cards = <SrsCard>[];
    var cardIndex = 0;

    for (final scene in script.scenes) {
      for (var i = 0; i < scene.lines.length; i++) {
        final line = scene.lines[i];
        if (line.role != role) continue;

        // Build the cue: the preceding non-direction line.
        final cue = _findPrecedingCue(scene.lines, i);

        // Check if this is a long monologue (multiple sentences).
        final sentences = _splitSentences(line.text);
        if (sentences.length > 1) {
          // Create sentence-pair cards for long monologues.
          for (var s = 0; s < sentences.length; s++) {
            final sentenceCue = s == 0 ? cue : sentences[s - 1];
            cards.add(
              SrsCard(
                id: 'card_${cardIndex++}',
                cueText: sentenceCue,
                answerText: sentences[s],
              ),
            );
          }
        } else {
          cards.add(
            SrsCard(
              id: 'card_${cardIndex++}',
              cueText: cue,
              answerText: line.text,
            ),
          );
        }
      }
    }

    return cards;
  }

  /// Generates a daily schedule from [startDate] to [deadline].
  List<DailySession> generateSchedule({
    required int totalCards,
    required DateTime startDate,
    required DateTime deadline,
  }) {
    final sessions = <DailySession>[];
    final daysAvailable = deadline.difference(startDate).inDays;
    if (daysAvailable <= 0) {
      // Everything in one session.
      return [
        DailySession(
          date: startDate,
          newCardCount: totalCards,
          reviewCardCount: 0,
        ),
      ];
    }

    final newPerDay = (totalCards / daysAvailable).ceil();
    var cardsIntroduced = 0;
    var estimatedReviews = 0;

    for (var day = 0; day < daysAvailable; day++) {
      final date = startDate.add(Duration(days: day));
      final remaining = totalCards - cardsIntroduced;
      final newToday = remaining < newPerDay ? remaining : newPerDay;

      sessions.add(
        DailySession(
          date: date,
          newCardCount: newToday,
          reviewCardCount: estimatedReviews,
        ),
      );

      cardsIntroduced += newToday;
      // Rough estimate: reviews grow by ~60% of new cards introduced
      // (assuming some will be remembered on first try).
      estimatedReviews = (cardsIntroduced * 0.6).round();
    }

    return sessions;
  }

  /// Finds the preceding dialogue line to use as a cue.
  String _findPrecedingCue(List<ScriptLine> lines, int currentIndex) {
    for (var i = currentIndex - 1; i >= 0; i--) {
      if (!lines[i].isStageDirection) {
        return lines[i].text;
      }
    }
    return '[Beginning of scene]';
  }

  /// Splits text into sentences.
  static List<String> _splitSentences(String text) {
    final sentences = text
        .split(RegExp(r'(?<=[.!?])\s+'))
        .where((s) => s.trim().isNotEmpty)
        .toList();
    return sentences.isEmpty ? [text] : sentences;
  }
}
