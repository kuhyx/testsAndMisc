// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file

part of 'app_database.dart';

// ignore_for_file: type=lint
class $TextMarksTableTable extends TextMarksTable
    with TableInfo<$TextMarksTableTable, TextMarksTableData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $TextMarksTableTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _scriptIdMeta = const VerificationMeta(
    'scriptId',
  );
  @override
  late final GeneratedColumn<String> scriptId = GeneratedColumn<String>(
    'script_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _lineIndexMeta = const VerificationMeta(
    'lineIndex',
  );
  @override
  late final GeneratedColumn<int> lineIndex = GeneratedColumn<int>(
    'line_index',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _startOffsetMeta = const VerificationMeta(
    'startOffset',
  );
  @override
  late final GeneratedColumn<int> startOffset = GeneratedColumn<int>(
    'start_offset',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _endOffsetMeta = const VerificationMeta(
    'endOffset',
  );
  @override
  late final GeneratedColumn<int> endOffset = GeneratedColumn<int>(
    'end_offset',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _markTypeMeta = const VerificationMeta(
    'markType',
  );
  @override
  late final GeneratedColumn<String> markType = GeneratedColumn<String>(
    'mark_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    scriptId,
    lineIndex,
    startOffset,
    endOffset,
    markType,
    createdAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'text_marks';
  @override
  VerificationContext validateIntegrity(
    Insertable<TextMarksTableData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('script_id')) {
      context.handle(
        _scriptIdMeta,
        scriptId.isAcceptableOrUnknown(data['script_id']!, _scriptIdMeta),
      );
    } else if (isInserting) {
      context.missing(_scriptIdMeta);
    }
    if (data.containsKey('line_index')) {
      context.handle(
        _lineIndexMeta,
        lineIndex.isAcceptableOrUnknown(data['line_index']!, _lineIndexMeta),
      );
    } else if (isInserting) {
      context.missing(_lineIndexMeta);
    }
    if (data.containsKey('start_offset')) {
      context.handle(
        _startOffsetMeta,
        startOffset.isAcceptableOrUnknown(
          data['start_offset']!,
          _startOffsetMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_startOffsetMeta);
    }
    if (data.containsKey('end_offset')) {
      context.handle(
        _endOffsetMeta,
        endOffset.isAcceptableOrUnknown(data['end_offset']!, _endOffsetMeta),
      );
    } else if (isInserting) {
      context.missing(_endOffsetMeta);
    }
    if (data.containsKey('mark_type')) {
      context.handle(
        _markTypeMeta,
        markType.isAcceptableOrUnknown(data['mark_type']!, _markTypeMeta),
      );
    } else if (isInserting) {
      context.missing(_markTypeMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  TextMarksTableData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return TextMarksTableData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      scriptId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}script_id'],
      )!,
      lineIndex: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}line_index'],
      )!,
      startOffset: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}start_offset'],
      )!,
      endOffset: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}end_offset'],
      )!,
      markType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}mark_type'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $TextMarksTableTable createAlias(String alias) {
    return $TextMarksTableTable(attachedDatabase, alias);
  }
}

