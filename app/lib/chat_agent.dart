import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:async/async.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

// const baseUrl = "http://210.28.142.241:6006";
const baseUrl = "http://210.28.141.187:80";

class ChatAgent {
  final String userId;
  final String postTextUrl;
  final String getResponseUrl;
  final String postToolInfoUrl;
  final String clearHistoryUrl;
  final String postSpeechUrl;
  final String downFileUrl;
  final String postFileUrl;
  final http.Client client;

  ChatAgent(this.userId)
      : postTextUrl = '$baseUrl/users/$userId/chat_text',
        getResponseUrl = '$baseUrl/users/$userId/response',
        postToolInfoUrl = '$baseUrl/users/$userId/inner_chat_text',
        clearHistoryUrl = '$baseUrl/users/$userId/clear_history',
        postSpeechUrl = '$baseUrl/users/$userId/chat_speech',
        downFileUrl = '$baseUrl/users/$userId/files/bytes',
        postFileUrl = '$baseUrl/users/$userId/chat_with_file',
        client = http.Client();

  void query(
    String message, {
    bool replyInSpeech = false,
    bool enableInstruct = false,
    bool enableComment = false,
  }) async {
    client.post(Uri.parse(postTextUrl),
        headers: {"Content-Type": "application/json"},
        body: json.encode({
          'text': message,
          'reply_in_speech': replyInSpeech,
          'enable_instruct': enableInstruct,
          'enable_comment': enableComment,
        }),
        encoding: Encoding.getByName('utf-8'));
  }

  void queryInSpeech(List data) async {}

  Future<int> queryInFile(
    Uint8List fileBytes,
    String fileName,
    String message,
    bool replyInSpeech, {
    bool enableInstruct = false,
    bool enableComment = false,
  }) async {
    var request = http.MultipartRequest('POST', Uri.parse(postFileUrl))
      ..fields['file_name'] = fileName
      ..fields['text'] = message
      ..fields['reply_in_speech'] = json.encode(replyInSpeech)
      ..fields['enable_instruct'] = json.encode(enableInstruct)
      ..fields['enable_comment'] = json.encode(enableComment)
      ..files.add(http.MultipartFile.fromBytes('file', fileBytes));
    var response = await request.send();

    return response.statusCode;
    // if (response.statusCode == 200) print('Uploaded!');
  }

  Future<Map<String, dynamic>> queryAndAnswer(String message) async {
    await client.post(Uri.parse(postToolInfoUrl),
        body: json.encode({'text': message}));
    return singleGetResponse();
  }

  void clearHistory() async {
    client.post(Uri.parse(clearHistoryUrl),
        headers: {"Content-Type": "application/json"},
        // body: json.encode({'text': message}),
        encoding: Encoding.getByName('utf-8'));
  }

  Future<Map<String, dynamic>> singleGetResponse() async {
    while (true) {
      var reply = await client.get(Uri.parse(getResponseUrl),
          headers: {'Content-Type': "application/json; charset=utf-8"});

      if (reply.body.isNotEmpty) {
        /// Server no utf-8 header set, we should re-decode
        final replyMap =
            json.decode(utf8.decode(reply.bodyBytes)) as Map<String, dynamic>;
        if (replyMap.containsKey('valid') && replyMap['valid'] as bool) {
          return replyMap;
        }
      }
      await Future.delayed(
        const Duration(seconds: 1),
      );
    }
  }

  Future<String> downloadFile(String remoteFilePath) async {
    // final streamResponse = await client
    //     .post(Uri.parse(downFileUrl), body: {'filepath': remoteFilePath});
    // final response = await http.Response.fromStream(response)

    final request = http.Request('POST', Uri.parse(downFileUrl))
      ..body = json.encode({'filepath': remoteFilePath})
      ..headers.addAll({'Content-Type': "application/json; charset=utf-8"});

    var response = await client.send(request);

    // var reader = ChunkedStreamReader(
    //     response.stream);
    final documentDir = (await getDownloadsDirectory())?.path;
    // print(body)
    final localFilePath = '$documentDir/${p.basename(remoteFilePath)}';
    if (!File(localFilePath).existsSync()) {
      final file = File(localFilePath);
      var sink = file.openWrite();
      await response.stream.pipe(sink);
      sink.close();
    }
    return localFilePath;
    // return response.bodyBytes;
  }
}
