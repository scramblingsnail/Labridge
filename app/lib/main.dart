import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_chat_types/flutter_chat_types.dart' as types;
import 'package:flutter_chat_ui/flutter_chat_ui.dart';
import 'package:image_picker/image_picker.dart';
import 'package:labridge/chat_agent.dart';
import 'package:open_filex/open_filex.dart';
import 'package:uuid/uuid.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:path/path.dart' as p;

// For the testing purposes, you should probably use https://pub.dev/packages/uuid.
String randomString() {
  const uuid = Uuid();
  return uuid.v8();
}

const String labridgeName = 'Labridge';
const uuid = Uuid();
final _labridgeId = uuid.v5(Uuid.NAMESPACE_URL, 'Labridge');
final _labridge = types.User(id: _labridgeId, firstName: 'Labridge');

void main() {
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
        home: const MyHomePage(),
        theme: ThemeData(textTheme: GoogleFonts.notoSansScTextTheme()),
        debugShowCheckedModeBanner: false,
      );
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key});

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  final List<types.Message> _messages = [];

  final chatAgent = ChatAgent('杨再正');

  bool _shouldEnterInnerChat = false;

  // bool _clearButtonVisible = false;
  double _clearButtonWidth = 0.0;
  Color _textColor = Colors.transparent;

  int _waitForUploadingContentsCount = 0;
  PlatformFile? waitForUploadingFile;
  Uint8List? waitForUploadingFileBytes;
  types.FileMessage? fileMessage;

  /// Create Agent

  final _user = const types.User(
      id: '82091008-a484-4a89-ae75-a22bf8d6f3ac',
      firstName: 'Yichen',
      lastName: 'Zhao');

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          elevation: 0,
          backgroundColor: Colors.grey[100],
          centerTitle: true,
          title: const Text(
            'Labridge',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          actions: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              width: _clearButtonWidth,
              height: 30,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                child: TextButton(
                  onPressed: _clearButtonWidth != 0.0
                      ? () {
                          setState(() {
                            _messages.clear();
                            _textColor = Colors.transparent;
                            _clearButtonWidth = 0.0;
                          });
                          chatAgent.clearHistory();
                        }
                      : null,
                  style: TextButton.styleFrom(
                      backgroundColor: Colors.blueAccent,
                      side: BorderSide.none,
                      padding: const EdgeInsets.all(0)),
                  child: Align(
                    alignment: Alignment.center,
                    child: Text(
                      '清空',
                      style: TextStyle(
                          color: _textColor,
                          fontWeight: FontWeight.w400,
                          fontSize: 14),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
              ),
              onEnd: () {
                setState(() {
                  _textColor = Colors.white;
                });
              },
            ),
          ],
          // titleTextStyle: const TextStyle(color: Colors.white),
        ),
        // extendBodyBehindAppBar: true,
        body: Chat(
          messages: _messages,
          onAttachmentPressed: _handleAttachmentPressed,
          onMessageTap: _handleMessageTap,
          onPreviewDataFetched: _handlePreviewDataFetched,
          onSendPressed: _handleSendPressed,
          usePreviewData: false,
          showUserNames: true,
          user: _user,
          theme: DefaultChatTheme(
              attachmentButtonIcon: _waitForUploadingContentsCount == 0
                  ? const Icon(
                      Icons.attach_file_rounded,
                      color: Colors.white,
                    )
                  : Badge.count(
                      count: 1,
                      backgroundColor: Colors.blue,
                      child: const Icon(
                        Icons.attach_file_rounded,
                        color: Colors.white,
                      ),
                    )),
        ),
      );

  void _addMessage(types.Message message) {
    setState(() {
      _messages.insert(0, message);
    });
  }

  void _handleAttachmentPressed() {
    showModalBottomSheet<void>(
      context: context,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(16))),
      builder: (BuildContext context) => SafeArea(
        child: SizedBox(
          height: 144,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              TextButton(
                style: TextButton.styleFrom(
                    shape: const RoundedRectangleBorder(
                        borderRadius: BorderRadius.all(Radius.circular(16)))),
                onPressed: () {
                  Navigator.pop(context);
                  _handleImageSelection();
                },
                child: const Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Text('Photo'),
                ),
              ),
              TextButton(
                onPressed: () {
                  Navigator.pop(context);
                  _handleFileSelection();
                },
                child: const Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Text('File'),
                ),
              ),
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Text('Cancel'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _handleFileSelection() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.any,
    );

    if (result != null && result.files.single.path != null) {
      fileMessage = types.FileMessage(
        author: _user,
        createdAt: DateTime.now().millisecondsSinceEpoch,
        id: randomString(),
        name: result.files.single.name,
        size: result.files.single.size,
        uri: result.files.single.path!,
      );
      // result.files.single.bytes
      waitForUploadingFileBytes =
          await File(result.files.single.path!).readAsBytes();

      waitForUploadingFile = result.files.single;
      setState(() {
        _waitForUploadingContentsCount = 1;
      });

      // _addMessage(message);
    }
  }

  void _handleImageSelection() async {
    final result = await ImagePicker().pickImage(
      imageQuality: 70,
      maxWidth: 1440,
      source: ImageSource.gallery,
    );

    if (result != null) {
      final bytes = await result.readAsBytes();
      final image = await decodeImageFromList(bytes);

      final message = types.ImageMessage(
        author: _user,
        createdAt: DateTime.now().millisecondsSinceEpoch,
        height: image.height.toDouble(),
        id: randomString(),
        name: result.name,
        size: bytes.length,
        uri: result.path,
        width: image.width.toDouble(),
      );

      _addMessage(message);
    }
  }

  void _handleMessageTap(BuildContext _, types.Message message) async {
    if (message is types.FileMessage) {
      var localPath = message.uri;
      if (message.uri.startsWith('remote:')) {
        try {
          final index =
              _messages.indexWhere((element) => element.id == message.id);
          final updatedMessage =
              (_messages[index] as types.FileMessage).copyWith(
            isLoading: true,
          );

          setState(() {
            _messages[index] = updatedMessage;
          });

          /// remove tag
          localPath = await chatAgent.downloadFile(localPath.substring(7));
        } finally {
          final index =
              _messages.indexWhere((element) => element.id == message.id);
          final updatedMessage =
              (_messages[index] as types.FileMessage).copyWith(
            isLoading: null,
          );

          setState(() {
            _messages[index] = updatedMessage;
          });
        }
      }

      await OpenFilex.open(localPath);
    } else if (message is types.AudioMessage) {
      final player = AudioPlayer();
      await player.play(DeviceFileSource(message.uri));
    }
  }

  /// 预览功能的回调函数
  void _handlePreviewDataFetched(
    types.TextMessage message,
    types.PreviewData previewData,
  ) {
    final index = _messages.indexWhere((element) => element.id == message.id);
    final updatedMessage = (_messages[index] as types.TextMessage).copyWith(
      previewData: previewData,
    );

    setState(() {
      _messages[index] = updatedMessage;
    });
  }

  void _handleSendPressed(types.PartialText message) async {
    /// TODO: performance
    setState(() {
      _clearButtonWidth = 90.0;
    });

    final textMessage = types.TextMessage(
      author: _user,
      createdAt: DateTime.now().millisecondsSinceEpoch,
      id: randomString(),
      text: message.text,
    );

    _addMessage(textMessage);
    Map<String, dynamic> response;

    /// 发送消息并等待响应
    if (!_shouldEnterInnerChat) {
      if (_waitForUploadingContentsCount == 0) {
        chatAgent.query(message.text, replyInSpeech: true);
        response = await chatAgent.singleGetResponse();
      } else {
        _addMessage(fileMessage!);
        setState(() {
          _waitForUploadingContentsCount = 0;
        });
        chatAgent.queryInFile(waitForUploadingFileBytes!,
            waitForUploadingFile!.name, message.text, false);
        response = await chatAgent.singleGetResponse();
      }
    } else {
      response = await chatAgent.queryAndAnswer(message.text);
    }

    _shouldEnterInnerChat = response['inner_chat'];

    /// update message
    if (response.containsKey('reply_text')) {
      final labridgeTextMessage = types.TextMessage(
        author: _labridge,
        createdAt: DateTime.now().millisecondsSinceEpoch,
        id: randomString(),
        text: response['reply_text'].toString().trim(),
      );
      _addMessage(labridgeTextMessage);
    } else {
      final replySpeechPaths =
          Map<String, int>.from(response['reply_speech_path']);

      for (final speechPathEntry in replySpeechPaths.entries) {
        var localPath = await chatAgent.downloadFile(speechPathEntry.key);
        final labridgeAudioMessage = types.AudioMessage(
          author: _labridge,
          createdAt: DateTime.now().millisecondsSinceEpoch,
          id: randomString(),
          name: p.basename(speechPathEntry.key),
          size: speechPathEntry.value,
          uri: localPath,
          duration: const Duration(seconds: 4),
        );
        _addMessage(labridgeAudioMessage);
      }
    }

    if (response['references'] != null) {
      // print('object');

      final references = Map<String, int>.from(response['references']);
      // print(references.keys);
      for (final referEntry in references.entries) {
        final fileMessage = types.FileMessage(
          author: _labridge,
          id: randomString(),
          name: p.basename(referEntry.key),
          size: referEntry.value,
          uri: 'remote:${referEntry.key}',
        );

        _addMessage(fileMessage);
      }
    }
  }
}
