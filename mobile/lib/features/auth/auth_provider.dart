import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../config.dart';
import '../../shared/http_client.dart';
import '../../shared/models.dart';

final authProvider = StateNotifierProvider<AuthController, UserModel?>((ref) => AuthController());

class AuthController extends StateNotifier<UserModel?> {
  AuthController() : super(null);
  final dio = buildClient();

  Future<void> login(String email, String password) async {
    final res = await dio.post('/auth/login', data: {'email': email, 'password': password});
    final token = res.data['access_token'];
    await storage.write(key: 'token', value: token);
    final me = await dio.get('/auth/me');
    state = UserModel.fromJson(me.data);
  }

  Future<void> signup(String email, String password) async {
    final res = await dio.post('/auth/signup', data: {'email': email, 'password': password});
    final token = res.data['access_token'] ?? res.data['token'];
    if (token != null) {
      await storage.write(key: 'token', value: token);
    }
    state = UserModel.fromJson(res.data);
  }

  Future<void> logout() async {
    await storage.delete(key: 'token');
    state = null;
  }
}