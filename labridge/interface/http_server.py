import asyncio
import argparse
import sys

import fsspec
import uvicorn


from typing import Dict, Tuple, Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# from pathlib import Path
#
# root = Path(__file__)
# for i in range(3):
#     root = root.parent
# sys.path.append(str(root))
# print(sys.path)

from labridge.agent.chat_msg.msg_types import ChatBuffer
from labridge.agent.chat_agent import ChatAgent
from labridge.agent.chat_msg.msg_types import ChatTextMessage, FileWithTextMessage, ChatSpeechMessage
from labridge.interface.utils import save_temporary_file, read_server_file, error_file
from labridge.accounts.users import AccountManager


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
    reply_in_speech: bool
    enable_instruct: bool
    enable_comment: bool


class ClientDownloadReq(BaseModel):
    filepath: str


class ClientLogInUpReq(BaseModel):
    user_id: str
    password: str


class AccountResponse(BaseModel):
    user_id: Optional[str]


async def single_chat(user_id: str):
    ChatAgent.set_chatting(user_id=user_id, chatting=True)
    packed_msgs = await ChatBuffer.get_user_msg(user_id=user_id)
    if packed_msgs:
        ChatAgent.set_chatting(user_id=user_id, chatting=True)
        agent_response = await ChatAgent.chat(packed_msgs=packed_msgs)
        ChatBuffer.put_agent_reply(
            user_id=user_id,
            reply_str=agent_response.response,
            references=agent_response.references,
            inner_chat=False,
        )
        ChatAgent.set_chatting(user_id=user_id, chatting=False)


@app.post("/accounts/log-in")
async def user_log_in(req: ClientLogInUpReq):
    account_manager = AccountManager()
    log_in = account_manager.user_log_in(user_id=req.user_id, password=req.password)
    if log_in:
        return AccountResponse(user_id=req.user_id)
    else:
        return AccountResponse()


@app.post("/accounts/sign-up")
async def user_sign_up(req: ClientLogInUpReq):
    account_manager = AccountManager()
    account_manager.add_user(user_id=req.user_id, password=req.password)
    ChatAgent.update_chatting_status()
    ChatBuffer.update_buffer_for_new_users()
    return AccountResponse(user_id=req.user_id)


@app.post("/users/{user_id}/inner_chat_text")
async def post_inner_chat_text(user_id: str, req: ClientTextReq):
    user_msg = ChatTextMessage(
        user_id=user_id,
        text=req.text,
        reply_in_speech=req.reply_in_speech,
        enable_instruct=req.enable_instruct,
        enable_comment=req.enable_comment,
    )
    ChatBuffer.put_user_msg(user_msg=user_msg)


@app.post("/users/{user_id}/chat_text")
async def post_chat_text(user_id: str, req: ClientTextReq):
    user_msg = ChatTextMessage(
        user_id=user_id,
        text=req.text,
        reply_in_speech=req.reply_in_speech,
        enable_instruct=req.enable_instruct,
        enable_comment=req.enable_comment,
    )
    ChatBuffer.put_user_msg(user_msg=user_msg)

    if not ChatAgent.is_chatting(user_id=user_id):
        await single_chat(user_id=user_id)


@app.post("/users/{user_id}/inner_chat_with_file")
async def post_inner_chat_with_file(
    user_id: str,
    file: bytes = File(),
    file_name: str = Form(),
    text: str = Form(),
    reply_in_speech: bool = Form(),
    enable_instruct: bool = Form(),
    enable_comment: bool = Form(),
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
        enable_instruct=enable_instruct,
        enable_comment=enable_comment,
    )

    ChatBuffer.put_user_msg(user_msg=user_msg)


@app.post("/users/{user_id}/chat_with_file")
async def post_chat_with_file(
    user_id: str,
    file: bytes = File(),
    file_name: str = Form(),
    text: str = Form(),
    reply_in_speech: bool = Form(),
    enable_instruct: bool = Form(),
    enable_comment: bool = Form(),
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
        enable_instruct=enable_instruct,
        enable_comment=enable_comment,
    )

    ChatBuffer.put_user_msg(user_msg=user_msg)

    if not ChatAgent.is_chatting(user_id=user_id):
        await single_chat(user_id=user_id)


@app.post("/users/{user_id}/inner_chat_speech")
async def post_inner_chat_speech(
    user_id: str,
    file: bytes = File(),
    file_suffix: str = Form(),
    reply_in_speech: bool = Form(),
    enable_instruct: bool = Form(),
    enable_comment: bool = Form(),
):
    speech_path = ChatBuffer.default_user_speech_path(user_id=user_id, speech_suffix=file_suffix)
    save_temporary_file(
        tmp_path=speech_path,
        file_bytes=file,
    )
    user_msg = ChatSpeechMessage(
        user_id=user_id,
        speech_path=speech_path,
        reply_in_speech=reply_in_speech,
        enable_instruct=enable_instruct,
        enable_comment=enable_comment,
    )
    ChatBuffer.put_user_msg(user_msg=user_msg)


@app.post("/users/{user_id}/chat_speech")
async def post_chat_speech(
    user_id: str,
    file: bytes = File(),
    reply_in_speech: bool = Form(),
    enable_instruct: bool = Form(),
    enable_comment: bool = Form(),
):
    speech_path = ChatBuffer.default_user_speech_path(user_id=user_id)
    save_temporary_file(
        tmp_path=speech_path,
        file_bytes=file,
    )

    user_msg = ChatSpeechMessage(
        user_id=user_id,
        speech_path=speech_path,
        reply_in_speech=reply_in_speech,
        enable_instruct=enable_instruct,
        enable_comment=enable_comment,
    )

    ChatBuffer.put_user_msg(user_msg=user_msg)

    if not ChatAgent.is_chatting(user_id=user_id):
        await single_chat(user_id=user_id)


@app.post("/users/{user_id}/files/bytes")
async def get_file(user_id: str, req: ClientDownloadReq):
    path = req.filepath
    fs = fsspec.filesystem("file")
    if fs.exists(path):
        return FileResponse(path=path)
    else:
        error_path, error_f_name = error_file(
            error_str=f"File path {path} does not exist!",
            user_id=user_id,
        )
        return FileResponse(path=error_path, filename=error_f_name)


@app.get("/users/{user_id}/files/{filepath}")
async def get_get_file(uesr_id:str, filepath:str):
    return FileResponse(path=filepath)


@app.get("/users/{user_id}/response")
async def get_response(user_id: str):
    return ChatBuffer.get_agent_reply(user_id=user_id)


@app.post("/users/{user_id}/clear_history")
async def clear_history(user_id: str):
    ChatAgent.short_memory_manager.clear_memory(user_id=user_id)


def run_http_server(host_url: str, port: int):
    uvicorn.run(app, host=host_url, port=port, workers=1)


if __name__ == "__main__":
    host = "localhost" # '127.0.0.1'
    port = 6006
    uvicorn.run(app, host=host, port=port, workers=1)
