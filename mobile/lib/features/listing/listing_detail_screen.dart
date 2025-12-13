import 'package:flutter/material.dart';
import '../../shared/models.dart';
import '../broker/request_bid_screen.dart';

class ListingDetailScreen extends StatelessWidget {
  final ListingModel listing;
  const ListingDetailScreen({super.key, required this.listing});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(listing.title)),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${listing.vehicle.year} ${listing.vehicle.make} ${listing.vehicle.model}', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(listing.location ?? ''),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => RequestBidScreen(listing: listing),
                ),
              ),
              child: const Text('Request bid'),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => Navigator.pushNamed(context, '/vin'),
              child: const Text('Open VIN tools'),
            )
          ],
        ),
      ),
    );
  }
}