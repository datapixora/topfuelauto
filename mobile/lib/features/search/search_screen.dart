import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'search_provider.dart';
import 'listing_card.dart';

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final queryCtrl = TextEditingController(text: 'Nissan GT-R 2005');

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(searchProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('TopFuel Auto')),
      body: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: queryCtrl,
                    decoration: const InputDecoration(labelText: 'Search make/model'),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.search),
                  onPressed: () => ref.read(searchProvider.notifier).search(queryCtrl.text),
                )
              ],
            ),
            const SizedBox(height: 8),
            Expanded(
              child: ListView.builder(
                itemCount: results.length,
                itemBuilder: (context, idx) => ListingCard(listing: results[idx]),
              ),
            )
          ],
        ),
      ),
    );
  }
}