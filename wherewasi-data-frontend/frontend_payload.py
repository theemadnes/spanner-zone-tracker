import emoji
import logging
from logging.config import dictConfig
from datetime import datetime
import sys
import os
import socket
import httpx

METADATA_URL = 'http://metadata.google.internal/computeMetadata/v1/'
METADATA_HEADERS = {'Metadata-Flavor': 'Google'}

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

    def build_payload(self):

        # grab info from GCE metadata
        try:
            #with httpx.Client() as client:
            r = httpx.get(METADATA_URL + '?recursive=true',
                                headers=METADATA_HEADERS)
            # get project / zone info
            self.payload['project_id'] = r.json()['project']['projectId']
            self.payload['zone'] = r.json()['instance']['zone'].split('/')[-1]

            # if we're running in GKE, we can also get cluster name
            try:
                self.payload['cluster_name'] = r.json()['instance']['attributes']['cluster-name']
            except:
                logging.warning("Unable to capture GKE cluster name.")
            try:
                    self.payload['gce_instance_id'] = r.json()['instance']['id']
            except:
                logging.warning("Unable to capture GCE instance ID.")
            try:
                self.payload['gce_service_account'] = r.json()['instance']['serviceAccounts']['default']['email']
            except:
                logging.warning("Unable to capture GCE service account.")
        except:
            logging.warning("Unable to access GCE metadata endpoint.")
            self.payload['zone'] = "unknown" # default value

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
            logging.warning("Unable to capture metadata.")

        return self.payload