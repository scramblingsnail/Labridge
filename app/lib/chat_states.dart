import 'package:flutter/material.dart';

/// Manage states in chat UI
class ChatLabridgeStates extends ChangeNotifier {
  /// if you upload a file, [_waitForUploadingContentsCount] += 1
  int _waitForUploadingContentsCount = 0;

  int get waitForUploadingContentsCount => _waitForUploadingContentsCount;

  void addUploadingContent() {
    _waitForUploadingContentsCount = 1;
    notifyListeners();
  }

  void clearUploadingContents() {
    _waitForUploadingContentsCount = 0;
    notifyListeners();
  }
}
