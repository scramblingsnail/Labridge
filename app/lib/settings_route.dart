import 'package:flutter/material.dart';
import 'package:labridge/main.dart';
import 'package:toggle_switch/toggle_switch.dart';

class SettingsRoute extends StatelessWidget {
  const SettingsRoute({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('设置'),
      ),
      body: ListView(children: [
        Card(
          elevation: 0.5,
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            leading: const Icon(Icons.phone_bluetooth_speaker),
            title: const Text('回复类型'),
            subtitle: const Text('设置Labridge是否使用语音回复'),
            trailing: ToggleSwitch(
              minWidth: 90.0,
              initialLabelIndex: settings.replyInSpeech ? 1 : 0,
              cornerRadius: 20.0,
              activeFgColor: Colors.white,
              inactiveBgColor: Colors.grey,
              inactiveFgColor: Colors.white,
              totalSwitches: 2,
              labels: const ['文字', '语音'],
              // icons: [FontAwesomeIcons.mars, FontAwesomeIcons.venus],
              activeBgColors: const [
                [Colors.blue],
                [Colors.purple]
              ],
              onToggle: (index) {
                if (index == 1) {
                  settings.replyInSpeech = true;
                } else {
                  settings.replyInSpeech = false;
                }
              },
            ),
          ),
        ),
        Card(
          elevation: 0.5,
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            leading: const Icon(Icons.integration_instructions_outlined),
            title: const Text('启用指令模式'),
            subtitle: const Text('指导Labridge的思考过程'),
            trailing: ToggleSwitch(
              minWidth: 90.0,
              initialLabelIndex: settings.enableInstruct ? 0 : 1,
              cornerRadius: 20.0,
              activeFgColor: Colors.white,
              inactiveBgColor: Colors.grey,
              inactiveFgColor: Colors.white,
              totalSwitches: 2,
              labels: const ['启用', '禁用'],
              // icons: [FontAwesomeIcons.mars, FontAwesomeIcons.venus],
              activeBgColors: const [
                [Colors.blue],
                [Colors.pink]
              ],
              onToggle: (index) {
                if (index == 0) {
                  settings.enableInstruct = true;
                } else {
                  settings.enableInstruct = false;
                }
              },
            ),
          ),
        ),
        Card(
          elevation: 0.5,
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            leading: const Icon(Icons.comment),
            title: const Text('启用评论模式'),
            subtitle: const Text('评论Labridge的执行动作'),
            trailing: ToggleSwitch(
              minWidth: 90.0,
              initialLabelIndex: settings.enableComment ? 0 : 1,
              cornerRadius: 20.0,
              activeFgColor: Colors.white,
              inactiveBgColor: Colors.grey,
              inactiveFgColor: Colors.white,
              totalSwitches: 2,
              labels: const  ['启用', '禁用'],
              // icons: [FontAwesomeIcons.mars, FontAwesomeIcons.venus],
              activeBgColors: const [
                [Colors.blue],
                [Colors.pink]
              ],
              onToggle: (index) {

                if (index == 0) {
                  settings.enableComment = true;
                } else {
                  settings.enableComment = false;
                }
              },
            ),
          ),
        ),
      ]),
    );
  }
}
