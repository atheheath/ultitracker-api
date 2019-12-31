import boto3

from pydantic import BaseModel
from typing import Dict, List
from ultitrackerapi import models


# start s3 client
s3Client = boto3.client("s3")

class Game(BaseModel):
    authorized_users: List[str]
    data: Dict
    game_id: str


class GameResponse(BaseModel):
    data: Dict
    game_id: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if len(self.data) != 0:
            self.data["thumbnail"] = s3Client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.data["bucket"],
                    "Key": self.data["thumbnail_key"]
                },
                ExpiresIn=10
            )

            self.data["video"] = s3Client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.data["bucket"],
                    "Key": self.data["video_key"]
                },
                ExpiresIn=60*60*2
            )


class GameList(BaseModel):
    game_list: List[Game]

    def add_game(self, game: Game):
        self.game_list.append(game)


class GameListResponse(BaseModel):
    game_list: List[GameResponse]


DB = Dict[str, GameList]

db = {
    "test": GameList(
        game_list=[
            Game(
                authorized_users=["test"],
                data={
                    "home": "Team 1",
                    "away": "Team 2",
                    "date": "2019-10-31",
                    "length": "00:00:10",
                    "bucket": "ultitracker-videos-test",
                    "thumbnail_key": "chicago.jpeg",
                    "video_key": "test_vid_1.mp4",
                    "name": "Chicago"
                },
                game_id="test_vid_1.mp4",
            ),
            Game(
                authorized_users=["test"],
                data={
                    "home": "Team 1",
                    "away": "Team 3",
                    "date": "2019-11-01",
                    "length": "00:00:10",
                    "bucket": "ultitracker-videos-test",
                    "thumbnail_key": "madison.jpeg",
                    "video_key": "test_vid_2.mp4",
                    "name": "Madison"
                },
                game_id="test_vid_2",
            ),
        ]
    )
}


def initialize_user(user: models.User):
    if user.username not in db:
        db[user.username] = GameList(game_list=[])


def get_game(game_id: str, user: models.User):
    initialize_user(user)

    game_response = None

    user_game_list = db[user.username]
    for game in user_game_list.game_list:
        if game_id == game.game_id:
            game_response = GameResponse(data=game.data, game_id=game.game_id)
            break

    return game_response


def get_game_list(user: models.User):
    initialize_user(user)

    return GameListResponse(
        game_list=[
            GameResponse(data=game.data, game_id=game.game_id)
            for game in db[user.username].game_list
        ]
    )


def add_game(user: models.User, game_id, additional_authorized_users=[], data={}):
    initialize_user(user)

    db[user.username].add_game(Game(
        authorized_users=[user.username] + additional_authorized_users,
        data=data,
        game_id=game_id
    ))

    return True
