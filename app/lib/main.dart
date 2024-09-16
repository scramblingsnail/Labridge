import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:labridge/pages/login_page.dart';
import 'package:labridge/pages/chat_page.dart';
import 'package:labridge/settings.dart';
import 'package:google_fonts/google_fonts.dart';

// For the testing purposes, you should probably use https://pub.dev/packages/uuid.

final settings = Settings();

void main() async {

  runApp(const MyApp());
  if (Platform.isAndroid) {
    SystemUiOverlayStyle systemUiOverlayStyle = const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      systemNavigationBarColor: Color(0xff1d1c21), // navigation bar color
      statusBarIconBrightness: Brightness.dark, // status bar icons' color
      systemNavigationBarIconBrightness: Brightness.dark, //naviga
    );
    SystemChrome.setSystemUIOverlayStyle(systemUiOverlayStyle);
  }
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        home: MyHomePage(),
        theme: ThemeData(textTheme: GoogleFonts.notoSansScTextTheme()),
        debugShowCheckedModeBanner: false,
      );
}

class MyHomePage extends StatelessWidget {
  MyHomePage({super.key});

  final Future<String?> _getUserName = settings.userNameInPrefs;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<String?>(
        future: _getUserName,
        builder: (BuildContext context, AsyncSnapshot<String?> snapshot) {
          if (!snapshot.hasError) {
            if (snapshot.data != null) {
              return  ChatPage(userName: snapshot.data!,);
            } else {
              return LoginPage();
            }
          } else {
            return const Center(child: Text('Error'),);
          }
        });
  }
}
