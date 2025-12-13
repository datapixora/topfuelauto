import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../shared/models.dart';
import 'broker_provider.dart';

class RequestBidScreen extends ConsumerStatefulWidget {
  final ListingModel listing;
  const RequestBidScreen({super.key, required this.listing});

  @override
  ConsumerState<RequestBidScreen> createState() => _RequestBidScreenState();
}

class _RequestBidScreenState extends ConsumerState<RequestBidScreen> {
  final nameCtrl = TextEditingController();
  final phoneCtrl = TextEditingController();
  final destCtrl = TextEditingController(text: 'USA');
  String? status;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Request broker bid')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Text(widget.listing.title),
            TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Full name')),
            TextField(controller: phoneCtrl, decoration: const InputDecoration(labelText: 'Phone')),
            TextField(controller: destCtrl, decoration: const InputDecoration(labelText: 'Destination country')),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: () async {
                try {
                  await ref.read(brokerProvider).requestBid(
                        listingId: widget.listing.id,
                        destination: destCtrl.text,
                        fullName: nameCtrl.text,
                        phone: phoneCtrl.text,
                      );
                  setState(() => status = 'Sent');
                } catch (e) {
                  setState(() => status = 'Failed (login?)');
                }
              },
              child: const Text('Send'),
            ),
            if (status != null) Text(status!),
          ],
        ),
      ),
    );
  }
}