import asyncio

import fsspec
import uvicorn
from typing import Dict, Tuple

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from labridge.agent.chat_msg.msg_types import ChatBuffer
from labridge.agent.chat_agent import ChatAgent
from labridge.agent.chat_msg.msg_types import ChatTextMessage, FileWithTextMessage, ChatSpeechMessage
from labridge.interface.utils import save_temporary_file, read_server_file


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClientTextReq(BaseModel):
    text: str

class ClientDownloadReq(BaseModel):
    filepath: str


async def single_chat(user_id: str):
    if not ChatAgent.is_chatting(user_id=user_id):
        ChatAgent.set_chatting(user_id=user_id, chatting=True)
        packed_msgs = await ChatBuffer.get_user_msg(user_id=user_id)
        if packed_msgs:
            ChatAgent.set_chatting(user_id=user_id, chatting=True)
            agent_response = await ChatAgent.chat(packed_msgs=packed_msgs)
            ChatBuffer.put_agent_reply(
                user_id=user_id,
                reply_str=agent_response.response,
                references=agent_response.references,
                reply_in_speech=agent_response.reply_in_speech,
                inner_chat=False,
            )
            ChatAgent.set_chatting(user_id=user_id, chatting=False)


@app.post("/users/{user_id}/inner_chat_text")
async def post_inner_chat_text(user_id: str, req: ClientTextReq):
    user_msg = ChatTextMessage(user_id=user_id, text=req.text)
    ChatBuffer.put_user_msg(user_msg=user_msg)


@app.post("/users/{user_id}/chat_text")
async def post_chat_text(user_id: str, req: ClientTextReq):
    user_msg = ChatTextMessage(user_id=user_id, text=req.text)
    ChatBuffer.put_user_msg(user_msg=user_msg)

    if not ChatAgent.is_chatting(user_id=user_id):
        await single_chat(user_id=user_id)


@app.post("/users/{user_id}/inner_chat_with_file")
async def post_inner_chat_with_file(
    user_id: str,
    file: bytes = File(),
    file_name: str = Form(),
    text: str = Form(),
    reply_in_speech: bool = False,
):
    tmp_path = ChatBuffer.default_tmp_file_path(
        user_id=user_id,
        file_name=file_name,
    )

    save_temporary_file(
        tmp_path=tmp_path,
        file_bytes=file,
    )

    user_msg = FileWithTextMessage(
        user_id=user_id,
        attached_text=text,
        file_path=tmp_path,
        reply_in_speech=reply_in_speech,
    )

    ChatBuffer.put_user_msg(user_msg=user_msg)


@app.post("/users/{user_id}/chat_with_file")
async def post_chat_with_file_web(
    user_id: str,
    file: bytes = File(),
    file_name: str = Form(),
    text: str = Form(),
    reply_in_speech: bool = Form(),
):
    tmp_path = ChatBuffer.default_tmp_file_path(
        user_id=user_id,
        file_name=file_name,
    )

    save_temporary_file(
        tmp_path=tmp_path,
        file_bytes=file,
    )

    user_msg = FileWithTextMessage(
        user_id=user_id,
        attached_text=text,
        file_path=tmp_path,
        reply_in_speech=reply_in_speech,
    )

    ChatBuffer.put_user_msg(user_msg=user_msg)

    if not ChatAgent.is_chatting(user_id=user_id):
        await single_chat(user_id=user_id)


