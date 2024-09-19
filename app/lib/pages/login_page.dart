import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:labridge/pages/chat_page.dart';
import 'package:labridge/main.dart';
import 'package:labridge/settings.dart';
import 'package:http/http.dart' as http;

class LoginPage extends StatelessWidget {
  LoginPage({super.key});

  final userNameTextController = TextEditingController();
  final passwordTextController = TextEditingController();

  final logo = Padding(
    padding: const EdgeInsets.only(bottom: 20, top: 0),
    child: SizedBox(
      width: 100,
      child: Image.asset('assets/login_logo.jpg'),
    ),
  );

  // final loginButton = ;
  Decoration? setLoginButtonGradientColor(Set<WidgetState> states) {
    if (states.contains(WidgetState.pressed)) {
      return const BoxDecoration(
        gradient: LinearGradient(
          colors: <Color>[
            Color(0xff1677ff),
            Color(0xff1677ff),
          ],
        ),
      );
    }
    return const BoxDecoration(
      gradient: LinearGradient(
        colors: <Color>[
          Color(0x991677ff),
          Color(0xff1677ff),
        ],
      ),
    );
  }

  Future<bool> loginLabridge(String userName, String password) async {
    var url = Uri.parse('$baseUrl/accounts/log-in');
    var response = await http.post(url,
        body: json.encode({"user_id": userName, "password": password}),
        headers: {'Content-Type': "application/json; charset=utf-8"});
    try {
      if (response.statusCode == 200 &&
          json.decode(response.body)['user_id'] != null) {
        return true;
      } else {
        return false;
      }
    } on Exception {
      return false;
    }
  }

  Future<bool> registerLabridge(String userName, String password) async {
    var url = Uri.parse('$baseUrl/accounts/sign-up');
    var response = await http.post(url,
        body: json.encode({"user_id": userName, "password": password}),
        headers: {'Content-Type': "application/json; charset=utf-8"});
    if (response.statusCode == 200 && json.decode(response.body) != null) {
      return true;
    } else {
      return false;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          // padding: const EdgeInsets.symmetric(horizontal: 50),
          children: [
            logo,
            Padding(
              padding: const EdgeInsets.only(bottom: 20),
              child: SizedBox(
                width: 300,
                // height: 100,
                child: TextField(
                  controller: userNameTextController,
                  keyboardType: TextInputType.text,
                  decoration: const InputDecoration(
                      hintText: 'User Name',
                      contentPadding:
                          EdgeInsets.symmetric(horizontal: 25, vertical: 20),
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.all(Radius.circular(10)))),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(bottom: 20),
              child: SizedBox(
                width: 300,
                // height: 100,
                child: TextField(
                  controller: passwordTextController,
                  keyboardType: TextInputType.text,
                  decoration: const InputDecoration(
                      hintText: 'Password',
                      contentPadding:
                          EdgeInsets.symmetric(horizontal: 25, vertical: 20),
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.all(Radius.circular(10)))),
                ),
              ),
            ),
            // Expanded(child: Container()),
            // Container(height: double.infinity,),
            SizedBox(
              width: 300,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(bottom: 5),
                    child: SizedBox(
                      height: 50,
                      width: 140,
                      child: TextButton(
                        style: TextButton.styleFrom(
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(18),
                              side: BorderSide(
                                  color: Theme.of(context).primaryColor,
                                  width: 1.5)),
                          // backgroundColor: Theme.of(context).secondaryHeaderColor,
                          // foregroundColor: Colors.black,
                        ),
                        onPressed: () async {
                          var loginStatus = await registerLabridge(
                              userNameTextController.text,
                              passwordTextController.text);
                          if (loginStatus == true) {
                            settings.userName = userNameTextController.text;
                            settings.password = passwordTextController.text;
                            if (context.mounted) {
                              Navigator.pushReplacement(
                                context,
                                MaterialPageRoute(
                                    builder: (context) => ChatPage(
                                          userName: userNameTextController.text,
                                        )),
                              );
                            }
                          } else {
                            ///TODO" show message
                          }
                        },
                        child: const Text(
                          'Register',
                          style: TextStyle(
                              fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(bottom: 5),
                    child: SizedBox(
                      height: 50,
                      width: 140,
                      child: TextButton(
                        style: TextButton.styleFrom(
                          backgroundBuilder: (BuildContext context,
                              Set<WidgetState> states, Widget? child) {
                            return AnimatedContainer(
                              duration: const Duration(milliseconds: 500),
                              decoration: setLoginButtonGradientColor(states),
                              child: child,
                            );
                          },
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(18),
                          ),
                          // backgroundColor: Color(0xdd1677ff),
                          foregroundColor: Colors.white,
                        ),
                        onPressed: () async {
                          var loginStatus = await loginLabridge(
                              userNameTextController.text,
                              passwordTextController.text);
                          if (loginStatus == true) {
                            settings.userName = userNameTextController.text;
                            settings.password = passwordTextController.text;
                            if (context.mounted) {
                              Navigator.pushReplacement(
                                context,
                                MaterialPageRoute(
                                    builder: (context) => ChatPage(
                                          userName: userNameTextController.text,
                                        )),
                              );
                            }
                          } else {
                            ///TODO" show message
                          }
                        },
                        child: const Text(
                          'Login',
                          style: TextStyle(
                              fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(
              height: 45,
            )
          ],
        ),
      ),
    );
  }
}
