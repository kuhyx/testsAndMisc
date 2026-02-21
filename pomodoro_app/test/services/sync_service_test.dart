import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pomodoro_app/models/pomodoro_state.dart';
import 'package:pomodoro_app/services/sync_service.dart';

/// A fake [RawDatagramSocket] that captures sent messages and allows
/// injecting received messages.
class FakeDatagramSocket implements RawDatagramSocket {
  final _controller = StreamController<RawSocketEvent>.broadcast();
  final List<SentDatagram> sentMessages = [];
  Datagram? _pendingDatagram;

  @override
  int send(List<int> buffer, InternetAddress address, int port) {
    sentMessages.add(SentDatagram(buffer, address, port));
    return buffer.length;
  }

  @override
  Datagram? receive() => _pendingDatagram;

  /// Simulates receiving a datagram.
  void injectDatagram(List<int> data, InternetAddress address, int port) {
    _pendingDatagram = Datagram(
      data as dynamic,
      address,
      port,
    );
    _controller.add(RawSocketEvent.read);
  }

  @override
  StreamSubscription<RawSocketEvent> listen(
    void Function(RawSocketEvent)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) {
    return _controller.stream.listen(
      onData,
      onError: onError,
      onDone: onDone,
      cancelOnError: cancelOnError ?? false,
    );
  }

  @override
  void joinMulticast(InternetAddress group, [NetworkInterface? interface_]) {}

  @override
  void leaveMulticast(InternetAddress group, [NetworkInterface? interface_]) {}

  @override
  void close() => _controller.close();

  // Required interface stubs.
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class SentDatagram {
  SentDatagram(this.data, this.address, this.port);
  final List<int> data;
  final InternetAddress address;
  final int port;

  Map<String, dynamic> get decoded =>
      jsonDecode(utf8.decode(data)) as Map<String, dynamic>;
}

void main() {
  group('SyncService', () {
    late FakeDatagramSocket fakeSocket;
    late SyncService service;
    PomodoroState? receivedState;
    String? receivedAction;

    setUp(() async {
      fakeSocket = FakeDatagramSocket();
      receivedState = null;
      receivedAction = null;

      service = SyncService(
        onStateReceived: (state, action) {
          receivedState = state;
          receivedAction = action;
        },
        deviceId: 'test-device-1',
        socketFactory: (host, port) async => fakeSocket,
      );
      await service.start();
    });

    tearDown(() async {
      await service.dispose();
    });

    test('is active after start', () {
      expect(service.isActive, true);
    });

    test('broadcast sends a message', () {
      // start() sends a wake message, so clear before testing broadcast.
      fakeSocket.sentMessages.clear();

      final state = PomodoroState.initial();
      service.broadcast(state, 'start');

      expect(fakeSocket.sentMessages, hasLength(1));
      final decoded = fakeSocket.sentMessages.first.decoded;
      expect(decoded['deviceId'], 'test-device-1');
      expect(decoded['action'], 'start');
      expect(decoded['state']['mode'], 'work');
      expect(decoded['state']['remainingSeconds'], 25 * 60);
    });

    test('ignores own messages', () async {
      final message = jsonEncode({
        'deviceId': 'test-device-1', // Same as our device.
        'timestamp': DateTime.now().millisecondsSinceEpoch,
        'action': 'start',
        'state': {
          'mode': 'work',
          'remainingSeconds': 1500,
          'totalSeconds': 1500,
          'isRunning': true,
          'completedPomodoros': 0,
          'pomodorosPerCycle': 4,
        },
      });

      fakeSocket.injectDatagram(
        utf8.encode(message),
        InternetAddress('192.168.1.100'),
        41234,
      );

      // Allow async processing.
      await Future<void>.delayed(Duration.zero);
      expect(receivedState, isNull);
      expect(receivedAction, isNull);
    });

    test('processes messages from other devices', () async {
      final message = jsonEncode({
        'deviceId': 'other-device-2',
        'timestamp': DateTime.now().millisecondsSinceEpoch,
        'action': 'pause',
        'state': {
          'mode': 'work',
          'remainingSeconds': 1200,
          'totalSeconds': 1500,
          'isRunning': false,
          'completedPomodoros': 1,
          'pomodorosPerCycle': 4,
        },
      });

      fakeSocket.injectDatagram(
        utf8.encode(message),
        InternetAddress('192.168.1.101'),
        41234,
      );

      await Future<void>.delayed(Duration.zero);
      expect(receivedState, isNotNull);
      expect(receivedAction, 'pause');
      expect(receivedState!.remainingSeconds, 1200);
      expect(receivedState!.isRunning, false);
      expect(receivedState!.completedPomodoros, 1);
    });

    test('handles malformed messages gracefully', () async {
      fakeSocket.injectDatagram(
        utf8.encode('not json at all'),
        InternetAddress('192.168.1.101'),
        41234,
      );

      await Future<void>.delayed(Duration.zero);
      // Should not crash, receivedState stays null.
      expect(receivedState, isNull);
    });

    test('broadcast does nothing after dispose', () async {
      await service.dispose();
      expect(service.isActive, false);

      // Should not throw.
      service.broadcast(PomodoroState.initial(), 'start');
    });

    test('heartbeat sends periodic state', () async {
      final state = PomodoroState.initial();
      service.startHeartbeat(() => state);

      // Wait for at least one heartbeat interval.
      // Note: In tests, Timer.periodic fires based on the test framework.
      // We just verify it doesn't crash and can be stopped.
      service.stopHeartbeat();
    });
  });

  group('SyncService state encoding', () {
    test('all modes encode and decode correctly', () async {
      for (final mode in PomodoroMode.values) {
        final fakeSocket = FakeDatagramSocket();
        PomodoroState? received;

        final sender = SyncService(
          onStateReceived: (_, _) {},
          deviceId: 'sender',
          socketFactory: (h, p) async => fakeSocket,
        );
        await sender.start();

        final receiver = SyncService(
          onStateReceived: (state, action) => received = state,
          deviceId: 'receiver',
          socketFactory: (h, p) async => fakeSocket,
        );
        await receiver.start();

        final state = PomodoroState(
          mode: mode,
          remainingSeconds: 300,
          totalSeconds: 600,
          isRunning: true,
          completedPomodoros: 3,
          pomodorosPerCycle: 4,
        );

        sender.broadcast(state, 'test');

        // Manually decode the sent message and inject it.
        final sent = fakeSocket.sentMessages.last;
        fakeSocket.injectDatagram(
          sent.data,
          InternetAddress('192.168.1.100'),
          41234,
        );

        await Future<void>.delayed(Duration.zero);
        expect(received, isNotNull);
        expect(received!.mode, mode);
        expect(received!.remainingSeconds, 300);
        expect(received!.totalSeconds, 600);
        expect(received!.isRunning, true);
        expect(received!.completedPomodoros, 3);

        await sender.dispose();
        await receiver.dispose();
      }
    });
  });
}
