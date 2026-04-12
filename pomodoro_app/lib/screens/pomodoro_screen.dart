import 'package:flutter/material.dart';

import 'package:pomodoro_app/models/pomodoro_state.dart';
import 'package:pomodoro_app/services/notification_service.dart';
import 'package:pomodoro_app/services/pomodoro_timer.dart';
import 'package:pomodoro_app/services/sound_service.dart';
import 'package:pomodoro_app/services/sync_service.dart';
import 'package:pomodoro_app/widgets/pomodoro_indicators.dart';
import 'package:pomodoro_app/widgets/timer_controls.dart';
import 'package:pomodoro_app/widgets/timer_display.dart';

/// The main screen of the Pomodoro app.
///
/// Displays the timer, controls, and session indicators in a responsive
/// layout that works on both mobile and desktop.
class PomodoroScreen extends StatefulWidget {
  /// Creates a [PomodoroScreen].
  const PomodoroScreen({this.timer, this.syncService, super.key});

  /// Optional timer instance for testing. If null, creates a default one.
  final PomodoroTimer? timer;

  /// Optional sync service for testing. If null, creates a default one.
  final SyncService? syncService;

  @override
  State<PomodoroScreen> createState() => PomodoroScreenState();
}

/// State for [PomodoroScreen], exposed for testing.
@visibleForTesting
class PomodoroScreenState extends State<PomodoroScreen> {
  PomodoroTimer? _timer;
  SyncService? _syncService;
  bool _ownsTimer = false;
  bool _ownsSyncService = false;
  bool _initialized = false;

  @override
  void initState() {
    super.initState();

    if (widget.timer != null) {
      // Test path: synchronous init, no sync service needed.
      _timer = widget.timer;
      _syncService = widget.syncService;
      _timer!.addListener(_onTimerChanged);
      _initialized = true;
    } else {
      // Production path: async init with sync service.
      _initAsync();
    }
  }

  Future<void> _initAsync() async {
    _syncService = SyncService(
      onStateReceived: onRemoteState,
    );
    _ownsSyncService = true;
    await _syncService!.start();

    _timer = PomodoroTimer(
      syncService: _syncService,
      soundService: SoundService(),
      notificationService: NotificationService(),
    );
    _ownsTimer = true;

    _timer!.addListener(_onTimerChanged);
    _initialized = true;
    if (mounted) setState(() {});
  }

  /// Handles state received from a remote device.
  @visibleForTesting
  void onRemoteState(PomodoroState state, String action) {
    _timer?.applyRemoteState(state, action);
  }

  void _onTimerChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _timer?.removeListener(_onTimerChanged);
    if (_ownsTimer) _timer?.dispose();
    if (_ownsSyncService) _syncService?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_initialized || _timer == null) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final timer = _timer!;
    final state = timer.state;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 500),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Spacer(flex: 2),
                  // Timer style picker.
                  SegmentedButton<TimerStyle>(
                    segments: const [
                      ButtonSegment(
                        value: TimerStyle.pomodoro,
                        label: Text('Pomodoro'),
                        icon: Icon(Icons.timer),
                      ),
                      ButtonSegment(
                        value: TimerStyle.ultraradian,
                        label: Text('Ultraradian'),
                        icon: Icon(Icons.self_improvement),
                      ),
                    ],
                    selected: {timer.timerStyle},
                    onSelectionChanged: (selected) {
                      timer.switchStyle(selected.first);
                    },
                  ),
                  const SizedBox(height: 16),
                  // Timer display.
                  Expanded(
                    flex: 5,
                    child: TimerDisplay(state: state),
                  ),
                  const SizedBox(height: 32),
                  // Controls.
                  TimerControls(
                    state: state,
                    onStart: timer.start,
                    onPause: timer.pause,
                    onReset: timer.reset,
                    onSkip: timer.skip,
                  ),
                  const SizedBox(height: 32),
                  // Session indicators.
                  PomodoroIndicators(state: state),
                  const SizedBox(height: 16),
                  // Completed count.
                  Text(
                    '${state.completedPomodoros} '
                    '${timer.timerStyle.label.toLowerCase()}'
                    '${state.completedPomodoros == 1 ? '' : 's'}'
                    ' completed',
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                  const Spacer(flex: 2),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
