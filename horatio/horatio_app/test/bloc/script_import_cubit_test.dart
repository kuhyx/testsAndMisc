import 'dart:convert';

import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/script_import/script_import_cubit.dart';
import 'package:horatio_app/bloc/script_import/script_import_state.dart';
import 'package:horatio_app/services/file_import_service.dart';
import 'package:horatio_app/services/script_repository.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class MockScriptRepository extends Mock implements ScriptRepository {}

class MockFileImportService extends Mock implements FileImportService {}

class FakeAssetBundle extends Fake implements AssetBundle {
  FakeAssetBundle(this._assets);

  final Map<String, String> _assets;

  @override
  Future<String> loadString(String key, {bool cache = true}) async {
    final data = _assets[key];
    if (data == null) {
      throw FormatException('Asset not found: $key');
    }
    return data;
  }
}

const _fallbackScript = Script(
  id: 'fallback-id',
  title: '',
  roles: [],
  scenes: [Scene(lines: [])],
);

void main() {
  setUpAll(() {
    registerFallbackValue(_fallbackScript);
    registerFallbackValue(Uint8List(0));
  });

  late MockScriptRepository repository;
  late MockFileImportService importService;

  setUp(() {
    repository = MockScriptRepository();
    importService = MockFileImportService();
    when(() => repository.scripts).thenReturn([]);
  });

  group('ScriptImportCubit', () {
    blocTest<ScriptImportCubit, ScriptImportState>(
      'loadScripts emits Loaded with current scripts',
      build: () => ScriptImportCubit(
        repository: repository,
        importService: importService,
      ),
      act: (cubit) => cubit.loadScripts(),
      expect: () => [isA<ScriptImportLoaded>()],
    );

    blocTest<ScriptImportCubit, ScriptImportState>(
      'importFromFile emits Loading then Loaded on success',
      setUp: () {
        final script = TextParser().parse(
          title: 'Test',
          content: 'A: Hello.\nB: World.',
        );
        when(() => importService.pickAndParse())
            .thenAnswer((_) async => script);
        when(() => repository.scripts).thenReturn([script]);
      },
      build: () => ScriptImportCubit(
        repository: repository,
        importService: importService,
      ),
      act: (cubit) => cubit.importFromFile(),
      expect: () => [
        isA<ScriptImportLoading>(),
        isA<ScriptImportLoaded>(),
      ],
    );

    blocTest<ScriptImportCubit, ScriptImportState>(
      'importFromFile emits Loaded on cancel (null result)',
      setUp: () {
        when(() => importService.pickAndParse())
            .thenAnswer((_) async => null);
      },
      build: () => ScriptImportCubit(
        repository: repository,
        importService: importService,
      ),
      act: (cubit) => cubit.importFromFile(),
      expect: () => [
        isA<ScriptImportLoading>(),
        isA<ScriptImportLoaded>(),
      ],
    );

    blocTest<ScriptImportCubit, ScriptImportState>(
      'importFromFile emits Error on FormatException',
      setUp: () {
        when(() => importService.pickAndParse())
            .thenThrow(const FormatException('bad format'));
      },
      build: () => ScriptImportCubit(
        repository: repository,
        importService: importService,
      ),
      act: (cubit) => cubit.importFromFile(),
      expect: () => [
        isA<ScriptImportLoading>(),
        isA<ScriptImportError>()
            .having((s) => s.message, 'message', 'bad format'),
      ],
    );

    blocTest<ScriptImportCubit, ScriptImportState>(
      'importFromText parses and adds script on success',
      build: () => ScriptImportCubit(
        repository: repository,
        importService: importService,
      ),
      act: (cubit) => cubit.importFromText(
        text: 'ROMEO: O soft!\nJULIET: Romeo!',
        title: 'R&J',
      ),
      expect: () => [
        isA<ScriptImportLoading>(),
        isA<ScriptImportLoaded>(),
      ],
      verify: (_) {
        verify(() => repository.add(any())).called(1);
      },
    );

    blocTest<ScriptImportCubit, ScriptImportState>(
      'importFromText emits Error when repository.add throws FormatException',
      setUp: () {
        when(() => repository.add(any()))
            .thenThrow(const FormatException('bad'));
      },
      build: () => ScriptImportCubit(
        repository: repository,
        importService: importService,
      ),
      act: (cubit) => cubit.importFromText(
        text: 'A: Hello.\nB: World.',
        title: 'Test',
      ),
      expect: () => [
        isA<ScriptImportLoading>(),
        isA<ScriptImportError>(),
      ],
    );

    blocTest<ScriptImportCubit, ScriptImportState>(
      'importFromBytes delegates to importService.parseBytes',
      setUp: () {
        final script = TextParser().parse(
          title: 'Drop',
          content: 'A: Hi.\nB: Bye.',
        );
        when(
          () => importService.parseBytes(
            bytes: any(named: 'bytes'),
            fileName: any(named: 'fileName'),
          ),
        ).thenAnswer((_) async => script);
        when(() => repository.scripts).thenReturn([script]);
      },
      build: () => ScriptImportCubit(
        repository: repository,
        importService: importService,
      ),
      act: (cubit) => cubit.importFromBytes(
        bytes: Uint8List.fromList('A: Hi.\nB: Bye.'.codeUnits),
        fileName: 'test.txt',
      ),
      expect: () => [
        isA<ScriptImportLoading>(),
        isA<ScriptImportLoaded>(),
      ],
    );

    blocTest<ScriptImportCubit, ScriptImportState>(
      'importFromBytes handles null result',
      setUp: () {
        when(
          () => importService.parseBytes(
            bytes: any(named: 'bytes'),
            fileName: any(named: 'fileName'),
          ),
        ).thenAnswer((_) async => null);
      },
      build: () => ScriptImportCubit(
        repository: repository,
        importService: importService,
      ),
      act: (cubit) => cubit.importFromBytes(
        bytes: Uint8List(0),
        fileName: 'empty.txt',
      ),
      expect: () => [isA<ScriptImportLoading>()],
    );

    blocTest<ScriptImportCubit, ScriptImportState>(
      'importFromBytes emits Error on FormatException',
      setUp: () {
        when(
          () => importService.parseBytes(
            bytes: any(named: 'bytes'),
            fileName: any(named: 'fileName'),
          ),
        ).thenThrow(const FormatException('bad bytes'));
      },
      build: () => ScriptImportCubit(
        repository: repository,
        importService: importService,
      ),
      act: (cubit) => cubit.importFromBytes(
        bytes: Uint8List(0),
        fileName: 'bad.txt',
      ),
      expect: () => [
        isA<ScriptImportLoading>(),
        isA<ScriptImportError>(),
      ],
    );

    blocTest<ScriptImportCubit, ScriptImportState>(
      'importFromAsset loads and parses asset JSON',
      setUp: () {
        when(() => repository.scripts).thenReturn([]);
      },
      build: () {
        final assetBundle = FakeAssetBundle({
          'assets/test.json': json.encode({
            'title': 'Test Play',
            'text': 'ROMEO: Hello.\nJULIET: Hi.',
          }),
        });
        return ScriptImportCubit(
          repository: repository,
          importService: importService,
          assetBundle: assetBundle,
        );
      },
      act: (cubit) => cubit.importFromAsset('assets/test.json'),
      expect: () => [
        isA<ScriptImportLoading>(),
        isA<ScriptImportLoaded>(),
      ],
      verify: (_) {
        verify(() => repository.add(any())).called(1);
      },
    );

    blocTest<ScriptImportCubit, ScriptImportState>(
      'importFromAsset emits Error when asset not found',
      build: () {
        final assetBundle = FakeAssetBundle({});
        return ScriptImportCubit(
          repository: repository,
          importService: importService,
          assetBundle: assetBundle,
        );
      },
      act: (cubit) => cubit.importFromAsset('assets/missing.json'),
      expect: () => [
        isA<ScriptImportLoading>(),
        isA<ScriptImportError>(),
      ],
    );

    blocTest<ScriptImportCubit, ScriptImportState>(
      'removeScript delegates to repository and emits Loaded',
      build: () => ScriptImportCubit(
        repository: repository,
        importService: importService,
      ),
      act: (cubit) => cubit.removeScript(0),
      expect: () => [isA<ScriptImportLoaded>()],
      verify: (_) {
        verify(() => repository.removeAt(0)).called(1);
      },
    );

    test('state classes have correct Equatable props', () {
      const initial = ScriptImportInitial();
      expect(initial.props, isEmpty);

      const loaded = ScriptImportLoaded(scripts: []);
      expect(loaded.props, hasLength(1));

      const loading = ScriptImportLoading();
      expect(loading.props, isEmpty);

      const error = ScriptImportError(message: 'oops');
      expect(error.props, hasLength(1));
    });
  });
}
