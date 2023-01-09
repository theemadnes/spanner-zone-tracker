import os
from google.cloud import spanner
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

#print(os.getenv("SPANNER_INSTANCE"))

def create_database(instance_id, database_id):
    """Creates a database and tables for sample data."""
    spanner_client = spanner.Client() # deplicate - remove later?
    instance = spanner_client.instance(instance_id)

    database = instance.database(
        database_id,
        ddl_statements=[
            """CREATE TABLE ZoneCounter (
            ZoneId       STRING(64) NOT NULL,
            Count        INT64 NOT NULL) PRIMARY KEY (ZoneId)""",
        ],
    )

    operation = database.create()

    print("Waiting for operation to complete...")
    operation.result(int(os.getenv("OPERATION_TIMEOUT_SECONDS", 10)))

    print("Created database {} on instance {}".format(database_id, instance_id))


# check to see if we need to create database
spanner_client = spanner.Client()
instance = spanner_client.instance(os.getenv("SPANNER_INSTANCE"))
if instance.database(os.getenv("DATABASE_ID")).exists():
    print(f'Database {os.getenv("DATABASE_ID")} found on Spanner instance {os.getenv("SPANNER_INSTANCE")}. Continuing...')

else:
    print(f'Database {os.getenv("DATABASE_ID")} not found on Spanner instance {os.getenv("SPANNER_INSTANCE")}. Attempting to create...')
    create_database(os.getenv("SPANNER_INSTANCE"), os.getenv("DATABASE_ID"))

