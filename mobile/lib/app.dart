import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'features/auth/login_screen.dart';
import 'features/auth/signup_screen.dart';
import 'features/search/search_screen.dart';
import 'features/vin/vin_screen.dart';

class TopFuelApp extends StatelessWidget {
  const TopFuelApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const ProviderScope(
      child: MaterialApp(
        title: 'TopFuel Auto',
        debugShowCheckedModeBanner: false,
        home: SearchScreen(),
        routes: {
          '/login': (context) => LoginScreen(),
          '/signup': (context) => SignupScreen(),
          '/vin': (context) => VinScreen(),
        },
      ),
    );
  }
}