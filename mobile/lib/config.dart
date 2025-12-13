class AppConfig {
  static const apiBase = String.fromEnvironment('API_BASE', defaultValue: 'http://localhost:8000/api/v1');
}