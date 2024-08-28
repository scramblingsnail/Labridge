import 'dart:convert';

import 'package:http/http.dart' as http;

// const baseUrl = "http://210.28.142.241:6006";
const baseUrl = "http://210.28.141.187:80";

class ChatAgent {
  final String userId;
  final String postTextUrl;
  final String getResponseUrl;
  final String postToolInfoUrl;
  final http.Client client;

  ChatAgent(this.userId)
      : postTextUrl = '$baseUrl/users/$userId/chat_text',
        getResponseUrl = '$baseUrl/users/$userId/response',
        postToolInfoUrl = '$baseUrl/users/$userId/inner_chat_text',
        client = http.Client();

  void query(String message) async {
    client.post(Uri.parse(postTextUrl),
        headers: {"Content-Type": "application/json"},
        body: json.encode({'text': message}),
        encoding: Encoding.getByName('utf-8'));
  }

  Future<Map<String, dynamic>> queryAndAnswer(String message) async {
    await client.post(Uri.parse(postToolInfoUrl),
        body: json.encode({'text': message}));
    return singleGetResponse();
  }

  Future<Map<String, dynamic>> singleGetResponse() async {
    while (true) {
      var reply = await client.get(Uri.parse(getResponseUrl), headers: {'Content-Type' : "application/json; charset=utf-8"});

      if (reply.body.isNotEmpty) {
        /// Server no utf-8 header set, we should re-decode
        final replyMap = json.decode(utf8.decode(reply.bodyBytes)) as Map<String, dynamic>;
        if (replyMap.containsKey('valid') && replyMap['valid'] as bool) {
          return replyMap;
        }
      }
      await Future.delayed(
        const Duration(seconds: 1),
      );
    }
  }
}
