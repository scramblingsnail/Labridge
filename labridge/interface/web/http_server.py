from typing import Annotated, Union

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HTTPChatMessage(BaseModel):
    text: str


@app.post("/users/{user_id}/user_input")
async def post_user_input(user_id: str, req: HTTPChatMessage):
    return HTTPChatMessage(text=f"this is response for user {user_id}")


@app.post("/users/{user_id}/chat_with_file")
async def post_chat_with_file(
    user_id: str,
    file: Annotated[bytes, File()],
    text: Annotated[str, Form()],
):
    return {
        "user_id": user_id,
        "file_size": len(file),
        "text": text,
    }


@app.get("/users/{user_id}/files/{filename}")
async def get_file(user_id: str, filename: str):
    return {}


@app.post("/users/{user_id}/chat_speech")
async def post_chat_speed(user_id: str, file: Annotated[bytes, File()]):
    return {"file_size": len(file)}
