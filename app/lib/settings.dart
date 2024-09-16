import 'package:shared_preferences/shared_preferences.dart';

const baseUrl = "http://210.28.141.187:80";

class Settings {
  bool replyInSpeech = false;
  bool enableInstruct = false;
  bool enableComment = false;

  // late final SharedPreferencesWithCache prefsWithCache;
  final SharedPreferencesAsync asyncPrefs = SharedPreferencesAsync();

  // late final SharedPreferences prefsWithCache;
  Future<String?> get userNameInPrefs async => await asyncPrefs.getString('userName');
  set userName(String name) {
    asyncPrefs.setString('userName', name);
  }

  Future<String?> get passwordInPrefs => asyncPrefs.getString('password');
  set password(String password) {
    asyncPrefs.setString('password', password);
  }


}
