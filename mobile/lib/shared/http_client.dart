import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config.dart';

final storage = FlutterSecureStorage();

Dio buildClient() {
  final dio = Dio(BaseOptions(baseUrl: AppConfig.apiBase));
  dio.interceptors.add(
    InterceptorsWrapper(onRequest: (options, handler) async {
      final token = await storage.read(key: 'token');
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      return handler.next(options);
    }),
  );
  return dio;
}