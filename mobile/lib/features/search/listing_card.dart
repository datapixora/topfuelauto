import 'package:flutter/material.dart';
import '../../shared/models.dart';
import '../listing/listing_detail_screen.dart';

class ListingCard extends StatelessWidget {
  final ListingModel listing;
  const ListingCard({super.key, required this.listing});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        title: Text(listing.title),
        subtitle: Text('${listing.vehicle.year} ${listing.vehicle.make} ${listing.vehicle.model}'),
        trailing: Text(listing.price != null ? '${listing.currency ?? 'USD'} ${listing.price}' : 'Ask'),
        onTap: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => ListingDetailScreen(listing: listing)),
        ),
      ),
    );
  }
}