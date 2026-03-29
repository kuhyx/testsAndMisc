import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_cubit.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_core/horatio_core.dart';

/// Screen showing the memorization schedule and providing SRS review launch.
class ScheduleScreen extends StatelessWidget {
  /// Creates a [ScheduleScreen].
  const ScheduleScreen({
    required this.script,
    required this.selectedRole,
    super.key,
  });

  /// The script being memorized.
  final Script script;

  /// The role selected by the actor.
  final Role selectedRole;

  @override
  Widget build(BuildContext context) {
    const planner = MemorizationPlanner();
    final cards = planner.createCards(
      script: script,
      role: selectedRole,
    );
    final now = DateTime.now();
    final schedule = planner.generateSchedule(
      totalCards: cards.length,
      startDate: now,
      deadline: now.add(const Duration(days: 30)),
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('Memorization Schedule'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _SummaryCard(cards: cards, role: selectedRole),
            const SizedBox(height: 16),
            Text(
              'Daily Plan',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Expanded(
              child: ListView.builder(
                itemCount: schedule.length,
                itemBuilder: (context, index) {
                  final session = schedule[index];
                  return ListTile(
                    leading: CircleAvatar(child: Text('${index + 1}')),
                    title: Text('Day ${index + 1}'),
                    subtitle: Text(
                      '${session.newCardCount} new · '
                      '${session.reviewCardCount} review',
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          final dueCards =
              cards.where((c) => c.isDue() || c.isNew).toList();
          if (dueCards.isEmpty) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('No cards due for review today.')),
            );
            return;
          }
          context.read<SrsReviewCubit>().startSession(dueCards);
          context.push(RoutePaths.srsReview, extra: dueCards);
        },
        icon: const Icon(Icons.play_arrow),
        label: const Text('Start Review'),
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.cards,
    required this.role,
  });

  final List<SrsCard> cards;
  final Role role;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              const Icon(Icons.person, size: 40),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      role.name,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    Text('${cards.length} cards to memorize'),
                    Text(
                      '${cards.where((c) => c.isDue()).length} due today',
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
}
