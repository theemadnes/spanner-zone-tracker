import os
import json, typing
from starlette.responses import Response
from fastapi import FastAPI
import uvicorn
import logging
from logging.config import dictConfig
from dotenv import load_dotenv
import frontend_payload

load_dotenv()  # take environment variables from .env

# set up logging
'''
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'default': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['default']
    }
})'''


# handle pretty-printing of JSON response from https://stackoverflow.com/questions/67783530/is-there-a-way-to-pretty-print-prettify-a-json-response-in-fastapi
class PrettyJSONResponse(Response):
    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(", ", ": "),
        ).encode("utf-8")

app = FastAPI()

@app.get("/healthz")
async def i_am_healthy():
    return ('OK')

@app.get("/", response_class=PrettyJSONResponse)
async def read_root():
    #return {"Hello": "World"}
    payload = frontend_payload.FrontendPayload()
    return payload.build_payload()

if __name__ == '__main__':

    uvicorn.run("app:app", port=int(os.getenv("PORT", "8080")), reload=os.getenv("DEBUG", "False"))