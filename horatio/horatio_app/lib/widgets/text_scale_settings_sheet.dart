import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_state.dart';

/// A bottom sheet with a slider for adjusting text scale factor.
class TextScaleSettingsSheet extends StatelessWidget {
  /// Creates a [TextScaleSettingsSheet].
  const TextScaleSettingsSheet({super.key});

  @override
  Widget build(BuildContext context) =>
      BlocBuilder<TextScaleCubit, TextScaleState>(
        builder: (context, state) => Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Text Size',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 16),
              Text(
                'Sample text at ${state.scaleFactor.toStringAsFixed(1)}x',
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 8),
              Slider(
                value: state.scaleFactor,
                min: 0.5,
                max: 3,
                divisions: 25,
                label: '${state.scaleFactor.toStringAsFixed(1)}x',
                onChanged: (value) =>
                    context.read<TextScaleCubit>().setScale(value),
              ),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () =>
                      context.read<TextScaleCubit>().resetToAuto(),
                  child: const Text('Reset to auto'),
                ),
              ),
            ],
          ),
        ),
      );
}
