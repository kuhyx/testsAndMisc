import 'package:device_preview/device_preview.dart';
import 'package:flutter/material.dart';
import 'package:horatio_app/app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    DevicePreview(
      builder: (_) => const HoratioApp(),
    ),
  );
}
