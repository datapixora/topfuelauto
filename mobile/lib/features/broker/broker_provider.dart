import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../shared/http_client.dart';

final brokerProvider = Provider<BrokerApi>((ref) => BrokerApi());

class BrokerApi {
  final dio = buildClient();

  Future<void> requestBid({required int listingId, required String destination, required String fullName, required String phone}) async {
    await dio.post('/broker/request-bid', data: {
      'listing_id': listingId,
      'destination_country': destination,
      'full_name': fullName,
      'phone': phone,
    });
  }
}