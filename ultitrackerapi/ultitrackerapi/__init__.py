import logging
import os

POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE")
POSTGRES_HOSTNAME = os.getenv("POSTGRES_HOSTNAME")
POSTGRES_USERNAME = os.getenv("POSTGRES_USERNAME")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_SCHEMA = os.getenv("POSTGRES_SCHEMA")
NUM_CONNECTION_RETRIES = 5

ANNOTATION_EXPIRATION_DURATION = 10
NUM_IMAGES_FOR_ANNOTATION = 5


def get_logger(name, level=logging.INFO):
    # create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    return logger


import boto3

# start s3 client
_s3Client = boto3.client("s3")

def get_s3Client():
    return _s3Client

from ultitrackerapi.sql_backend import SQLClient

_sqlClient = SQLClient(
    username=POSTGRES_USERNAME,
    password=POSTGRES_PASSWORD,
    hostname=POSTGRES_HOSTNAME,
    port=POSTGRES_PORT,
    database=POSTGRES_DATABASE,
    num_connection_retries=NUM_CONNECTION_RETRIES
)

from ultitrackerapi.backend import InMemoryBackend
from ultitrackerapi.sql_backend import SQLBackend
from ultitrackerapi import models

# _backend = InMemoryBackend(game_db={}, user_db={})
_backend = SQLBackend(_sqlClient)

def get_backend():
    return _backend
