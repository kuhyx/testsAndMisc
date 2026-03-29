import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/script_import/script_import_state.dart';
import 'package:horatio_app/services/file_import_service.dart';
import 'package:horatio_app/services/script_repository.dart';
import 'package:horatio_core/horatio_core.dart';

/// Manages script import and library state.
class ScriptImportCubit extends Cubit<ScriptImportState> {
  /// Creates a [ScriptImportCubit].
  ScriptImportCubit({
    required ScriptRepository repository,
    FileImportService? importService,
    AssetBundle? assetBundle,
  })  : _repository = repository,
        _importService = importService ?? const FileImportService(),
        _assetBundle = assetBundle ?? rootBundle,
        super(const ScriptImportInitial());

  final ScriptRepository _repository;
  final FileImportService _importService;
  final AssetBundle _assetBundle;

  /// Loads the current script library.
  void loadScripts() {
    emit(ScriptImportLoaded(scripts: _repository.scripts));
  }

  /// Imports a script from a user-selected file.
  Future<void> importFromFile() async {
    emit(const ScriptImportLoading());
    try {
      final script = await _importService.pickAndParse();
      if (script == null) {
        // User cancelled.
        emit(ScriptImportLoaded(scripts: _repository.scripts));
        return;
      }
      _repository.add(script);
      emit(ScriptImportLoaded(scripts: _repository.scripts));
    } on FormatException catch (e) {
      emit(ScriptImportError(message: e.message));
    }
  }

  /// Imports a script from raw text content.
  void importFromText({
    required String text,
    required String title,
  }) {
    emit(const ScriptImportLoading());
    try {
      final parser = TextParser();
      final script = parser.parse(content: text, title: title);
      _repository.add(script);
      emit(ScriptImportLoaded(scripts: _repository.scripts));
    } on FormatException catch (e) {
      emit(ScriptImportError(message: e.message));
    }
  }

  /// Imports a script from dropped file bytes.
  Future<void> importFromBytes({
    required Uint8List bytes,
    required String fileName,
  }) async {
    emit(const ScriptImportLoading());
    try {
      final script = await _importService.parseBytes(
        bytes: bytes,
        fileName: fileName,
      );
      if (script == null) return;
      _repository.add(script);
      emit(ScriptImportLoaded(scripts: _repository.scripts));
    } on FormatException catch (e) {
      emit(ScriptImportError(message: e.message));
    }
  }

  /// Imports a bundled public domain script from assets.
  Future<void> importFromAsset(String assetPath) async {
    emit(const ScriptImportLoading());
    try {
      final jsonString = await _assetBundle.loadString(assetPath);
      final data = json.decode(jsonString) as Map<String, dynamic>;
      final title = data['title'] as String;
      final text = data['text'] as String;
      final parser = TextParser();
      final script = parser.parse(content: text, title: title);
      _repository.add(script);
      emit(ScriptImportLoaded(scripts: _repository.scripts));
    } on FormatException catch (e) {
      emit(ScriptImportError(message: e.message));
    }
  }

  /// Removes a script at [index].
  void removeScript(int index) {
    _repository.removeAt(index);
    emit(ScriptImportLoaded(scripts: _repository.scripts));
  }
}
