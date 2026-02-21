import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../models/pomodoro_state.dart';

/// Callback type for receiving a synced [PomodoroState] and action name.
typedef SyncCallback = void Function(PomodoroState state, String action);

/// Provides LAN synchronization between Pomodoro app instances using
/// UDP broadcast.
///
/// Uses subnet broadcast (255.255.255.255) instead of multicast for
/// maximum compatibility across platforms. A unique [deviceId] prevents
/// echo (processing own messages).
class SyncService {
  /// Creates a [SyncService].
  ///
  /// [onStateReceived] is called when a remote device broadcasts a state
  /// change. [port] can be overridden for testing.
  SyncService({
    required this.onStateReceived,
    this.port = 41234,
    @visibleForTesting String? deviceId,
    @visibleForTesting
    Future<RawDatagramSocket> Function(dynamic host, int port)?
        socketFactory,
  })  : deviceId = deviceId ?? _generateDeviceId(),
        _socketFactory = socketFactory;

  /// Unique identifier for this device instance.
  final String deviceId;

  /// UDP port for sync messages.
  final int port;

  /// UDP port for wake signals (separate from sync to allow a daemon to
  /// listen without conflicting with the app's sync socket).
  static const int wakePort = 41235;

  /// Called when a state update is received from another device.
  final SyncCallback onStateReceived;

  final Future<RawDatagramSocket> Function(dynamic host, int port)?
      _socketFactory;

  RawDatagramSocket? _socket;
  Timer? _heartbeat;
  bool _disposed = false;

  static const _methodChannel = MethodChannel('pomodoro_multicast_lock');

  /// Whether the service is currently listening.
  bool get isActive => _socket != null && !_disposed;

  /// Starts listening for broadcast messages and enables sending.
  Future<void> start() async {
    if (_disposed) return;

    // Acquire Android multicast/broadcast lock.
    await _acquireMulticastLock();

    try {
      if (_socketFactory != null) {
        _socket = await _socketFactory(InternetAddress.anyIPv4, port);
      } else {
        _socket = await RawDatagramSocket.bind(
          InternetAddress.anyIPv4,
          port,
          reuseAddress: true,
        );
      }

      _socket?.broadcastEnabled = true;

      _socket?.listen(
        _onSocketEvent,
        onError: _onError,
        cancelOnError: false,
      );

      debugPrint('SyncService: Listening on port $port (device=$deviceId)');

      // Notify other devices that this instance just opened.
      _sendWake();
    } on Object catch (e) {
      debugPrint('SyncService: Failed to start: $e');
    }
  }

  /// Broadcasts the given [state] with an [action] label to all peers.
  void broadcast(PomodoroState state, String action) {
    if (_socket == null || _disposed) return;

    final message = _encodeMessage(state, action);
    try {
      final sent = _socket!.send(
        message,
        InternetAddress('255.255.255.255'),
        port,
      );
      debugPrint(
        'SyncService: Sent $action ($sent bytes) '
        'to 255.255.255.255:$port',
      );
    } on Object catch (e) {
      debugPrint('SyncService: Send failed: $e');
    }
  }

  /// Starts periodic heartbeat that broadcasts current state.
  ///
  /// This keeps devices in sync even if an individual message is lost.
  void startHeartbeat(PomodoroState Function() stateProvider) {
    _heartbeat?.cancel();
    _heartbeat = Timer.periodic(
      const Duration(seconds: 5),
      (_) => broadcast(stateProvider(), 'heartbeat'),
    );
  }

  /// Stops the periodic heartbeat.
  void stopHeartbeat() {
    _heartbeat?.cancel();
    _heartbeat = null;
  }

  /// Shuts down the sync service.
  Future<void> dispose() async {
    _disposed = true;
    _heartbeat?.cancel();
    _heartbeat = null;

    _socket?.close();
    _socket = null;

    await _releaseMulticastLock();
  }

  // -- Private helpers --

  /// Sends a wake signal to the dedicated wake port so that a desktop
  /// daemon can auto-launch the app on other devices.
  void _sendWake() {
    if (_socket == null || _disposed) return;
    final message = utf8.encode(jsonEncode(<String, dynamic>{
      'deviceId': deviceId,
      'action': 'wake',
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    }));
    try {
      _socket!.send(message, InternetAddress('255.255.255.255'), wakePort);
      debugPrint('SyncService: Sent wake to port $wakePort');
    } on Object catch (e) {
      debugPrint('SyncService: Wake send failed: $e');
    }
  }

  void _onSocketEvent(RawSocketEvent event) {
    if (event != RawSocketEvent.read) return;

    final datagram = _socket?.receive();
    if (datagram == null) return;

    try {
      final json = utf8.decode(datagram.data);
      final map = jsonDecode(json) as Map<String, dynamic>;

      // Ignore own messages.
      if (map['deviceId'] == deviceId) return;

      final state = _decodeState(map['state'] as Map<String, dynamic>);
      final action = map['action'] as String;
      debugPrint(
        'SyncService: Received $action from ${map['deviceId']}',
      );
      onStateReceived(state, action);
    } on Object catch (e) {
      debugPrint('SyncService: Parse error: $e');
    }
  }

  void _onError(Object error) {
    debugPrint('SyncService: Socket error: $error');
  }

  List<int> _encodeMessage(PomodoroState state, String action) {
    final map = <String, dynamic>{
      'deviceId': deviceId,
      'timestamp': DateTime.now().millisecondsSinceEpoch,
      'action': action,
      'state': _encodeState(state),
    };
    return utf8.encode(jsonEncode(map));
  }

  static Map<String, dynamic> _encodeState(PomodoroState state) {
    return {
      'mode': state.mode.name,
      'remainingSeconds': state.remainingSeconds,
      'totalSeconds': state.totalSeconds,
      'isRunning': state.isRunning,
      'completedPomodoros': state.completedPomodoros,
      'pomodorosPerCycle': state.pomodorosPerCycle,
    };
  }

  static PomodoroState _decodeState(Map<String, dynamic> map) {
    return PomodoroState(
      mode: PomodoroMode.values.byName(map['mode'] as String),
      remainingSeconds: map['remainingSeconds'] as int,
      totalSeconds: map['totalSeconds'] as int,
      isRunning: map['isRunning'] as bool,
      completedPomodoros: map['completedPomodoros'] as int,
      pomodorosPerCycle: map['pomodorosPerCycle'] as int,
    );
  }

  static Future<void> _acquireMulticastLock() async {
    if (!Platform.isAndroid) return;
    try {
      await _methodChannel.invokeMethod<bool>('acquire');
    } on MissingPluginException {
      // Platform channel not available (e.g., in tests).
    } on Object catch (e) {
      debugPrint('SyncService: Failed to acquire multicast lock: $e');
    }
  }

  static Future<void> _releaseMulticastLock() async {
    if (!Platform.isAndroid) return;
    try {
      await _methodChannel.invokeMethod<bool>('release');
    } on MissingPluginException {
      // Platform channel not available.
    } on Object catch (e) {
      debugPrint('SyncService: Failed to release multicast lock: $e');
    }
  }

  static String _generateDeviceId() {
    final random = Random();
    return List.generate(
      8,
      (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
    ).join();
  }
}
