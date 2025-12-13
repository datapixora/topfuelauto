import 'package:flutter/material.dart';

class FiltersWidget extends StatelessWidget {
  final void Function(String) onChanged;
  const FiltersWidget({super.key, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          children: [
            const Text('Filters'),
            TextField(
              decoration: const InputDecoration(labelText: 'Location'),
              onChanged: onChanged,
            ),
          ],
        ),
      ),
    );
  }
}