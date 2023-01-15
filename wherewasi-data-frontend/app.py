import os
import json, typing
from starlette.responses import Response
from fastapi import FastAPI
import uvicorn
import logging
from logging.config import dictConfig
from dotenv import load_dotenv
import frontend_payload
from google.cloud import pubsub_v1
#from concurrent.futures import ThreadPoolExecutor


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

# create pubsub client
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(os.getenv("PROJECT_ID"), os.getenv("TOPIC_ID"))

# create web server
app = FastAPI()

# create payload object
payload_obj = frontend_payload.FrontendPayload()

@app.get("/healthz")
async def i_am_healthy():
    return ('OK')

#@app.get("/")#, response_class=PrettyJSONResponse)
@app.get("/", response_class=PrettyJSONResponse)
async def read_root():
    #generate payload
    payload = payload_obj.build_payload()

    # publish to pubsub topic
    future = publisher.publish(topic_path, json.dumps(payload).encode("utf-8"))
    #print(future.result()) # fire and forget

    return payload

if __name__ == '__main__':

    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8080")), reload=os.getenv("DEBUG", "False"))