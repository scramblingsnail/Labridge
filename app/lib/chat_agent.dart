import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:labridge/settings.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'package:http_parser/http_parser.dart';

class ChatAgent {
  final String userId;
  final String chatTextUrl;
  final String getResponseUrl;
  final String innerChatTextUrl;
  final String clearHistoryUrl;
  final String chatSpeechUrl;
  final String innerChatSpeechUrl;
  final String downFileUrl;
  final String chatFileUrl;
  final String innerChatFileUrl;
  final http.Client client;

  ChatAgent(this.userId)
      : chatTextUrl = '$baseUrl/users/$userId/chat_text',
        getResponseUrl = '$baseUrl/users/$userId/response',
        innerChatTextUrl = '$baseUrl/users/$userId/inner_chat_text',
        clearHistoryUrl = '$baseUrl/users/$userId/clear_history',
        chatSpeechUrl = '$baseUrl/users/$userId/chat_speech',
        innerChatSpeechUrl = '$baseUrl/users/$userId/inner_chat_speech',
        downFileUrl = '$baseUrl/users/$userId/files/bytes',
        chatFileUrl = '$baseUrl/users/$userId/chat_with_file',
        innerChatFileUrl = '$baseUrl/users/$userId/inner_chat_with_file',
        client = http.Client();

  void chatWithText(
    String message, {
    required bool isInnerChat,
    bool replyInSpeech = false,
    bool enableInstruct = false,
    bool enableComment = false,
  }) async {
    final url = isInnerChat ? innerChatTextUrl : chatTextUrl;
    client.post(Uri.parse(url),
        headers: {"Content-Type": "application/json"},
        body: json.encode({
          'text': message,
          'reply_in_speech': replyInSpeech,
          'enable_instruct': enableInstruct,
          'enable_comment': enableComment,
        }),
        encoding: Encoding.getByName('utf-8'));
  }

  /// Query about some info with uploaded file. If you want query with audio, you should use [chatWithAudio]
  Future<int> chatWithFile(
    Uint8List fileBytes,
    String fileName,
    String message, {
    required bool isInnerChat,
    bool replyInSpeech = false,
    bool enableInstruct = false,
    bool enableComment = false,
  }) async {
    final url = isInnerChat ? innerChatFileUrl : chatFileUrl;
    var request = http.MultipartRequest('POST', Uri.parse(url))
      ..fields['file_name'] = fileName
      ..fields['text'] = message
      ..fields['reply_in_speech'] = json.encode(replyInSpeech)
      ..fields['enable_instruct'] = json.encode(enableInstruct)
      ..fields['enable_comment'] = json.encode(enableComment)
      ..files.add(http.MultipartFile.fromBytes(
        'file',
        fileBytes,
        filename: fileName,
        contentType: MediaType('multipart', 'form-data'),
      ));
    var response = await request.send();

    /// Response denotes uploading status
    return response.statusCode;
  }

  Future<int> chatWithAudio(
    Uint8List fileBytes,
    String fileName, {
    required bool isInnerChat,
    required bool replyInSpeech,
    required bool enableInstruct,
    required bool enableComment,
  }) async {
    final url = isInnerChat ? innerChatSpeechUrl : chatSpeechUrl;
    var request = http.MultipartRequest('POST', Uri.parse(url))
      // ..fields['file_name'] = fileName
      // ..fields['text'] = message
      ..fields['file_suffix'] = '.wav'
      ..fields['reply_in_speech'] = json.encode(replyInSpeech)
      ..fields['enable_instruct'] = json.encode(enableInstruct)
      ..fields['enable_comment'] = json.encode(enableComment)
      ..files.add(http.MultipartFile.fromBytes(
        'file',
        fileBytes,
        filename: fileName,
        contentType: MediaType('multipart', 'form-data'),
      ));
    var response = await request.send();

    return response.statusCode;
    // if (response.statusCode == 200) print('Uploaded!');
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
        // print(getResponseUrl);
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

  Future<String> downloadFile(String remoteFilePath, {String? localFileName}) async {
    // final streamResponse = await client
    //     .post(Uri.parse(downFileUrl), body: {'filepath': remoteFilePath});
    // final response = await http.Response.fromStream(response)

    final request = http.Request('POST', Uri.parse(downFileUrl))
      ..body = json.encode({'filepath': remoteFilePath})
      ..headers.addAll({'Content-Type': "application/json; charset=utf-8"});

    var response = await client.send(request);

    // var reader = ChunkedStreamReader(
    //     response.stream);
    final documentDir = (await getTemporaryDirectory()).path;

    if (localFileName == null) {
      remoteFilePath = remoteFilePath.replaceAll('\\', '/');
      localFileName = p.basename(remoteFilePath);
    }

    final localFilePath = '$documentDir/$localFileName';
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
