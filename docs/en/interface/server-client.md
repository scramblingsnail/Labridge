# Description for the communication between the Server and Client

## Data Structure

### User log up, log in:
[ClientLogInUpReq](labridge/interface/http_server):

- user_id: the user id of a lab member
- password: given password

Sign in:

- Post URL: `/accounts/log-up`
- Return: return user_id if success，otherwise return None

Log up:

- Post URL: `/accounts/log-up`
- Return: return user_id if success，otherwise return None

## Data uploaded by clients：

### Chat with text:
**ClientTextReq**:

- text (str): The message string of the user
- reply_in_speech (bool): 用户希望得到语音回复还是文本回复。
- enable_instruct (bool): 当前轮次QA, 用户是否介入Agent的Reasoning
- enable_comment (bool): 当前轮次QA, 用户是否介入Agent的Acting

Post URL: `/users/{user_id}/chat_text`

### Download File:
**ClientDownloadReq**:

- filepath (str): The path of the requested file

Post URL: `/users/{user_id}/files/bytes`

### Chat with file:
- file (bytes): The bytes of the uploaded file.
- file_name (str): The name of the uploaded file (including suffix)
- text (str): The user's attached text
- reply_in_speech (bool): Whether the user expect reply in speech or not

Post URL: `/users/{user_id}/chat_with_file`

### Chat with speech:
- file (bytes): The bytes of the speech file

Post URL: `/users/{user_id}/chat_speech`

## Get reply from the server:
Get URL: `/users/{user_id}/response`

### Returned data structure
**ServerReply**:

- reply_text (str): The reply string of the agent
- valid (bool): Whether this reply is valid. If it is invalid, the client should keep requesting until receiving a valid response.
- references (Dict[str, int]): Key -- the path of the reference file, Value -- the file size of the ref file
- error (str): The error message. If no error occurs, it is `None`
- inner_chat (bool): Whether this reply is an `inner` reply. If `True`, the client should send the user's next message to
the corresponding `Inner` URL.

**ServerSpeechReply**:

- reply_speech (str): The file path of the agent's speech reply
- valid (bool):  Whether this reply is valid. If it is invalid, the client should keep requesting until receiving a valid response.
- references (Dict[str, int]): Key -- the path of the reference file, Value -- the file size of the ref file
- inner_chat: Optional[bool]: Whether this reply is an `inner` reply. If `True`, the client should send the user's next message to
the corresponding `Inner` URL.
- error (str): The error message. If no error occurs, it is `None`

## Corresponding Inner URL:

### Chat with text:
Inner URL: `/users/{user_id}/inner_chat_text`

### Chat with speech:
Inner URL: `/users/{user_id}/inner_chat_speech`

### Chat with file:
Inner URL: `/users/{user_id}/inner_chat_with_file`