import emoji
import logging
from logging.config import dictConfig
from datetime import datetime
import sys
import os
import socket
import httpx
import redis
from dotenv import load_dotenv

METADATA_URL = 'http://metadata.google.internal/computeMetadata/v1/'
METADATA_HEADERS = {'Metadata-Flavor': 'Google'}

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

# set up emoji list
emoji_list = list(emoji.EMOJI_DATA.keys())

class FrontendPayload(object):

    def __init__(self):

        self.payload = {}
        '''
        # use connection API to connect to Spanner
        self.connection = connect(os.getenv("INSTANCE_ID"), os.getenv("DATABASE_ID"))
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()'''
        self.redis_host = os.environ.get('REDIS_IP', 'localhost')
        self.redis_port = int(os.environ.get('REDIS_PORT', 6379))
        self.redis_client = redis.StrictRedis(host=self.redis_host, port=self.redis_port)

        # attempt to call GCE metadata endpoint and store results - no need to call metadata endpoint every time this service gets called
        self.gce_metadata = {}
        r = httpx.get(METADATA_URL + '?recursive=true',
                                headers=METADATA_HEADERS)
        if r.status_code == 200:
            logging.info("Successfully accessed GCE metadata endpoint.")
            self.gce_metadata = r.json()
        else:
            logging.warning("Unable to access GCE metadata endpoint.")
            self.payload['zone'] = "unknown" # default value



    def build_payload(self):

        '''
        self.payload['zone_hits'] = {}
        self.cursor.execute(f'SELECT * FROM {os.getenv("TABLE_ID")}')
        current_data = self.cursor.fetchall()
        self.payload['zone_hits'] = dict(current_data)'''


        # grab info from GCE metadata
        if len(self.gce_metadata):
            # get project / zone info
            self.payload['project_id'] = self.gce_metadata['project']['projectId']
            self.payload['zone'] = self.gce_metadata['instance']['zone'].split('/')[-1]

            # if we're running in GKE, we can also get cluster name
            try:
                self.payload['cluster_name'] = self.gce_metadata['instance']['attributes']['cluster-name']
            except:
                logging.warning("Unable to capture GKE cluster name.")
            try:
                    self.payload['gce_instance_id'] = self.gce_metadata['instance']['id']
            except:
                logging.warning("Unable to capture GCE instance ID.")
            try:
                self.payload['gce_service_account'] = self.gce_metadata['instance']['serviceAccounts']['default']['email']
            except:
                logging.warning("Unable to capture GCE service account.")

        # redis updates
        self.redis_client.incr(self.payload['zone'], 1)

        # now get all keys and values from redis
        keys = self.redis_client.keys()
        vals = self.redis_client.mget(keys)
        kv = zip(keys, vals)
        #print(list(kv))
        kv_dict = {}
        for i in kv:
            kv_dict[i[0].decode("utf-8")] = int(i[1])
        #print(kv_dict)
        self.payload['zone_hits'] = kv_dict

        # get pod name, emoji & datetime
        self.payload['pod_name'] = socket.gethostname()
        self.payload['pod_name_emoji'] = emoji_list[hash(
            socket.gethostname()) % len(emoji_list)]
        self.payload['timestamp'] = datetime.now().replace(
            microsecond=0).isoformat()

        # get namespace, pod ip, and pod service account via downward API
        if os.getenv('POD_NAMESPACE'):
            self.payload['pod_namespace'] = os.getenv('POD_NAMESPACE')
        else:
            logging.warning("Unable to capture pod namespace.")

        if os.getenv('POD_IP'):
            self.payload['pod_ip'] = os.getenv('POD_IP')
        else:
            logging.warning("Unable to capture pod IP address.")

        if os.getenv('POD_SERVICE_ACCOUNT'):
            self.payload['pod_service_account'] = os.getenv(
                'POD_SERVICE_ACCOUNT')
        else:
            logging.warning("Unable to capture pod KSA.")

        # get the METADATA envvar
        if os.getenv('METADATA'):
            self.payload['metadata'] = os.getenv('METADATA')
        else:
            logging.warning("Unable to capture metadata environment variable.")

        return self.payload