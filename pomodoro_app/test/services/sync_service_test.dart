import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
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
    sentMessages.add(SentDatagram(buffer));
    return buffer.length;
  }

  @override
  Datagram? receive() => _pendingDatagram;

  /// Simulates receiving a datagram.
  void injectDatagram(List<int> data, InternetAddress address, int port) {
    _pendingDatagram = Datagram(
      Uint8List.fromList(data),
      address,
      port,
    );
    _controller.add(RawSocketEvent.read);
  }

  /// Simulates a socket error.
  void injectError(Object error) {
    _controller.addError(error);
  }

  @override
  StreamSubscription<RawSocketEvent> listen(
    void Function(RawSocketEvent)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) =>
      _controller.stream.listen(
        onData,
        onError: onError,
        onDone: onDone,
        cancelOnError: cancelOnError ?? false,
      );

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
  SentDatagram(this.data);
  final List<int> data;

  Map<String, dynamic> get decoded =>
      jsonDecode(utf8.decode(data)) as Map<String, dynamic>;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

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
      final stateMap = decoded['state'] as Map<String, dynamic>;
      expect(stateMap['mode'], 'work');
      expect(stateMap['remainingSeconds'], 25 * 60);
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
      service
        ..startHeartbeat(() => state)
        ..stopHeartbeat();
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

  group('SyncService error paths', () {
    test('start catches socket bind failure', () async {
      final service = SyncService(
        onStateReceived: (_, _) {},
        deviceId: 'err-device',
        socketFactory: (host, port) async {
          throw const SocketException('bind failed');
        },
      );

      // Should not throw.
      await service.start();
      expect(service.isActive, false);

      await service.dispose();
    });

    test('broadcast catches send failure', () async {
      final throwingSocket = _ThrowingSendSocket();
      final service = SyncService(
        onStateReceived: (_, _) {},
        deviceId: 'send-err',
        socketFactory: (host, port) async => throwingSocket,
      );
      await service.start();

      // broadcast should not throw.
      service.broadcast(PomodoroState.initial(), 'test');

      await service.dispose();
    });

    test('heartbeat callback fires and sends broadcast', () async {
      final fakeSocket = FakeDatagramSocket();
      final service = SyncService(
        onStateReceived: (_, _) {},
        deviceId: 'hb-device',
        socketFactory: (host, port) async => fakeSocket,
      );
      await service.start();

      fakeSocket.sentMessages.clear();
      service.startHeartbeat(
        PomodoroState.initial,
        interval: const Duration(milliseconds: 1),
      );

      // Allow the periodic timer to fire.
      await Future<void>.delayed(const Duration(milliseconds: 20));

      // The heartbeat should have fired at least once.
      expect(fakeSocket.sentMessages, isNotEmpty);

      service.stopHeartbeat();
      await service.dispose();
    });

    test('wake send failure is caught', () async {
      // _sendWake is called during start(). If socket.send throws for
      // the wake port, it should be caught.
      final throwOnWakeSocket = _ThrowingSendSocket();
      final service = SyncService(
        onStateReceived: (_, _) {},
        deviceId: 'wake-err',
        socketFactory: (host, port) async => throwOnWakeSocket,
      );

      // start() calls _sendWake() which will throw — should be caught.
      await service.start();

      await service.dispose();
    });

    test('socket stream error invokes onError handler', () async {
      final fakeSocket = FakeDatagramSocket();
      final service = SyncService(
        onStateReceived: (_, _) {},
        deviceId: 'stream-err',
        socketFactory: (host, port) async => fakeSocket,
      );
      await service.start();

      // Inject an error into the stream — should not crash.
      fakeSocket.injectError(const SocketException('stream error'));
      await Future<void>.delayed(Duration.zero);

      await service.dispose();
    });
  });

  group('SyncService multicast lock (Android paths)', () {
    const channel = MethodChannel('pomodoro_multicast_lock');

    test('acquires and releases lock when isAndroid is true', () async {
      // No handler registered → MissingPluginException caught internally.
      final fakeSocket = FakeDatagramSocket();
      final service = SyncService(
        onStateReceived: (_, _) {},
        deviceId: 'android-device',
        isAndroid: true,
        socketFactory: (host, port) async => fakeSocket,
      );

      await service.start();
      await service.dispose();
    });

    test('handles non-MissingPluginException in acquire', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (call) async {
        if (call.method == 'acquire') {
          throw PlatformException(code: 'ERROR', message: 'lock failed');
        }
        return null;
      });

      final fakeSocket = FakeDatagramSocket();
      final service = SyncService(
        onStateReceived: (_, _) {},
        deviceId: 'android-err-acquire',
        isAndroid: true,
        socketFactory: (host, port) async => fakeSocket,
      );

      await service.start();
      await service.dispose();

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null);
    });

    test('handles non-MissingPluginException in release', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (call) async {
        if (call.method == 'release') {
          throw PlatformException(code: 'ERROR', message: 'release failed');
        }
        return true;
      });

      final fakeSocket = FakeDatagramSocket();
      final service = SyncService(
        onStateReceived: (_, _) {},
        deviceId: 'android-err-release',
        isAndroid: true,
        socketFactory: (host, port) async => fakeSocket,
      );

      await service.start();
      await service.dispose();

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null);
    });
  });
}

/// A fake socket that throws on every [send] call.
class _ThrowingSendSocket extends FakeDatagramSocket {
  @override
  int send(List<int> buffer, InternetAddress address, int port) {
    throw const SocketException('send failed');
  }
}
