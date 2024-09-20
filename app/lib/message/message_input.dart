import 'package:flutter/material.dart';
import 'package:flutter_chat_types/flutter_chat_types.dart';
import 'package:labridge/chat_states.dart';
import 'package:provider/provider.dart';

class CustomMessageInput extends StatefulWidget {
  const CustomMessageInput({
    super.key,
    required this.handleSendPressed,
    required this.handleAttachmentPressed,
    required this.onTapUp,
    required this.onTapDown,
    required this.onTapCancel,
  });

  final void Function(PartialText) handleSendPressed;
  final void Function() handleAttachmentPressed;

  final void Function(TapUpDetails) onTapUp;
  final void Function(TapDownDetails) onTapDown;
  final void Function() onTapCancel;

  @override
  State<CustomMessageInput> createState() => _CustomMessageInputState();
}

class _CustomMessageInputState extends State<CustomMessageInput> {
  // final _emojiParser = EmojiParser();
  final _inputController = TextEditingController();

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    // _inputController.removeListener(_inputListener);
    _inputController.dispose();
    super.dispose();
  }

  void sendText(String text) {
    if (text.isNotEmpty) {
      PartialText partialText = PartialText(text: text);

      widget.handleSendPressed(partialText);

      _inputController.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      child: Row(
        children: [
          Flexible(
            child: Container(
              decoration: ShapeDecoration(
                shape:
                    StadiumBorder(side: BorderSide(color: Colors.grey[300]!)),
                color: Colors.white,
              ),
              child: TextField(
                controller: _inputController,
                textInputAction: TextInputAction.search,
                onSubmitted: (String text) {
                  sendText(text);
                },
                textCapitalization: TextCapitalization.sentences,
                maxLines: null,
                decoration: InputDecoration(
                  contentPadding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
                  border: const OutlineInputBorder(
                    borderSide: BorderSide.none,
                    borderRadius: BorderRadius.all(Radius.circular(12)),
                  ),
                  hintText: "请输入内容",
                  suffixIcon: Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Consumer<ChatLabridgeStates>(
                            builder: (context, states, child) {
                          return states.waitForUploadingContentsCount == 0
                              ? IconButton(
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 8),
                                  onPressed: widget.handleAttachmentPressed,
                                  icon: Icon(
                                    Icons.attach_file_rounded,
                                    color:
                                        Theme.of(context).colorScheme.primary,
                                  ),
                                )
                              : Badge.count(
                                  count: 1,
                                  backgroundColor:
                                      Theme.of(context).colorScheme.primary,
                                  child: IconButton(
                                    // padding:
                                    //     const EdgeInsets.symmetric(vertical: 8),
                                    onPressed: widget.handleAttachmentPressed,
                                    icon: Icon(
                                      Icons.attach_file_rounded,
                                      color:
                                          Theme.of(context).colorScheme.primary,
                                    ),
                                  ),
                                );
                        }),
                        IconButton(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          onPressed: () {
                            sendText(_inputController.text);
                          },
                          icon: Icon(Icons.send,
                              color: Theme.of(context).colorScheme.primary),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(left: 16),
            child: Material(
              // color: Theme.of(context).colorScheme.primary,
              // color: Colors.transparent,
              child: InkWell(
                // onLongPress: () => {},
                // onTap: () => {},
                onTapUp: widget.onTapUp,
                onTapDown: widget.onTapDown,
                onTapCancel: widget.onTapCancel,
                splashColor: Theme.of(context).colorScheme.primaryContainer,
                customBorder: const CircleBorder(),
                child: Ink(
                  width: 48,

                  height: 48,
                  // color: Theme.of(context).colorScheme.primary,
                  decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Theme.of(context).colorScheme.primary),
                  child: const Icon(
                    Icons.keyboard_voice,
                    color: Colors.white,
                    size: 28,
                  ),
                ),
              ),
            ),
          )
        ],
      ),
    );
  }
}
