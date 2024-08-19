from typing import Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from labridge.agent.utils import get_chat_engine
from labridge.accounts.users import AccountManager
from labridge.common.chat.utils import pack_user_message


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


class HTTPChatMessage(BaseModel):
    text: str


rsp_ok = {"status": "ok"}

chat_engine = get_chat_engine()
user_id = "realzhao"

account_manager = AccountManager()
account_manager.add_user(user_id=user_id, password="123456")


@app.get("/chat_history")
def get_chat_history():
    return chat_engine.chat_history


# @app.post("/reset")
# def post_reset():
#     return rsp_ok


@app.post("/user_input")
def poast_user_input(req: HTTPChatMessage):
    user_query = "User: " + req.text
    message = pack_user_message(
        user_id=user_id,
        chat_group_id=None,
        message_str=user_query,
    )
    response = chat_engine.chat(message=message)

    return HTTPChatMessage(text=str(response))
