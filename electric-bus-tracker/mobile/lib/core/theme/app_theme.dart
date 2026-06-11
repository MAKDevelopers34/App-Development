import 'package:flutter/material.dart';

class AppTheme {
  static const Color primaryGreen = Color(0xFF00A63E);
  static const Color darkGreen = Color(0xFF008236);
  static const Color lightGreen = Color(0xFFE8F8F0);
  static const Color white = Color(0xFFFFFFFF);
  static const Color bgGrey = Color(0xFFF5F5F5);
  static const Color textDark = Color(0xFF1A1A1A);
  static const Color textGrey = Color(0xFF8A8A8A);
  static const Color redStatus = Color(0xFFE7000B);
  static const Color orangeStatus = Color(0xFFF0B100);
  static const Color cardShadow = Color(0x1A000000);

  static ThemeData get lightTheme => ThemeData(
    primaryColor: primaryGreen,
    scaffoldBackgroundColor: white,
    fontFamily: 'Poppins',
    colorScheme: const ColorScheme.light(
      primary: primaryGreen,
      secondary: darkGreen,
      surface: white,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: white,
      elevation: 0,
      iconTheme: IconThemeData(color: textDark),
      titleTextStyle: TextStyle(
        color: textDark,
        fontSize: 18,
        fontWeight: FontWeight.w600,
        fontFamily: 'Poppins',
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: primaryGreen,
        foregroundColor: white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 24),
        textStyle: const TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w600,
          fontFamily: 'Poppins',
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: bgGrey,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide.none,
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: primaryGreen, width: 1.5),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      color: white,
    ),
  );
}
