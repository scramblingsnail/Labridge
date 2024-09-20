import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_chat_types/flutter_chat_types.dart' as types;
import 'package:flutter_chat_ui/flutter_chat_ui.dart';
import 'package:image_picker/image_picker.dart';
import 'package:labridge/chat_agent.dart';
import 'package:labridge/chat_states.dart';
import 'package:labridge/message/message_input.dart';
import 'package:labridge/pages/login_page.dart';
import 'package:labridge/pdf_viewer_route.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';
import 'package:record/record.dart';
import 'package:uuid/uuid.dart';
import 'package:path/path.dart' as p;
import 'package:labridge/message/audio_message.dart';
import 'package:labridge/pages/settings_page.dart';

import '../main.dart';

class ChatPage extends StatefulWidget {
  const ChatPage({super.key, required this.userName});

  /// userName determines server URL.
  /// It should be a registered name in server.
  final String userName;

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  /// chat messages list
  final List<types.Message> _messages = [];

  /// audio player instance
  final player = AudioPlayer();
  final recorder = AudioRecorder();

  /// unique id
  final uuid = const Uuid();

  late final _labridgeId = uuid.v5(Uuid.NAMESPACE_URL, 'Labridge');
  late final _labridge = types.User(id: _labridgeId, firstName: 'Labridge');

  late final ChatAgent chatAgent = ChatAgent(widget.userName);
  late final types.User _user = types.User(
      id: '82091008-a484-4a89-ae75-a22bf8d6f3ac', firstName: widget.userName);

  late final String audioFileStorageDirectory;

  /// denote current chat status defined in our LLM server
  bool _isInnerChat = false;

  double _clearButtonWidth = 0.0;

  /// can be [Colors.transparent] or [Colors.white]
  /// When message length > 1, [_clearButtonTextColor] is set [Colors.white]
  Color _clearButtonTextColor = Colors.transparent;

  // int _waitForUploadingContentsCount = 0;

  /// [waitForUploadingFile] is a file instance storing file which will be uploaded to server
  PlatformFile? waitForUploadingFile;

  /// stores bytes of file
  Uint8List? waitForUploadingFileBytes;

  /// Message instance in chat
  types.FileMessage? fileMessage;

  String? audioFileName;

  final OverlayEntry overlayEntry =
      OverlayEntry(builder: (BuildContext context) {
    return Center(
        child: Opacity(
            opacity: 0.5,
            child: Container(
              decoration: BoxDecoration(
                  color: Colors.grey, borderRadius: BorderRadius.circular(8)),
              width: 100,
              height: 100,
              child: const Column(
                children: [
                  Icon(
                    Icons.keyboard_voice,
                    size: 80,
                  ),
                  Text(
                    '录音中',
                    style: TextStyle(
                        fontSize: 12,
                        decoration: TextDecoration.none,
                        color: Colors.white70),
                  )
                ],
              ),
            )));
  });

  /// [randomUniqueId] can generate unique id for each message
  String randomUniqueId() {
    return uuid.v8();
  }

