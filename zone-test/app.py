import os
from dotenv import load_dotenv
from google.cloud import spanner
from google.cloud.spanner_dbapi.connection import connect

load_dotenv()


def main():
    print("hi")

