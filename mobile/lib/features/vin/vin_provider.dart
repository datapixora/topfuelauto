import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../shared/http_client.dart';

final vinProvider = StateNotifierProvider<VinController, Map<String, dynamic>?>((ref) => VinController());

class VinController extends StateNotifier<Map<String, dynamic>?> {
  VinController() : super(null);
  final dio = buildClient();

  Future<void> decode(String vin) async {
    final res = await dio.get('/vin/decode', queryParameters: {'vin': vin});
    state = res.data;
  }

  Future<void> history(String vin) async {
    final res = await dio.get('/vin/history', queryParameters: {'vin': vin});
    state = res.data;
  }
}