  @override
  void dispose() {
    overlayEntry.remove();
    overlayEntry.dispose();

    /// ensure audio recorder has been disposed
    recorder.dispose();

    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    getTemporaryDirectory().then((Directory directory) {
      audioFileStorageDirectory = directory.path;
    });
    recorder.hasPermission();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        // elevation: 0.2,
        backgroundColor: Colors.grey[100],
        // 防止滚动时变色
        scrolledUnderElevation: 0.0,
        centerTitle: true,
        title: const Text(
          'Labridge',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        shape: Border(
            bottom: BorderSide(
          color: Colors.grey[200]!,
          width: 0.5,
        )),
        actions: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            width: _clearButtonWidth,
            height: 30,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: TextButton(
                onPressed: _clearButtonWidth != 0.0
                    ? () async {
                        setState(() {
                          _messages.clear();

                          _clearButtonTextColor = Colors.transparent;
                          _clearButtonWidth = 0.0;
                        });
                        player.release();
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
                        color: _clearButtonTextColor,
                        fontWeight: FontWeight.w400,
                        fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ),
            onEnd: () {
              setState(() {
                _clearButtonTextColor = Colors.white;
              });
            },
          ),
        ],
        // titleTextStyle: const TextStyle(color: Colors.white),
      ),
      drawer: Drawer(
        // width: 200,
        child: Column(
          children: [
            Column(
              // padding: EdgeInsets.zero,
              children: [
                const SizedBox(
                  height: 100,
                  child: DrawerHeader(
                    decoration: BoxDecoration(
                      color: Color(0xff1d1c21),
                    ),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        'Labridge',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                ),
                ListTile(
                  title: const Text('设置'),
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (context) => const SettingsPage()),
                    );
                  },
                )
              ],
            ),
            Expanded(child: Container()),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 20),
              child: SizedBox(
                width: double.infinity,
                child: TextButton(
                  style: TextButton.styleFrom(
                    backgroundColor:
                        Theme.of(context).colorScheme.primaryContainer,
                  ),
                  onPressed: () {
                    settings.clearUserInfo();
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => LoginPage()),
                    );
                  },
                  child: const Text('登出'),
                ),
              ),
            ),
          ],
        ),
      ),
      // extendBodyBehindAppBar: true,
      body: Chat(
        messages: _messages,
        audioMessageBuilder: _audioMessageBuilder,
        onAttachmentPressed: _handleAttachmentPressed,
        onMessageTap: _handleMessageTap,
        onPreviewDataFetched: _handlePreviewDataFetched,
        onSendPressed: _handleSendPressed,
        usePreviewData: false,
        showUserNames: true,
        user: _user,
        customBottomWidget: CustomMessageInput(
          handleSendPressed: _handleSendPressed,
          handleAttachmentPressed: _handleAttachmentPressed,
          onTapUp: (_) async {
            await recorder.stop();
            overlayEntry.remove();
            _sendAudioMessage();
          },
          onTapDown: (_) async {
            Overlay.of(context).insert(overlayEntry);
            audioFileName = '${randomUniqueId()}.wav';
            await recorder.start(
                const RecordConfig(
                    encoder: AudioEncoder.wav, sampleRate: 16000),
                path: '$audioFileStorageDirectory/$audioFileName');
          },
          onTapCancel: () {
            overlayEntry.remove();
            recorder.cancel();
          },
        ),
        theme: DefaultChatTheme(
          backgroundColor: Colors.grey[100]!,
          secondaryColor: Colors.white,
        ),
      ),
    );
  }

  void _addMessageToChat(types.Message message) {
    setState(() {
      _messages.insert(0, message);
    });
  }

  void _sendAudioMessage() async {
    setState(() {
      _clearButtonWidth = 90.0;
    });

    final filePath = '$audioFileStorageDirectory/$audioFileName';
    final file = File(filePath);
    final fileBytes = await file.readAsBytes();
    // final fileSize = await file.
    final audioMessage = types.AudioMessage(
      author: _user,
      duration: const Duration(milliseconds: 1),
      id: randomUniqueId(),
      name: 'my speech',
      size: fileBytes.length,
      uri: '$audioFileStorageDirectory/$audioFileName',
    );

    _addMessageToChat(audioMessage);

    chatAgent.chatWithAudio(
      fileBytes,
      '$audioFileName',
      isInnerChat: _isInnerChat,
      replyInSpeech: settings.replyInSpeech,
      enableInstruct: settings.enableInstruct,
      enableComment: settings.enableComment,
    );

    var response = await chatAgent.singleGetResponse();
    _parserReplyContent(response);
    // await recorder.start(const RecordConfig(encoder: AudioEncoder.wav), path: '$documentDir/test.wav');
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

  Widget _audioMessageBuilder(types.AudioMessage message,
      {required messageWidth}) {
    return AudioMessageBlock(message: message, messageWidth: messageWidth);
  }

  void _handleFileSelection() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.any,
      allowMultiple: false,
      withData: true,
    );

    if (result != null && result.files.isNotEmpty) {
      fileMessage = types.FileMessage(
        author: _user,
        createdAt: DateTime.now().millisecondsSinceEpoch,
        id: randomUniqueId(),
        name: result.files.single.name,
        size: result.files.single.size,
        uri: !kIsWeb ? result.files.single.path! : result.files.single.name,
      );
      // result.files.single.bytes
      // if (!kIsWeb) {
      //   waitForUploadingFileBytes =
      //   await File(result.files.single.path!).readAsBytes();
      // } else {
      // print(result.files.first.bytes);
      waitForUploadingFileBytes = result.files.first.bytes;
      // }

      waitForUploadingFile = result.files.single;

      if (mounted) {
        Provider.of<ChatLabridgeStates>(context, listen: false)
            .addUploadingContent();
      }

      // setState(() {
      //   _waitForUploadingContentsCount = 1;
      // });

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
        id: randomUniqueId(),
        name: result.name,
        size: bytes.length,
        uri: result.path,
        width: image.width.toDouble(),
      );

      _addMessageToChat(message);
    }
  }

  void _handleMessageTap(BuildContext context, types.Message message) async {
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

      // await OpenFilex.open(localPath);
      if (context.mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
              builder: (context) => PdfViewerRoute(pdfPath: localPath)),
        );
      }
    } else if (message is types.AudioMessage) {
      await player.release();
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

  void _parserReplyContent(Map<String, dynamic> response) async {
    _isInnerChat = response['inner_chat'];

    /// determine which reply was sent from server
    /// {'reply_text' : string } or {'reply_speech' : Map<String, int>}
    /// For more information, please see  https://github.com/scramblingsnail/Labridge/blob/main/docs/zh/interface/server-client.md
    if (response.containsKey('reply_text')) {
      final labridgeTextMessage = types.TextMessage(
        author: _labridge,
        createdAt: DateTime.now().millisecondsSinceEpoch,
        id: randomUniqueId(),
        text: response['reply_text'].toString().trim(),
      );
      _addMessageToChat(labridgeTextMessage);
    } else {
      final replySpeechPaths = Map<String, int>.from(response['reply_speech']);

      for (final speechPathEntry in replySpeechPaths.entries) {
        var localPath = await chatAgent.downloadFile(speechPathEntry.key, localFileName: '${randomUniqueId()}.wav');
        // print(localPath);
        final labridgeAudioMessage = types.AudioMessage(
          author: _labridge,
          createdAt: DateTime.now().millisecondsSinceEpoch,
          id: randomUniqueId(),
          name: 'labridge\'s speech',
          size: speechPathEntry.value,
          uri: localPath,
          duration: const Duration(seconds: 4),
        );
        _addMessageToChat(labridgeAudioMessage);
      }
    }

    /// process extra_info
    if (response['extra_info'] != null) {
      final labridgeTextMessage = types.TextMessage(
        author: _labridge,
        createdAt: DateTime.now().millisecondsSinceEpoch,
        id: randomUniqueId(),
        text: response['extra_info'].toString().trim(),
      );
      _addMessageToChat(labridgeTextMessage);
    }

    /// Reference Files. For example, research articles
    if (response['references'] != null) {
      final references = Map<String, int>.from(response['references']);
      for (final referEntry in references.entries) {
        var fileName = referEntry.key.replaceAll('\\', '/');
        fileName = p.basename(fileName);
        final fileMessage = types.FileMessage(
          author: _labridge,
          id: randomUniqueId(),
          name: fileName,
          size: referEntry.value,
          uri: 'remote:${referEntry.key}',
        );

        _addMessageToChat(fileMessage);
      }
    }
  }

  void _handleSendPressed(types.PartialText message) async {
    /// TODO: performance
    setState(() {
      _clearButtonWidth = 90.0;
    });

    final textMessage = types.TextMessage(
      author: _user,
      createdAt: DateTime.now().millisecondsSinceEpoch,
      id: randomUniqueId(),
      text: message.text,
    );

    _addMessageToChat(textMessage);

    Map<String, dynamic> response;

    /// 发送消息并等待响应
    if (Provider.of<ChatLabridgeStates>(context, listen: false)
            .waitForUploadingContentsCount ==
        0) {
      chatAgent.chatWithText(
        message.text,
        isInnerChat: _isInnerChat,
        replyInSpeech: settings.replyInSpeech,
        enableComment: settings.enableComment,
        enableInstruct: settings.enableInstruct,
      );
      response = await chatAgent.singleGetResponse();
    } else {
      _addMessageToChat(fileMessage!);
      // setState(() {
      //   _waitForUploadingContentsCount = 0;
      // });
      if (mounted) {
        Provider.of<ChatLabridgeStates>(context, listen: false)
            .clearUploadingContents();
      }

      chatAgent.chatWithFile(
        waitForUploadingFileBytes!,
        waitForUploadingFile!.name,
        message.text,
        isInnerChat: _isInnerChat,
        replyInSpeech: settings.replyInSpeech,
        enableComment: settings.enableComment,
        enableInstruct: settings.enableInstruct,
      );
      response = await chatAgent.singleGetResponse();
    }

    _parserReplyContent(response);
  }
}
