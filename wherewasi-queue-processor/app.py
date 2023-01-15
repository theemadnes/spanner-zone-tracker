import os
from dotenv import load_dotenv
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError, ThreadPoolExecutor
import json
from collections import defaultdict
from google.cloud import spanner
from google.cloud.spanner_dbapi.connection import connect


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
    print("Running with no timeout.")
max_messages = int(os.getenv("MAX_MESSAGES", 10))
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

# Spanner setup
spanner_client = spanner.Client()
instance = spanner_client.instance(os.getenv("INSTANCE_ID"))
database = instance.database(os.getenv("DATABASE_ID"))
table = os.getenv("TABLE_ID")
print(f"Spanner instance: {instance.name}\nSpanner database: {database.name}\nSpanner table: {table}")

# variable to track how many messages have been processed so far; limited by $CHECKPOINT_MESSAGE_COUNT
messages_processed = 0 
max_messages_processed = int(os.getenv("CHECKPOINT_MESSAGE_COUNT", 500))

def insert_zone_metrics(transaction):

    # stage zone counts
    global zone_count # laziness
    zone_count_stage = zone_count.copy()
    zone_count = defaultdict(lambda: 0) # reset zone count

    # use connection API to get existing records
    connection = connect(os.getenv("INSTANCE_ID"), os.getenv("DATABASE_ID"))
    connection.autocommit = True

    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM {table}")

    current_data = cursor.fetchall()
    current_data_dict = dict(current_data) #list_to_dict(current_data)

    # dicts used to determine whether to insert or update records in DB
    updates = {}
    new_data = {}

    for k in current_data_dict.keys():
        if k in zone_count_stage.keys():
            updates[k] = current_data_dict[k] + zone_count_stage[k]

    for j in zone_count_stage.keys():
        if j not in current_data_dict.keys():
            new_data[j] = zone_count_stage[j]

    if len(new_data):
    
        row_ct = transaction.insert(
            table,
            columns=['zone', 'hits'],
            values=[[key, value] for key, value in new_data.items()],
        )
        print("{} new record(s) inserted.".format(len(new_data)))

    if len(updates):

        row_in = transaction.update(
            table,
            columns=['zone', 'hits'],
            values=[[key, value] for key, value in updates.items()],
        )
        print("{} record(s) updated.".format(len(updates)))

zone_count = defaultdict(lambda: 0) # tracks counts per zone
executor = ThreadPoolExecutor(10) # handles message acks async

def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    global messages_processed # being lazy
    print(f"Received {message.data!r}.")
    zone_count[json.loads(message.data.decode())['zone']] += 1
    print(dict(zone_count))
    #message.ack()
    messages_processed += 1
    future = executor.submit(message.ack(), ("Completed")) # send `ack` to threadpool executor
    # test to see if we've hit $CHECKPOINT_MESSAGE_COUNT; if, so, write to DB
    print(messages_processed)
    if messages_processed >= max_messages_processed:
        print(f"Hit max messaged processed value of {max_messages_processed}")
        messages_processed = 0
        database.run_in_transaction(insert_zone_metrics)

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
        database.run_in_transaction(insert_zone_metrics) # write to the database before shutdown
        streaming_pull_future.cancel()  # Trigger the shutdown.
        streaming_pull_future.result()  # Block until the shutdown is complete.