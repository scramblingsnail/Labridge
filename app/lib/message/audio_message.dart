import 'package:flutter/material.dart';
import 'package:flutter_chat_types/flutter_chat_types.dart' as types;
import 'package:flutter_chat_ui/flutter_chat_ui.dart';

class AudioMessageBlock extends StatelessWidget {
  final types.AudioMessage message;
  final int messageWidth;

  const AudioMessageBlock({
    super.key,
    required this.message,
    required this.messageWidth,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(8),
      color: Theme.of(context).colorScheme.primaryContainer,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primary,
              borderRadius: BorderRadius.circular(21),
            ),
            height: 42,
            width: 42,
            child: const Icon(Icons.multitrack_audio_rounded, color: Colors.white,),
          ),
          Flexible(
            child: Container(
              margin: const EdgeInsetsDirectional.only(
                start: 16,
                end: 4
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message.name,
                    textWidthBasis: TextWidthBasis.longestLine,
                  ),
                  Container(
                    margin: const EdgeInsets.only(
                      top: 4,
                    ),
                    child: Text(
                      formatBytes(message.size.truncate()),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