# @app.post("/users/{user_id}/inner_chat_with_file/app")
# async def post_inner_chat_with_file_app(
#     user_id: str,
#     file: bytes,
#     file_name: str,
#     text: str,
#     reply_in_speech: bool = False,
# ):
#     tmp_path = ChatBuffer.default_tmp_file_path(
#         user_id=user_id,
#         file_name=file_name,
#     )
#     save_temporary_file(
#         tmp_path=tmp_path,
#         file_bytes=file,
#     )
#     user_msg = FileWithTextMessage(
#         user_id=user_id,
#         attached_text=text,
#         file_path=tmp_path,
#         reply_in_speech=reply_in_speech,
#     )
#     ChatBuffer.put_user_msg(user_msg=user_msg)
#
#
# @app.post("/users/{user_id}/chat_with_file/app")
# async def post_chat_with_file_app(
#     user_id: str,
#     file: bytes,
#     file_name: str,
#     text: str,
#     reply_in_speech: bool = False,
# ):
#     tmp_path = ChatBuffer.default_tmp_file_path(
#         user_id=user_id,
#         file_name=file_name,
#     )
#
#     save_temporary_file(
#         tmp_path=tmp_path,
#         file_bytes=file,
#     )
#
#     user_msg = FileWithTextMessage(
#         user_id=user_id,
#         attached_text=text,
#         file_path=tmp_path,
#         reply_in_speech=reply_in_speech,
#     )
#
#     ChatBuffer.put_user_msg(user_msg=user_msg)
#
#     if not ChatAgent.is_chatting(user_id=user_id):
#         await single_chat(user_id=user_id)


@app.post("/users/{user_id}/inner_chat_speech")
async def post_inner_chat_speech_web(user_id: str, file: bytes = File()):
    speech_path = ChatBuffer.default_user_speech_path(user_id=user_id)
    save_temporary_file(
        tmp_path=speech_path,
        file_bytes=file,
    )
    user_msg = ChatSpeechMessage(
        user_id=user_id,
        speech_path=speech_path,
        reply_in_speech=True,
    )
    ChatBuffer.put_user_msg(user_msg=user_msg)


@app.post("/users/{user_id}/chat_speech")
async def post_chat_speech_web(user_id: str, file: bytes = File()):
    speech_path = ChatBuffer.default_user_speech_path(user_id=user_id)
    save_temporary_file(
        tmp_path=speech_path,
        file_bytes=file,
    )

    user_msg = ChatSpeechMessage(
        user_id=user_id,
        speech_path=speech_path,
        reply_in_speech=True,
    )

    ChatBuffer.put_user_msg(user_msg=user_msg)

    if not ChatAgent.is_chatting(user_id=user_id):
        await single_chat(user_id=user_id)


# @app.post("/users/{user_id}/inner_chat_speech/app")
# async def post_chat_speech_app(user_id: str, file: bytes = File()):
#     speech_path = ChatBuffer.default_user_speech_path(user_id=user_id)
#     save_temporary_file(
#         tmp_path=speech_path,
#         file_bytes=file,
#     )
#     user_msg = ChatSpeechMessage(
#         user_id=user_id,
#         speech_path=speech_path,
#         reply_in_speech=True,
#     )
#     ChatBuffer.put_user_msg(user_msg=user_msg)
#
#
# @app.post("/users/{user_id}/chat_speech/app")
# async def post_chat_speech_app(user_id: str, file: Tuple[str, bytes]):
#
#     print(user_id)
#     print(type(file))
#     print(file)
#     raise ValueError
#
#     speech_path = ChatBuffer.default_user_speech_path(user_id=user_id)
#     save_temporary_file(
#         tmp_path=speech_path,
#         file_bytes=file,
#     )
#
#     user_msg = ChatSpeechMessage(
#         user_id=user_id,
#         speech_path=speech_path,
#         reply_in_speech=True,
#     )
#
#     ChatBuffer.put_user_msg(user_msg=user_msg)
#
#     if not ChatAgent.is_chatting(user_id=user_id):
#         await single_chat(user_id=user_id)

@app.post("/users/{user_id}/files/bytes")
async def get_file(user_id: str, req: ClientDownloadReq):
    path = req.filepath
    fs = fsspec.filesystem("file")
    if fs.exists(path):
        file_bytes = open(path, "rb")
    else:
        file_bytes = "Invalid File".encode("utf-8")

    return StreamingResponse(
        content=file_bytes
    )

@app.get("/users/{user_id}/response")
async def get_response(user_id: str):
    return ChatBuffer.get_agent_reply(user_id=user_id)


if __name__ == "__main__":
    host = '127.0.0.1'
    port = 6006
    uvicorn.run(app, host=host, port=port, workers=1)