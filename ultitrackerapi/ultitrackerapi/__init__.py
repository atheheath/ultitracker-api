import boto3

from ultitrackerapi import models
from passlib.hash import pbkdf2_sha256

POSTGRES_DATABASE = ""
POSTGRES_HOSTNAME = ""
POSTGRES_USERNAME = ""
POSTGRES_PASSWORD = ""
POSTGRES_PORT = ""
NUM_CONNECTION_RETRIES = ""

# start s3 client
_s3Client = boto3.client("s3")

from ultitrackerapi.backend import InMemoryBackend

_backend = InMemoryBackend(
    game_db={
        "test": models.GameList(
            game_list=[
                models.Game(
                    authorized_users=["test"],
                    data={
                        "home": "Team 1",
                        "away": "Team 2",
                        "date": "2019-10-31",
                        "length": "00:00:10",
                        "bucket": "ultitracker-videos-test",
                        "thumbnail_key": "chicago.jpeg",
                        "video_key": "test_vid_1.mp4",
                        "name": "Chicago",
                    },
                    game_id="test_vid_1.mp4",
                ),
                models.Game(
                    authorized_users=["test"],
                    data={
                        "home": "Team 1",
                        "away": "Team 3",
                        "date": "2019-11-01",
                        "length": "00:00:10",
                        "bucket": "ultitracker-videos-test",
                        "thumbnail_key": "madison.jpeg",
                        "video_key": "test_vid_2.mp4",
                        "name": "Madison",
                    },
                    game_id="test_vid_2",
                ),
            ]
        )
    },
    user_db={
        "test": models.UserInDB(
            username="test",
            email="test@test.com",
            full_name="Jane Doe",
            salted_password=pbkdf2_sha256.hash("test"),
        )
    },
)


def get_backend():
    return _backend

def get_s3Client():
    return _s3Client