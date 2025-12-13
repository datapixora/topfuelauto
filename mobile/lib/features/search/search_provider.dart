import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../shared/http_client.dart';
import '../../shared/models.dart';

final searchProvider = StateNotifierProvider<SearchController, List<ListingModel>>((ref) => SearchController());

class SearchController extends StateNotifier<List<ListingModel>> {
  SearchController() : super([]);
  final dio = buildClient();

  Future<void> search(String query) async {
    final res = await dio.get('/search', queryParameters: {'q': query});
    final data = res.data as List;
    state = data.map((e) => ListingModel.fromJson(e)).toList();
  }
}