import 'package:equatable/equatable.dart';

/// State for [TextScaleCubit].
final class TextScaleState extends Equatable {
  /// Creates a [TextScaleState].
  const TextScaleState({required this.scaleFactor});

  /// The text scale multiplier (0.5 – 3.0).
  final double scaleFactor;

  @override
  List<Object?> get props => [scaleFactor];
}