class TextMarksTableData extends DataClass
    implements Insertable<TextMarksTableData> {
  final String id;
  final String scriptId;
  final int lineIndex;
  final int startOffset;
  final int endOffset;
  final String markType;
  final DateTime createdAt;
  const TextMarksTableData({
    required this.id,
    required this.scriptId,
    required this.lineIndex,
    required this.startOffset,
    required this.endOffset,
    required this.markType,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['script_id'] = Variable<String>(scriptId);
    map['line_index'] = Variable<int>(lineIndex);
    map['start_offset'] = Variable<int>(startOffset);
    map['end_offset'] = Variable<int>(endOffset);
    map['mark_type'] = Variable<String>(markType);
    map['created_at'] = Variable<DateTime>(createdAt);
    return map;
  }

  TextMarksTableCompanion toCompanion(bool nullToAbsent) {
    return TextMarksTableCompanion(
      id: Value(id),
      scriptId: Value(scriptId),
      lineIndex: Value(lineIndex),
      startOffset: Value(startOffset),
      endOffset: Value(endOffset),
      markType: Value(markType),
      createdAt: Value(createdAt),
    );
  }

  factory TextMarksTableData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return TextMarksTableData(
      id: serializer.fromJson<String>(json['id']),
      scriptId: serializer.fromJson<String>(json['scriptId']),
      lineIndex: serializer.fromJson<int>(json['lineIndex']),
      startOffset: serializer.fromJson<int>(json['startOffset']),
      endOffset: serializer.fromJson<int>(json['endOffset']),
      markType: serializer.fromJson<String>(json['markType']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'scriptId': serializer.toJson<String>(scriptId),
      'lineIndex': serializer.toJson<int>(lineIndex),
      'startOffset': serializer.toJson<int>(startOffset),
      'endOffset': serializer.toJson<int>(endOffset),
      'markType': serializer.toJson<String>(markType),
      'createdAt': serializer.toJson<DateTime>(createdAt),
    };
  }

  TextMarksTableData copyWith({
    String? id,
    String? scriptId,
    int? lineIndex,
    int? startOffset,
    int? endOffset,
    String? markType,
    DateTime? createdAt,
  }) => TextMarksTableData(
    id: id ?? this.id,
    scriptId: scriptId ?? this.scriptId,
    lineIndex: lineIndex ?? this.lineIndex,
    startOffset: startOffset ?? this.startOffset,
    endOffset: endOffset ?? this.endOffset,
    markType: markType ?? this.markType,
    createdAt: createdAt ?? this.createdAt,
  );
  TextMarksTableData copyWithCompanion(TextMarksTableCompanion data) {
    return TextMarksTableData(
      id: data.id.present ? data.id.value : this.id,
      scriptId: data.scriptId.present ? data.scriptId.value : this.scriptId,
      lineIndex: data.lineIndex.present ? data.lineIndex.value : this.lineIndex,
      startOffset: data.startOffset.present
          ? data.startOffset.value
          : this.startOffset,
      endOffset: data.endOffset.present ? data.endOffset.value : this.endOffset,
      markType: data.markType.present ? data.markType.value : this.markType,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('TextMarksTableData(')
          ..write('id: $id, ')
          ..write('scriptId: $scriptId, ')
          ..write('lineIndex: $lineIndex, ')
          ..write('startOffset: $startOffset, ')
          ..write('endOffset: $endOffset, ')
          ..write('markType: $markType, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    scriptId,
    lineIndex,
    startOffset,
    endOffset,
    markType,
    createdAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is TextMarksTableData &&
          other.id == this.id &&
          other.scriptId == this.scriptId &&
          other.lineIndex == this.lineIndex &&
          other.startOffset == this.startOffset &&
          other.endOffset == this.endOffset &&
          other.markType == this.markType &&
          other.createdAt == this.createdAt);
}

class TextMarksTableCompanion extends UpdateCompanion<TextMarksTableData> {
  final Value<String> id;
  final Value<String> scriptId;
  final Value<int> lineIndex;
  final Value<int> startOffset;
  final Value<int> endOffset;
  final Value<String> markType;
  final Value<DateTime> createdAt;
  final Value<int> rowid;
  const TextMarksTableCompanion({
    this.id = const Value.absent(),
    this.scriptId = const Value.absent(),
    this.lineIndex = const Value.absent(),
    this.startOffset = const Value.absent(),
    this.endOffset = const Value.absent(),
    this.markType = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  TextMarksTableCompanion.insert({
    required String id,
    required String scriptId,
    required int lineIndex,
    required int startOffset,
    required int endOffset,
    required String markType,
    required DateTime createdAt,
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       scriptId = Value(scriptId),
       lineIndex = Value(lineIndex),
       startOffset = Value(startOffset),
       endOffset = Value(endOffset),
       markType = Value(markType),
       createdAt = Value(createdAt);
  static Insertable<TextMarksTableData> custom({
    Expression<String>? id,
    Expression<String>? scriptId,
    Expression<int>? lineIndex,
    Expression<int>? startOffset,
    Expression<int>? endOffset,
    Expression<String>? markType,
    Expression<DateTime>? createdAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (scriptId != null) 'script_id': scriptId,
      if (lineIndex != null) 'line_index': lineIndex,
      if (startOffset != null) 'start_offset': startOffset,
      if (endOffset != null) 'end_offset': endOffset,
      if (markType != null) 'mark_type': markType,
      if (createdAt != null) 'created_at': createdAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  TextMarksTableCompanion copyWith({
    Value<String>? id,
    Value<String>? scriptId,
    Value<int>? lineIndex,
    Value<int>? startOffset,
    Value<int>? endOffset,
    Value<String>? markType,
    Value<DateTime>? createdAt,
    Value<int>? rowid,
  }) {
    return TextMarksTableCompanion(
      id: id ?? this.id,
      scriptId: scriptId ?? this.scriptId,
      lineIndex: lineIndex ?? this.lineIndex,
      startOffset: startOffset ?? this.startOffset,
      endOffset: endOffset ?? this.endOffset,
      markType: markType ?? this.markType,
      createdAt: createdAt ?? this.createdAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (scriptId.present) {
      map['script_id'] = Variable<String>(scriptId.value);
    }
    if (lineIndex.present) {
      map['line_index'] = Variable<int>(lineIndex.value);
    }
    if (startOffset.present) {
      map['start_offset'] = Variable<int>(startOffset.value);
    }
    if (endOffset.present) {
      map['end_offset'] = Variable<int>(endOffset.value);
    }
    if (markType.present) {
      map['mark_type'] = Variable<String>(markType.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('TextMarksTableCompanion(')
          ..write('id: $id, ')
          ..write('scriptId: $scriptId, ')
          ..write('lineIndex: $lineIndex, ')
          ..write('startOffset: $startOffset, ')
          ..write('endOffset: $endOffset, ')
          ..write('markType: $markType, ')
          ..write('createdAt: $createdAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $LineNotesTableTable extends LineNotesTable
    with TableInfo<$LineNotesTableTable, LineNotesTableData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LineNotesTableTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _scriptIdMeta = const VerificationMeta(
    'scriptId',
  );
  @override
  late final GeneratedColumn<String> scriptId = GeneratedColumn<String>(
    'script_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _lineIndexMeta = const VerificationMeta(
    'lineIndex',
  );
  @override
  late final GeneratedColumn<int> lineIndex = GeneratedColumn<int>(
    'line_index',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _categoryMeta = const VerificationMeta(
    'category',
  );
  @override
  late final GeneratedColumn<String> category = GeneratedColumn<String>(
    'category',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _noteTextMeta = const VerificationMeta(
    'noteText',
  );
  @override
  late final GeneratedColumn<String> noteText = GeneratedColumn<String>(
    'note_text',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    scriptId,
    lineIndex,
    category,
    noteText,
    createdAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'line_notes';
  @override
  VerificationContext validateIntegrity(
    Insertable<LineNotesTableData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('script_id')) {
      context.handle(
        _scriptIdMeta,
        scriptId.isAcceptableOrUnknown(data['script_id']!, _scriptIdMeta),
      );
    } else if (isInserting) {
      context.missing(_scriptIdMeta);
    }
    if (data.containsKey('line_index')) {
      context.handle(
        _lineIndexMeta,
        lineIndex.isAcceptableOrUnknown(data['line_index']!, _lineIndexMeta),
      );
    } else if (isInserting) {
      context.missing(_lineIndexMeta);
    }
    if (data.containsKey('category')) {
      context.handle(
        _categoryMeta,
        category.isAcceptableOrUnknown(data['category']!, _categoryMeta),
      );
    } else if (isInserting) {
      context.missing(_categoryMeta);
    }
    if (data.containsKey('note_text')) {
      context.handle(
        _noteTextMeta,
        noteText.isAcceptableOrUnknown(data['note_text']!, _noteTextMeta),
      );
    } else if (isInserting) {
      context.missing(_noteTextMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  LineNotesTableData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return LineNotesTableData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      scriptId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}script_id'],
      )!,
      lineIndex: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}line_index'],
      )!,
      category: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}category'],
      )!,
      noteText: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}note_text'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $LineNotesTableTable createAlias(String alias) {
    return $LineNotesTableTable(attachedDatabase, alias);
  }
}

class LineNotesTableData extends DataClass
    implements Insertable<LineNotesTableData> {
  final String id;
  final String scriptId;
  final int lineIndex;
  final String category;
  final String noteText;
  final DateTime createdAt;
  const LineNotesTableData({
    required this.id,
    required this.scriptId,
    required this.lineIndex,
    required this.category,
    required this.noteText,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['script_id'] = Variable<String>(scriptId);
    map['line_index'] = Variable<int>(lineIndex);
    map['category'] = Variable<String>(category);
    map['note_text'] = Variable<String>(noteText);
    map['created_at'] = Variable<DateTime>(createdAt);
    return map;
  }

  LineNotesTableCompanion toCompanion(bool nullToAbsent) {
    return LineNotesTableCompanion(
      id: Value(id),
      scriptId: Value(scriptId),
      lineIndex: Value(lineIndex),
      category: Value(category),
      noteText: Value(noteText),
      createdAt: Value(createdAt),
    );
  }

  factory LineNotesTableData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return LineNotesTableData(
      id: serializer.fromJson<String>(json['id']),
      scriptId: serializer.fromJson<String>(json['scriptId']),
      lineIndex: serializer.fromJson<int>(json['lineIndex']),
      category: serializer.fromJson<String>(json['category']),
      noteText: serializer.fromJson<String>(json['noteText']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'scriptId': serializer.toJson<String>(scriptId),
      'lineIndex': serializer.toJson<int>(lineIndex),
      'category': serializer.toJson<String>(category),
      'noteText': serializer.toJson<String>(noteText),
      'createdAt': serializer.toJson<DateTime>(createdAt),
    };
  }

  LineNotesTableData copyWith({
    String? id,
    String? scriptId,
    int? lineIndex,
    String? category,
    String? noteText,
    DateTime? createdAt,
  }) => LineNotesTableData(
    id: id ?? this.id,
    scriptId: scriptId ?? this.scriptId,
    lineIndex: lineIndex ?? this.lineIndex,
    category: category ?? this.category,
    noteText: noteText ?? this.noteText,
    createdAt: createdAt ?? this.createdAt,
  );
  LineNotesTableData copyWithCompanion(LineNotesTableCompanion data) {
    return LineNotesTableData(
      id: data.id.present ? data.id.value : this.id,
      scriptId: data.scriptId.present ? data.scriptId.value : this.scriptId,
      lineIndex: data.lineIndex.present ? data.lineIndex.value : this.lineIndex,
      category: data.category.present ? data.category.value : this.category,
      noteText: data.noteText.present ? data.noteText.value : this.noteText,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('LineNotesTableData(')
          ..write('id: $id, ')
          ..write('scriptId: $scriptId, ')
          ..write('lineIndex: $lineIndex, ')
          ..write('category: $category, ')
          ..write('noteText: $noteText, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, scriptId, lineIndex, category, noteText, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is LineNotesTableData &&
          other.id == this.id &&
          other.scriptId == this.scriptId &&
          other.lineIndex == this.lineIndex &&
          other.category == this.category &&
          other.noteText == this.noteText &&
          other.createdAt == this.createdAt);
}

class LineNotesTableCompanion extends UpdateCompanion<LineNotesTableData> {
  final Value<String> id;
  final Value<String> scriptId;
  final Value<int> lineIndex;
  final Value<String> category;
  final Value<String> noteText;
  final Value<DateTime> createdAt;
  final Value<int> rowid;
  const LineNotesTableCompanion({
    this.id = const Value.absent(),
    this.scriptId = const Value.absent(),
    this.lineIndex = const Value.absent(),
    this.category = const Value.absent(),
    this.noteText = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  LineNotesTableCompanion.insert({
    required String id,
    required String scriptId,
    required int lineIndex,
    required String category,
    required String noteText,
    required DateTime createdAt,
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       scriptId = Value(scriptId),
       lineIndex = Value(lineIndex),
       category = Value(category),
       noteText = Value(noteText),
       createdAt = Value(createdAt);
  static Insertable<LineNotesTableData> custom({
    Expression<String>? id,
    Expression<String>? scriptId,
    Expression<int>? lineIndex,
    Expression<String>? category,
    Expression<String>? noteText,
    Expression<DateTime>? createdAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (scriptId != null) 'script_id': scriptId,
      if (lineIndex != null) 'line_index': lineIndex,
      if (category != null) 'category': category,
      if (noteText != null) 'note_text': noteText,
      if (createdAt != null) 'created_at': createdAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  LineNotesTableCompanion copyWith({
    Value<String>? id,
    Value<String>? scriptId,
    Value<int>? lineIndex,
    Value<String>? category,
    Value<String>? noteText,
    Value<DateTime>? createdAt,
    Value<int>? rowid,
  }) {
    return LineNotesTableCompanion(
      id: id ?? this.id,
      scriptId: scriptId ?? this.scriptId,
      lineIndex: lineIndex ?? this.lineIndex,
      category: category ?? this.category,
      noteText: noteText ?? this.noteText,
      createdAt: createdAt ?? this.createdAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (scriptId.present) {
      map['script_id'] = Variable<String>(scriptId.value);
    }
    if (lineIndex.present) {
      map['line_index'] = Variable<int>(lineIndex.value);
    }
    if (category.present) {
      map['category'] = Variable<String>(category.value);
    }
    if (noteText.present) {
      map['note_text'] = Variable<String>(noteText.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LineNotesTableCompanion(')
          ..write('id: $id, ')
          ..write('scriptId: $scriptId, ')
          ..write('lineIndex: $lineIndex, ')
          ..write('category: $category, ')
          ..write('noteText: $noteText, ')
          ..write('createdAt: $createdAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $AnnotationSnapshotsTableTable extends AnnotationSnapshotsTable
    with
        TableInfo<
          $AnnotationSnapshotsTableTable,
          AnnotationSnapshotsTableData
        > {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $AnnotationSnapshotsTableTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _scriptIdMeta = const VerificationMeta(
    'scriptId',
  );
  @override
  late final GeneratedColumn<String> scriptId = GeneratedColumn<String>(
    'script_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _timestampMeta = const VerificationMeta(
    'timestamp',
  );
  @override
  late final GeneratedColumn<DateTime> timestamp = GeneratedColumn<DateTime>(
    'timestamp',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _snapshotJsonMeta = const VerificationMeta(
    'snapshotJson',
  );
  @override
  late final GeneratedColumn<String> snapshotJson = GeneratedColumn<String>(
    'snapshot_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [id, scriptId, timestamp, snapshotJson];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'annotation_snapshots';
  @override
  VerificationContext validateIntegrity(
    Insertable<AnnotationSnapshotsTableData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('script_id')) {
      context.handle(
        _scriptIdMeta,
        scriptId.isAcceptableOrUnknown(data['script_id']!, _scriptIdMeta),
      );
    } else if (isInserting) {
      context.missing(_scriptIdMeta);
    }
    if (data.containsKey('timestamp')) {
      context.handle(
        _timestampMeta,
        timestamp.isAcceptableOrUnknown(data['timestamp']!, _timestampMeta),
      );
    } else if (isInserting) {
      context.missing(_timestampMeta);
    }
    if (data.containsKey('snapshot_json')) {
      context.handle(
        _snapshotJsonMeta,
        snapshotJson.isAcceptableOrUnknown(
          data['snapshot_json']!,
          _snapshotJsonMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_snapshotJsonMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  AnnotationSnapshotsTableData map(
    Map<String, dynamic> data, {
    String? tablePrefix,
  }) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return AnnotationSnapshotsTableData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      scriptId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}script_id'],
      )!,
      timestamp: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}timestamp'],
      )!,
      snapshotJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}snapshot_json'],
      )!,
    );
  }

  @override
  $AnnotationSnapshotsTableTable createAlias(String alias) {
    return $AnnotationSnapshotsTableTable(attachedDatabase, alias);
  }
}

class AnnotationSnapshotsTableData extends DataClass
    implements Insertable<AnnotationSnapshotsTableData> {
  final String id;
  final String scriptId;
  final DateTime timestamp;
  final String snapshotJson;
  const AnnotationSnapshotsTableData({
    required this.id,
    required this.scriptId,
    required this.timestamp,
    required this.snapshotJson,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['script_id'] = Variable<String>(scriptId);
    map['timestamp'] = Variable<DateTime>(timestamp);
    map['snapshot_json'] = Variable<String>(snapshotJson);
    return map;
  }

  AnnotationSnapshotsTableCompanion toCompanion(bool nullToAbsent) {
    return AnnotationSnapshotsTableCompanion(
      id: Value(id),
      scriptId: Value(scriptId),
      timestamp: Value(timestamp),
      snapshotJson: Value(snapshotJson),
    );
  }

  factory AnnotationSnapshotsTableData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return AnnotationSnapshotsTableData(
      id: serializer.fromJson<String>(json['id']),
      scriptId: serializer.fromJson<String>(json['scriptId']),
      timestamp: serializer.fromJson<DateTime>(json['timestamp']),
      snapshotJson: serializer.fromJson<String>(json['snapshotJson']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'scriptId': serializer.toJson<String>(scriptId),
      'timestamp': serializer.toJson<DateTime>(timestamp),
      'snapshotJson': serializer.toJson<String>(snapshotJson),
    };
  }

  AnnotationSnapshotsTableData copyWith({
    String? id,
    String? scriptId,
    DateTime? timestamp,
    String? snapshotJson,
  }) => AnnotationSnapshotsTableData(
    id: id ?? this.id,
    scriptId: scriptId ?? this.scriptId,
    timestamp: timestamp ?? this.timestamp,
    snapshotJson: snapshotJson ?? this.snapshotJson,
  );
  AnnotationSnapshotsTableData copyWithCompanion(
    AnnotationSnapshotsTableCompanion data,
  ) {
    return AnnotationSnapshotsTableData(
      id: data.id.present ? data.id.value : this.id,
      scriptId: data.scriptId.present ? data.scriptId.value : this.scriptId,
      timestamp: data.timestamp.present ? data.timestamp.value : this.timestamp,
      snapshotJson: data.snapshotJson.present
          ? data.snapshotJson.value
          : this.snapshotJson,
    );
  }

  @override
  String toString() {
    return (StringBuffer('AnnotationSnapshotsTableData(')
          ..write('id: $id, ')
          ..write('scriptId: $scriptId, ')
          ..write('timestamp: $timestamp, ')
          ..write('snapshotJson: $snapshotJson')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, scriptId, timestamp, snapshotJson);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is AnnotationSnapshotsTableData &&
          other.id == this.id &&
          other.scriptId == this.scriptId &&
          other.timestamp == this.timestamp &&
          other.snapshotJson == this.snapshotJson);
}

class AnnotationSnapshotsTableCompanion
    extends UpdateCompanion<AnnotationSnapshotsTableData> {
  final Value<String> id;
  final Value<String> scriptId;
  final Value<DateTime> timestamp;
  final Value<String> snapshotJson;
  final Value<int> rowid;
  const AnnotationSnapshotsTableCompanion({
    this.id = const Value.absent(),
    this.scriptId = const Value.absent(),
    this.timestamp = const Value.absent(),
    this.snapshotJson = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  AnnotationSnapshotsTableCompanion.insert({
    required String id,
    required String scriptId,
    required DateTime timestamp,
    required String snapshotJson,
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       scriptId = Value(scriptId),
       timestamp = Value(timestamp),
       snapshotJson = Value(snapshotJson);
  static Insertable<AnnotationSnapshotsTableData> custom({
    Expression<String>? id,
    Expression<String>? scriptId,
    Expression<DateTime>? timestamp,
    Expression<String>? snapshotJson,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (scriptId != null) 'script_id': scriptId,
      if (timestamp != null) 'timestamp': timestamp,
      if (snapshotJson != null) 'snapshot_json': snapshotJson,
      if (rowid != null) 'rowid': rowid,
    });
  }

  AnnotationSnapshotsTableCompanion copyWith({
    Value<String>? id,
    Value<String>? scriptId,
    Value<DateTime>? timestamp,
    Value<String>? snapshotJson,
    Value<int>? rowid,
  }) {
    return AnnotationSnapshotsTableCompanion(
      id: id ?? this.id,
      scriptId: scriptId ?? this.scriptId,
      timestamp: timestamp ?? this.timestamp,
      snapshotJson: snapshotJson ?? this.snapshotJson,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (scriptId.present) {
      map['script_id'] = Variable<String>(scriptId.value);
    }
    if (timestamp.present) {
      map['timestamp'] = Variable<DateTime>(timestamp.value);
    }
    if (snapshotJson.present) {
      map['snapshot_json'] = Variable<String>(snapshotJson.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('AnnotationSnapshotsTableCompanion(')
          ..write('id: $id, ')
          ..write('scriptId: $scriptId, ')
          ..write('timestamp: $timestamp, ')
          ..write('snapshotJson: $snapshotJson, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $LineRecordingsTableTable extends LineRecordingsTable
    with TableInfo<$LineRecordingsTableTable, LineRecordingsTableData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LineRecordingsTableTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _scriptIdMeta = const VerificationMeta(
    'scriptId',
  );
  @override
  late final GeneratedColumn<String> scriptId = GeneratedColumn<String>(
    'script_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _lineIndexMeta = const VerificationMeta(
    'lineIndex',
  );
  @override
  late final GeneratedColumn<int> lineIndex = GeneratedColumn<int>(
    'line_index',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _filePathMeta = const VerificationMeta(
    'filePath',
  );
  @override
  late final GeneratedColumn<String> filePath = GeneratedColumn<String>(
    'file_path',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _durationMsMeta = const VerificationMeta(
    'durationMs',
  );
  @override
  late final GeneratedColumn<int> durationMs = GeneratedColumn<int>(
    'duration_ms',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _gradeMeta = const VerificationMeta('grade');
  @override
  late final GeneratedColumn<int> grade = GeneratedColumn<int>(
    'grade',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    scriptId,
    lineIndex,
    filePath,
    durationMs,
    createdAt,
    grade,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'line_recordings';
  @override
  VerificationContext validateIntegrity(
    Insertable<LineRecordingsTableData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('script_id')) {
      context.handle(
        _scriptIdMeta,
        scriptId.isAcceptableOrUnknown(data['script_id']!, _scriptIdMeta),
      );
    } else if (isInserting) {
      context.missing(_scriptIdMeta);
    }
    if (data.containsKey('line_index')) {
      context.handle(
        _lineIndexMeta,
        lineIndex.isAcceptableOrUnknown(data['line_index']!, _lineIndexMeta),
      );
    } else if (isInserting) {
      context.missing(_lineIndexMeta);
    }
    if (data.containsKey('file_path')) {
      context.handle(
        _filePathMeta,
        filePath.isAcceptableOrUnknown(data['file_path']!, _filePathMeta),
      );
    } else if (isInserting) {
      context.missing(_filePathMeta);
    }
    if (data.containsKey('duration_ms')) {
      context.handle(
        _durationMsMeta,
        durationMs.isAcceptableOrUnknown(data['duration_ms']!, _durationMsMeta),
      );
    } else if (isInserting) {
      context.missing(_durationMsMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('grade')) {
      context.handle(
        _gradeMeta,
        grade.isAcceptableOrUnknown(data['grade']!, _gradeMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  LineRecordingsTableData map(
    Map<String, dynamic> data, {
    String? tablePrefix,
  }) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return LineRecordingsTableData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      scriptId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}script_id'],
      )!,
      lineIndex: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}line_index'],
      )!,
      filePath: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}file_path'],
      )!,
      durationMs: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}duration_ms'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      grade: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}grade'],
      ),
    );
  }

  @override
  $LineRecordingsTableTable createAlias(String alias) {
    return $LineRecordingsTableTable(attachedDatabase, alias);
  }
}

class LineRecordingsTableData extends DataClass
    implements Insertable<LineRecordingsTableData> {
  final String id;
  final String scriptId;
  final int lineIndex;
  final String filePath;
  final int durationMs;
  final DateTime createdAt;
  final int? grade;
  const LineRecordingsTableData({
    required this.id,
    required this.scriptId,
    required this.lineIndex,
    required this.filePath,
    required this.durationMs,
    required this.createdAt,
    this.grade,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['script_id'] = Variable<String>(scriptId);
    map['line_index'] = Variable<int>(lineIndex);
    map['file_path'] = Variable<String>(filePath);
    map['duration_ms'] = Variable<int>(durationMs);
    map['created_at'] = Variable<DateTime>(createdAt);
    if (!nullToAbsent || grade != null) {
      map['grade'] = Variable<int>(grade);
    }
    return map;
  }

  LineRecordingsTableCompanion toCompanion(bool nullToAbsent) {
    return LineRecordingsTableCompanion(
      id: Value(id),
      scriptId: Value(scriptId),
      lineIndex: Value(lineIndex),
      filePath: Value(filePath),
      durationMs: Value(durationMs),
      createdAt: Value(createdAt),
      grade: grade == null && nullToAbsent
          ? const Value.absent()
          : Value(grade),
    );
  }

  factory LineRecordingsTableData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return LineRecordingsTableData(
      id: serializer.fromJson<String>(json['id']),
      scriptId: serializer.fromJson<String>(json['scriptId']),
      lineIndex: serializer.fromJson<int>(json['lineIndex']),
      filePath: serializer.fromJson<String>(json['filePath']),
      durationMs: serializer.fromJson<int>(json['durationMs']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      grade: serializer.fromJson<int?>(json['grade']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'scriptId': serializer.toJson<String>(scriptId),
      'lineIndex': serializer.toJson<int>(lineIndex),
      'filePath': serializer.toJson<String>(filePath),
      'durationMs': serializer.toJson<int>(durationMs),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'grade': serializer.toJson<int?>(grade),
    };
  }

  LineRecordingsTableData copyWith({
    String? id,
    String? scriptId,
    int? lineIndex,
    String? filePath,
    int? durationMs,
    DateTime? createdAt,
    Value<int?> grade = const Value.absent(),
  }) => LineRecordingsTableData(
    id: id ?? this.id,
    scriptId: scriptId ?? this.scriptId,
    lineIndex: lineIndex ?? this.lineIndex,
    filePath: filePath ?? this.filePath,
    durationMs: durationMs ?? this.durationMs,
    createdAt: createdAt ?? this.createdAt,
    grade: grade.present ? grade.value : this.grade,
  );
  LineRecordingsTableData copyWithCompanion(LineRecordingsTableCompanion data) {
    return LineRecordingsTableData(
      id: data.id.present ? data.id.value : this.id,
      scriptId: data.scriptId.present ? data.scriptId.value : this.scriptId,
      lineIndex: data.lineIndex.present ? data.lineIndex.value : this.lineIndex,
      filePath: data.filePath.present ? data.filePath.value : this.filePath,
      durationMs: data.durationMs.present
          ? data.durationMs.value
          : this.durationMs,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      grade: data.grade.present ? data.grade.value : this.grade,
    );
  }

  @override
  String toString() {
    return (StringBuffer('LineRecordingsTableData(')
          ..write('id: $id, ')
          ..write('scriptId: $scriptId, ')
          ..write('lineIndex: $lineIndex, ')
          ..write('filePath: $filePath, ')
          ..write('durationMs: $durationMs, ')
          ..write('createdAt: $createdAt, ')
          ..write('grade: $grade')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    scriptId,
    lineIndex,
    filePath,
    durationMs,
    createdAt,
    grade,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is LineRecordingsTableData &&
          other.id == this.id &&
          other.scriptId == this.scriptId &&
          other.lineIndex == this.lineIndex &&
          other.filePath == this.filePath &&
          other.durationMs == this.durationMs &&
          other.createdAt == this.createdAt &&
          other.grade == this.grade);
}

class LineRecordingsTableCompanion
    extends UpdateCompanion<LineRecordingsTableData> {
  final Value<String> id;
  final Value<String> scriptId;
  final Value<int> lineIndex;
  final Value<String> filePath;
  final Value<int> durationMs;
  final Value<DateTime> createdAt;
  final Value<int?> grade;
  final Value<int> rowid;
  const LineRecordingsTableCompanion({
    this.id = const Value.absent(),
    this.scriptId = const Value.absent(),
    this.lineIndex = const Value.absent(),
    this.filePath = const Value.absent(),
    this.durationMs = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.grade = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  LineRecordingsTableCompanion.insert({
    required String id,
    required String scriptId,
    required int lineIndex,
    required String filePath,
    required int durationMs,
    required DateTime createdAt,
    this.grade = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       scriptId = Value(scriptId),
       lineIndex = Value(lineIndex),
       filePath = Value(filePath),
       durationMs = Value(durationMs),
       createdAt = Value(createdAt);
  static Insertable<LineRecordingsTableData> custom({
    Expression<String>? id,
    Expression<String>? scriptId,
    Expression<int>? lineIndex,
    Expression<String>? filePath,
    Expression<int>? durationMs,
    Expression<DateTime>? createdAt,
    Expression<int>? grade,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (scriptId != null) 'script_id': scriptId,
      if (lineIndex != null) 'line_index': lineIndex,
      if (filePath != null) 'file_path': filePath,
      if (durationMs != null) 'duration_ms': durationMs,
      if (createdAt != null) 'created_at': createdAt,
      if (grade != null) 'grade': grade,
      if (rowid != null) 'rowid': rowid,
    });
  }

  LineRecordingsTableCompanion copyWith({
    Value<String>? id,
    Value<String>? scriptId,
    Value<int>? lineIndex,
    Value<String>? filePath,
    Value<int>? durationMs,
    Value<DateTime>? createdAt,
    Value<int?>? grade,
    Value<int>? rowid,
  }) {
    return LineRecordingsTableCompanion(
      id: id ?? this.id,
      scriptId: scriptId ?? this.scriptId,
      lineIndex: lineIndex ?? this.lineIndex,
      filePath: filePath ?? this.filePath,
      durationMs: durationMs ?? this.durationMs,
      createdAt: createdAt ?? this.createdAt,
      grade: grade ?? this.grade,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (scriptId.present) {
      map['script_id'] = Variable<String>(scriptId.value);
    }
    if (lineIndex.present) {
      map['line_index'] = Variable<int>(lineIndex.value);
    }
    if (filePath.present) {
      map['file_path'] = Variable<String>(filePath.value);
    }
    if (durationMs.present) {
      map['duration_ms'] = Variable<int>(durationMs.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (grade.present) {
      map['grade'] = Variable<int>(grade.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LineRecordingsTableCompanion(')
          ..write('id: $id, ')
          ..write('scriptId: $scriptId, ')
          ..write('lineIndex: $lineIndex, ')
          ..write('filePath: $filePath, ')
          ..write('durationMs: $durationMs, ')
          ..write('createdAt: $createdAt, ')
          ..write('grade: $grade, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $TextMarksTableTable textMarksTable = $TextMarksTableTable(this);
  late final $LineNotesTableTable lineNotesTable = $LineNotesTableTable(this);
  late final $AnnotationSnapshotsTableTable annotationSnapshotsTable =
      $AnnotationSnapshotsTableTable(this);
  late final $LineRecordingsTableTable lineRecordingsTable =
      $LineRecordingsTableTable(this);
  late final AnnotationDao annotationDao = AnnotationDao(this as AppDatabase);
  late final RecordingDao recordingDao = RecordingDao(this as AppDatabase);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    textMarksTable,
    lineNotesTable,
    annotationSnapshotsTable,
    lineRecordingsTable,
  ];
}

typedef $$TextMarksTableTableCreateCompanionBuilder =
    TextMarksTableCompanion Function({
      required String id,
      required String scriptId,
      required int lineIndex,
      required int startOffset,
      required int endOffset,
      required String markType,
      required DateTime createdAt,
      Value<int> rowid,
    });
typedef $$TextMarksTableTableUpdateCompanionBuilder =
    TextMarksTableCompanion Function({
      Value<String> id,
      Value<String> scriptId,
      Value<int> lineIndex,
      Value<int> startOffset,
      Value<int> endOffset,
      Value<String> markType,
      Value<DateTime> createdAt,
      Value<int> rowid,
    });

class $$TextMarksTableTableFilterComposer
    extends Composer<_$AppDatabase, $TextMarksTableTable> {
  $$TextMarksTableTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get scriptId => $composableBuilder(
    column: $table.scriptId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get lineIndex => $composableBuilder(
    column: $table.lineIndex,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get startOffset => $composableBuilder(
    column: $table.startOffset,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get endOffset => $composableBuilder(
    column: $table.endOffset,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get markType => $composableBuilder(
    column: $table.markType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$TextMarksTableTableOrderingComposer
    extends Composer<_$AppDatabase, $TextMarksTableTable> {
  $$TextMarksTableTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get scriptId => $composableBuilder(
    column: $table.scriptId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get lineIndex => $composableBuilder(
    column: $table.lineIndex,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get startOffset => $composableBuilder(
    column: $table.startOffset,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get endOffset => $composableBuilder(
    column: $table.endOffset,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get markType => $composableBuilder(
    column: $table.markType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$TextMarksTableTableAnnotationComposer
    extends Composer<_$AppDatabase, $TextMarksTableTable> {
  $$TextMarksTableTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get scriptId =>
      $composableBuilder(column: $table.scriptId, builder: (column) => column);

  GeneratedColumn<int> get lineIndex =>
      $composableBuilder(column: $table.lineIndex, builder: (column) => column);

  GeneratedColumn<int> get startOffset => $composableBuilder(
    column: $table.startOffset,
    builder: (column) => column,
  );

  GeneratedColumn<int> get endOffset =>
      $composableBuilder(column: $table.endOffset, builder: (column) => column);

  GeneratedColumn<String> get markType =>
      $composableBuilder(column: $table.markType, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$TextMarksTableTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $TextMarksTableTable,
          TextMarksTableData,
          $$TextMarksTableTableFilterComposer,
          $$TextMarksTableTableOrderingComposer,
          $$TextMarksTableTableAnnotationComposer,
          $$TextMarksTableTableCreateCompanionBuilder,
          $$TextMarksTableTableUpdateCompanionBuilder,
          (
            TextMarksTableData,
            BaseReferences<
              _$AppDatabase,
              $TextMarksTableTable,
              TextMarksTableData
            >,
          ),
          TextMarksTableData,
          PrefetchHooks Function()
        > {
  $$TextMarksTableTableTableManager(
    _$AppDatabase db,
    $TextMarksTableTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$TextMarksTableTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$TextMarksTableTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$TextMarksTableTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<String> scriptId = const Value.absent(),
                Value<int> lineIndex = const Value.absent(),
                Value<int> startOffset = const Value.absent(),
                Value<int> endOffset = const Value.absent(),
                Value<String> markType = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => TextMarksTableCompanion(
                id: id,
                scriptId: scriptId,
                lineIndex: lineIndex,
                startOffset: startOffset,
                endOffset: endOffset,
                markType: markType,
                createdAt: createdAt,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                required String scriptId,
                required int lineIndex,
                required int startOffset,
                required int endOffset,
                required String markType,
                required DateTime createdAt,
                Value<int> rowid = const Value.absent(),
              }) => TextMarksTableCompanion.insert(
                id: id,
                scriptId: scriptId,
                lineIndex: lineIndex,
                startOffset: startOffset,
                endOffset: endOffset,
                markType: markType,
                createdAt: createdAt,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$TextMarksTableTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $TextMarksTableTable,
      TextMarksTableData,
      $$TextMarksTableTableFilterComposer,
      $$TextMarksTableTableOrderingComposer,
      $$TextMarksTableTableAnnotationComposer,
      $$TextMarksTableTableCreateCompanionBuilder,
      $$TextMarksTableTableUpdateCompanionBuilder,
      (
        TextMarksTableData,
        BaseReferences<_$AppDatabase, $TextMarksTableTable, TextMarksTableData>,
      ),
      TextMarksTableData,
      PrefetchHooks Function()
    >;
typedef $$LineNotesTableTableCreateCompanionBuilder =
    LineNotesTableCompanion Function({
      required String id,
      required String scriptId,
      required int lineIndex,
      required String category,
      required String noteText,
      required DateTime createdAt,
      Value<int> rowid,
    });
typedef $$LineNotesTableTableUpdateCompanionBuilder =
    LineNotesTableCompanion Function({
      Value<String> id,
      Value<String> scriptId,
      Value<int> lineIndex,
      Value<String> category,
      Value<String> noteText,
      Value<DateTime> createdAt,
      Value<int> rowid,
    });

class $$LineNotesTableTableFilterComposer
    extends Composer<_$AppDatabase, $LineNotesTableTable> {
  $$LineNotesTableTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get scriptId => $composableBuilder(
    column: $table.scriptId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get lineIndex => $composableBuilder(
    column: $table.lineIndex,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get category => $composableBuilder(
    column: $table.category,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get noteText => $composableBuilder(
    column: $table.noteText,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$LineNotesTableTableOrderingComposer
    extends Composer<_$AppDatabase, $LineNotesTableTable> {
  $$LineNotesTableTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get scriptId => $composableBuilder(
    column: $table.scriptId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get lineIndex => $composableBuilder(
    column: $table.lineIndex,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get category => $composableBuilder(
    column: $table.category,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get noteText => $composableBuilder(
    column: $table.noteText,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$LineNotesTableTableAnnotationComposer
    extends Composer<_$AppDatabase, $LineNotesTableTable> {
  $$LineNotesTableTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get scriptId =>
      $composableBuilder(column: $table.scriptId, builder: (column) => column);

  GeneratedColumn<int> get lineIndex =>
      $composableBuilder(column: $table.lineIndex, builder: (column) => column);

  GeneratedColumn<String> get category =>
      $composableBuilder(column: $table.category, builder: (column) => column);

  GeneratedColumn<String> get noteText =>
      $composableBuilder(column: $table.noteText, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$LineNotesTableTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $LineNotesTableTable,
          LineNotesTableData,
          $$LineNotesTableTableFilterComposer,
          $$LineNotesTableTableOrderingComposer,
          $$LineNotesTableTableAnnotationComposer,
          $$LineNotesTableTableCreateCompanionBuilder,
          $$LineNotesTableTableUpdateCompanionBuilder,
          (
            LineNotesTableData,
            BaseReferences<
              _$AppDatabase,
              $LineNotesTableTable,
              LineNotesTableData
            >,
          ),
          LineNotesTableData,
          PrefetchHooks Function()
        > {
  $$LineNotesTableTableTableManager(
    _$AppDatabase db,
    $LineNotesTableTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$LineNotesTableTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$LineNotesTableTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$LineNotesTableTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<String> scriptId = const Value.absent(),
                Value<int> lineIndex = const Value.absent(),
                Value<String> category = const Value.absent(),
                Value<String> noteText = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => LineNotesTableCompanion(
                id: id,
                scriptId: scriptId,
                lineIndex: lineIndex,
                category: category,
                noteText: noteText,
                createdAt: createdAt,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                required String scriptId,
                required int lineIndex,
                required String category,
                required String noteText,
                required DateTime createdAt,
                Value<int> rowid = const Value.absent(),
              }) => LineNotesTableCompanion.insert(
                id: id,
                scriptId: scriptId,
                lineIndex: lineIndex,
                category: category,
                noteText: noteText,
                createdAt: createdAt,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$LineNotesTableTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $LineNotesTableTable,
      LineNotesTableData,
      $$LineNotesTableTableFilterComposer,
      $$LineNotesTableTableOrderingComposer,
      $$LineNotesTableTableAnnotationComposer,
      $$LineNotesTableTableCreateCompanionBuilder,
      $$LineNotesTableTableUpdateCompanionBuilder,
      (
        LineNotesTableData,
        BaseReferences<_$AppDatabase, $LineNotesTableTable, LineNotesTableData>,
      ),
      LineNotesTableData,
      PrefetchHooks Function()
    >;
typedef $$AnnotationSnapshotsTableTableCreateCompanionBuilder =
    AnnotationSnapshotsTableCompanion Function({
      required String id,
      required String scriptId,
      required DateTime timestamp,
      required String snapshotJson,
      Value<int> rowid,
    });
typedef $$AnnotationSnapshotsTableTableUpdateCompanionBuilder =
    AnnotationSnapshotsTableCompanion Function({
      Value<String> id,
      Value<String> scriptId,
      Value<DateTime> timestamp,
      Value<String> snapshotJson,
      Value<int> rowid,
    });

class $$AnnotationSnapshotsTableTableFilterComposer
    extends Composer<_$AppDatabase, $AnnotationSnapshotsTableTable> {
  $$AnnotationSnapshotsTableTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get scriptId => $composableBuilder(
    column: $table.scriptId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get timestamp => $composableBuilder(
    column: $table.timestamp,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get snapshotJson => $composableBuilder(
    column: $table.snapshotJson,
    builder: (column) => ColumnFilters(column),
  );
}

class $$AnnotationSnapshotsTableTableOrderingComposer
    extends Composer<_$AppDatabase, $AnnotationSnapshotsTableTable> {
  $$AnnotationSnapshotsTableTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get scriptId => $composableBuilder(
    column: $table.scriptId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get timestamp => $composableBuilder(
    column: $table.timestamp,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get snapshotJson => $composableBuilder(
    column: $table.snapshotJson,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$AnnotationSnapshotsTableTableAnnotationComposer
    extends Composer<_$AppDatabase, $AnnotationSnapshotsTableTable> {
  $$AnnotationSnapshotsTableTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get scriptId =>
      $composableBuilder(column: $table.scriptId, builder: (column) => column);

  GeneratedColumn<DateTime> get timestamp =>
      $composableBuilder(column: $table.timestamp, builder: (column) => column);

  GeneratedColumn<String> get snapshotJson => $composableBuilder(
    column: $table.snapshotJson,
    builder: (column) => column,
  );
}

class $$AnnotationSnapshotsTableTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $AnnotationSnapshotsTableTable,
          AnnotationSnapshotsTableData,
          $$AnnotationSnapshotsTableTableFilterComposer,
          $$AnnotationSnapshotsTableTableOrderingComposer,
          $$AnnotationSnapshotsTableTableAnnotationComposer,
          $$AnnotationSnapshotsTableTableCreateCompanionBuilder,
          $$AnnotationSnapshotsTableTableUpdateCompanionBuilder,
          (
            AnnotationSnapshotsTableData,
            BaseReferences<
              _$AppDatabase,
              $AnnotationSnapshotsTableTable,
              AnnotationSnapshotsTableData
            >,
          ),
          AnnotationSnapshotsTableData,
          PrefetchHooks Function()
        > {
  $$AnnotationSnapshotsTableTableTableManager(
    _$AppDatabase db,
    $AnnotationSnapshotsTableTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$AnnotationSnapshotsTableTableFilterComposer(
                $db: db,
                $table: table,
              ),
          createOrderingComposer: () =>
              $$AnnotationSnapshotsTableTableOrderingComposer(
                $db: db,
                $table: table,
              ),
          createComputedFieldComposer: () =>
              $$AnnotationSnapshotsTableTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<String> scriptId = const Value.absent(),
                Value<DateTime> timestamp = const Value.absent(),
                Value<String> snapshotJson = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => AnnotationSnapshotsTableCompanion(
                id: id,
                scriptId: scriptId,
                timestamp: timestamp,
                snapshotJson: snapshotJson,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                required String scriptId,
                required DateTime timestamp,
                required String snapshotJson,
                Value<int> rowid = const Value.absent(),
              }) => AnnotationSnapshotsTableCompanion.insert(
                id: id,
                scriptId: scriptId,
                timestamp: timestamp,
                snapshotJson: snapshotJson,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$AnnotationSnapshotsTableTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $AnnotationSnapshotsTableTable,
      AnnotationSnapshotsTableData,
      $$AnnotationSnapshotsTableTableFilterComposer,
      $$AnnotationSnapshotsTableTableOrderingComposer,
      $$AnnotationSnapshotsTableTableAnnotationComposer,
      $$AnnotationSnapshotsTableTableCreateCompanionBuilder,
      $$AnnotationSnapshotsTableTableUpdateCompanionBuilder,
      (
        AnnotationSnapshotsTableData,
        BaseReferences<
          _$AppDatabase,
          $AnnotationSnapshotsTableTable,
          AnnotationSnapshotsTableData
        >,
      ),
      AnnotationSnapshotsTableData,
      PrefetchHooks Function()
    >;
typedef $$LineRecordingsTableTableCreateCompanionBuilder =
    LineRecordingsTableCompanion Function({
      required String id,
      required String scriptId,
      required int lineIndex,
      required String filePath,
      required int durationMs,
      required DateTime createdAt,
      Value<int?> grade,
      Value<int> rowid,
    });
typedef $$LineRecordingsTableTableUpdateCompanionBuilder =
    LineRecordingsTableCompanion Function({
      Value<String> id,
      Value<String> scriptId,
      Value<int> lineIndex,
      Value<String> filePath,
      Value<int> durationMs,
      Value<DateTime> createdAt,
      Value<int?> grade,
      Value<int> rowid,
    });

class $$LineRecordingsTableTableFilterComposer
    extends Composer<_$AppDatabase, $LineRecordingsTableTable> {
  $$LineRecordingsTableTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get scriptId => $composableBuilder(
    column: $table.scriptId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get lineIndex => $composableBuilder(
    column: $table.lineIndex,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get filePath => $composableBuilder(
    column: $table.filePath,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get durationMs => $composableBuilder(
    column: $table.durationMs,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get grade => $composableBuilder(
    column: $table.grade,
    builder: (column) => ColumnFilters(column),
  );
}

class $$LineRecordingsTableTableOrderingComposer
    extends Composer<_$AppDatabase, $LineRecordingsTableTable> {
  $$LineRecordingsTableTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get scriptId => $composableBuilder(
    column: $table.scriptId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get lineIndex => $composableBuilder(
    column: $table.lineIndex,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get filePath => $composableBuilder(
    column: $table.filePath,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get durationMs => $composableBuilder(
    column: $table.durationMs,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get grade => $composableBuilder(
    column: $table.grade,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$LineRecordingsTableTableAnnotationComposer
    extends Composer<_$AppDatabase, $LineRecordingsTableTable> {
  $$LineRecordingsTableTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get scriptId =>
      $composableBuilder(column: $table.scriptId, builder: (column) => column);

  GeneratedColumn<int> get lineIndex =>
      $composableBuilder(column: $table.lineIndex, builder: (column) => column);

  GeneratedColumn<String> get filePath =>
      $composableBuilder(column: $table.filePath, builder: (column) => column);

  GeneratedColumn<int> get durationMs => $composableBuilder(
    column: $table.durationMs,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<int> get grade =>
      $composableBuilder(column: $table.grade, builder: (column) => column);
}

class $$LineRecordingsTableTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $LineRecordingsTableTable,
          LineRecordingsTableData,
          $$LineRecordingsTableTableFilterComposer,
          $$LineRecordingsTableTableOrderingComposer,
          $$LineRecordingsTableTableAnnotationComposer,
          $$LineRecordingsTableTableCreateCompanionBuilder,
          $$LineRecordingsTableTableUpdateCompanionBuilder,
          (
            LineRecordingsTableData,
            BaseReferences<
              _$AppDatabase,
              $LineRecordingsTableTable,
              LineRecordingsTableData
            >,
          ),
          LineRecordingsTableData,
          PrefetchHooks Function()
        > {
  $$LineRecordingsTableTableTableManager(
    _$AppDatabase db,
    $LineRecordingsTableTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$LineRecordingsTableTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$LineRecordingsTableTableOrderingComposer(
                $db: db,
                $table: table,
              ),
          createComputedFieldComposer: () =>
              $$LineRecordingsTableTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<String> scriptId = const Value.absent(),
                Value<int> lineIndex = const Value.absent(),
                Value<String> filePath = const Value.absent(),
                Value<int> durationMs = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<int?> grade = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => LineRecordingsTableCompanion(
                id: id,
                scriptId: scriptId,
                lineIndex: lineIndex,
                filePath: filePath,
                durationMs: durationMs,
                createdAt: createdAt,
                grade: grade,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                required String scriptId,
                required int lineIndex,
                required String filePath,
                required int durationMs,
                required DateTime createdAt,
                Value<int?> grade = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => LineRecordingsTableCompanion.insert(
                id: id,
                scriptId: scriptId,
                lineIndex: lineIndex,
                filePath: filePath,
                durationMs: durationMs,
                createdAt: createdAt,
                grade: grade,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$LineRecordingsTableTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $LineRecordingsTableTable,
      LineRecordingsTableData,
      $$LineRecordingsTableTableFilterComposer,
      $$LineRecordingsTableTableOrderingComposer,
      $$LineRecordingsTableTableAnnotationComposer,
      $$LineRecordingsTableTableCreateCompanionBuilder,
      $$LineRecordingsTableTableUpdateCompanionBuilder,
      (
        LineRecordingsTableData,
        BaseReferences<
          _$AppDatabase,
          $LineRecordingsTableTable,
          LineRecordingsTableData
        >,
      ),
      LineRecordingsTableData,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$TextMarksTableTableTableManager get textMarksTable =>
      $$TextMarksTableTableTableManager(_db, _db.textMarksTable);
  $$LineNotesTableTableTableManager get lineNotesTable =>
      $$LineNotesTableTableTableManager(_db, _db.lineNotesTable);
  $$AnnotationSnapshotsTableTableTableManager get annotationSnapshotsTable =>
      $$AnnotationSnapshotsTableTableTableManager(
        _db,
        _db.annotationSnapshotsTable,
      );
  $$LineRecordingsTableTableTableManager get lineRecordingsTable =>
      $$LineRecordingsTableTableTableManager(_db, _db.lineRecordingsTable);
}
