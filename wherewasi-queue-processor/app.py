import os
from dotenv import load_dotenv
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError

load_dotenv()  # take environment variables from .env

# TODO(developer)
project_id = os.getenv("PROJECT_ID")
subscription_id = os.getenv("SUB_ID")
# Number of seconds the subscriber should listen for messages
timeout = float(os.getenv("TIMEOUT", 5.0))

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    print(f"Received {message.data!r}.")
    message.ack()

# Limit the subscriber to only have ten outstanding messages at a time.
flow_control = pubsub_v1.types.FlowControl(max_messages=10)

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