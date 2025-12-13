import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'vin_provider.dart';

class VinScreen extends ConsumerStatefulWidget {
  const VinScreen({super.key});

  @override
  ConsumerState<VinScreen> createState() => _VinScreenState();
}

class _VinScreenState extends ConsumerState<VinScreen> {
  final vinCtrl = TextEditingController();
  String? status;

  @override
  Widget build(BuildContext context) {
    final result = ref.watch(vinProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('VIN tools')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(controller: vinCtrl, decoration: const InputDecoration(labelText: 'VIN')),
            const SizedBox(height: 12),
            Row(
              children: [
                ElevatedButton(
                  onPressed: () => ref.read(vinProvider.notifier).decode(vinCtrl.text),
                  child: const Text('Decode'),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () async {
                    try {
                      await ref.read(vinProvider.notifier).history(vinCtrl.text);
                    } catch (e) {
                      setState(() => status = 'Pro required');
                    }
                  },
                  child: const Text('History (Pro)'),
                ),
              ],
            ),
            if (status != null) Text(status!),
            const SizedBox(height: 12),
            if (result != null) Text(result.toString()),
          ],
        ),
      ),
    );
  }
}