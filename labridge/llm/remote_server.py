import json
from typing import Union

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from labridge.agent.utils import get_chat_engine
from labridge.llm.load_server_model import load_server_llm
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


class ModelOutput(BaseModel):
	output: str


rsp_ok = {"status": "ok"}
llm = load_server_llm(use_mindspore=True)


@app.post("/user_input")
def post_user_input(req: HTTPChatMessage):
	local_query = req.text
	response = llm.complete(local_query)
	return ModelOutput(output=str(response))

@app.post("/async_user_input")
async def apost_user_input(req: HTTPChatMessage):
	local_query = req.text
	response = await llm.acomplete(local_query)
	return ModelOutput(output=str(response))


if __name__ == "__main__":
	uvicorn.run(app, host='127.0.0.1', port=6006, workers=1)
