from typing import Union

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from labridge.models.remote.utils import load_server_llm


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
llm = load_server_llm()


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


def run_remote_model(host: str, port: int):
	uvicorn.run(app, host=host, port=port, workers=1)


if __name__ == "__main__":
	r""" This URL is the proxy url of an Autodl server. """
	uvicorn.run(app, host='127.0.0.1', port=6006, workers=1)
