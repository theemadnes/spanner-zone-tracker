import os
from dotenv import load_dotenv
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError, ThreadPoolExecutor
import json
from collections import defaultdict
from google.cloud import spanner

load_dotenv()  # take environment variables from .env

# PubSub setup
project_id = os.getenv("PROJECT_ID")
subscription_id = os.getenv("SUB_ID")
# Number of seconds the subscriber should listen for messages
if os.getenv("TIMEOUT", None):
    timeout = float(os.getenv("TIMEOUT"))
    print(f'Running with timeout of {timeout} seconds.')
else:
    timeout = None
    print("Running with no timeout. This will clear the queue but won't write to the database.")
max_messages = int(os.getenv("MAX_MESSAGES", 10))
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

# Spanner setup
spanner_client = spanner.Client()
instance = spanner_client.instance(os.getenv("INSTANCE_ID"))
database = instance.database(os.getenv("DATABASE_ID"))

zone_count = defaultdict(lambda: 0) # tracks counts per zone
executor = ThreadPoolExecutor(10)

def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    print(f"Received {message.data!r}.")
    #print(json.loads(message.data.decode())['zone'])
    zone_count[json.loads(message.data.decode())['zone']] += 1
    print(dict(zone_count))
    #message.ack()
    future = executor.submit(message.ack(), ("Completed")) # send `ack` to threadpool executor

# Limit the subscriber to only have ten outstanding messages at a time.
flow_control = pubsub_v1.types.FlowControl(max_messages=max_messages)

streaming_pull_future = subscriber.subscribe(
    subscription_path, callback=callback, flow_control=flow_control
)
print(f"Listening for messages on {subscription_path}..\n")

# Wrap subscriber in a 'with' block to automatically call close() when done.
with subscriber:
    try:
        # When `timeout` is not set, result() will block indefinitely,
        # unless an exception is encountered first.
        streaming_pull_future.result(timeout=timeout)
    except TimeoutError:
        streaming_pull_future.cancel()  # Trigger the shutdown.
        streaming_pull_future.result()  # Block until the shutdown is complete.