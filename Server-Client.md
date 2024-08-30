# Server与Client之间的通信说明

## 数据结构：

## Client上传的数据：

### Chat with text:
[ClientTextReq](labridge/interface/http_server):
- text (str): 用户的消息字符串
- reply_in_speech (bool): 用户希望得到语音回复还是文本回复。
- enable_instruct (bool): 当前轮次QA, 用户是否介入Agent的Reasoning
- enable_comment (bool): 当前轮次QA, 用户是否介入Agent的Acting

Post URL: `/users/{user_id}/chat_text`

### Download File:
[ClientDownloadReq](labridge/interface/http_server.py):
- filepath (str): 申请下载的文件路径

Post URL: `/users/{user_id}/files/bytes`

### Chat with file:
- file (bytes): 上传文件的二进制数据
- file_name (str): 上传文件的文件名（包含后缀）
- text (str): 用户与该文件相关的消息
- reply_in_speech (bool): 用户希望得到语音回复还是文本回复。
- enable_instruct (bool): 当前轮次QA, 用户是否介入Agent的Reasoning
- enable_comment (bool): 当前轮次QA, 用户是否介入Agent的Acting

Post URL: `/users/{user_id}/chat_with_file`

### Chat with speech:
- file (bytes): 语音文件的二进制数据
- enable_instruct (bool): 当前轮次QA, 用户是否介入Agent的Reasoning
- enable_comment (bool): 当前轮次QA, 用户是否介入Agent的Acting

Post URL: `/users/{user_id}/chat_speech`

## 从Server获取回复:
Get URL: `/users/{user_id}/response`

### 返回的数据结构
[ServerReply](labridge/agent/chat_msg/msg_types.py):
- reply_text (str): Agent的回复字符串
- valid (bool): 本回复是否是有效回复，若没有得到有效回复，客户端应轮询直至获得有效回复
- references (Dict[str, int]): 参考文件在server的存储路径与文件字节数。
- error (str): 错误信息，如果没有错误，则为`None`.
- inner_chat (bool): 本回复是否是一个Chat调用内部的回复。如果为`True`, 客户端应该把用户接下来的回复发送到相应的 `Inner` URL.
- extra_info (str): 额外信息。其它过长的信息会放在这里，如果没有，则为 `None`

[ServerSpeechReply](labridge/agent/chat_msg/msg_types.py):
- reply_speech (Dict[str, int]): Key: Agent回复的语音文件在Server的存储路径, Value: 语音文件字节数。
- valid (bool): 本回复是否是有效回复，若没有得到有效回复，客户端应轮询直至获得有效回复
- references (Dict[str, int]): 参考文件在server的存储路径与文件字节数。
- inner_chat: Optional[bool] = False
- error (str): 错误信息，如果没有错误，则为`None`.
- extra_info (str): 额外信息。其它过长的信息会放在这里，如果没有，则为 `None`

## 相应的 Inner URL:

### Chat with text:
Inner URL: `/users/{user_id}/inner_chat_text`

### Chat with speech:
Inner URL: `/users/{user_id}/inner_chat_speech`

### Chat with file:
Inner URL: `/users/{user_id}/inner_chat_with_file`