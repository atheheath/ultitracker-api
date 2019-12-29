from pydantic import BaseModel
from typing import Dict, List
from ultitrackerapi import models


class Game(BaseModel):
    authorized_users: List[str]
    data: Dict
    game_id: str


class GameResponse(BaseModel):
    data: Dict
    game_id: str


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
                    "thumbnail": "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.ytimg.com%2Fvi%2FaNCuZJe1zQk%2Fmaxresdefault.jpg&f=1&nofb=1",
                    "length": "02:21:34",
                },
                game_id="00000001",
            ),
            Game(
                authorized_users=["test"],
                data={
                    "home": "Team 1",
                    "away": "Team 3",
                    "date": "2019-11-01",
                    "thumbnail": "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.ytimg.com%2Fvi%2FSnidMSsk14Q%2Fmaxresdefault.jpg&f=1&nofb=1",
                    "length": "01:51:25",
                },
                game_id="00000002",
            ),
        ]
    )
}


def initialize_user(user: models.User):
    if user.username not in db:
        db[user.username] = GameList(game_list=[])


def get_game(game_id: str, user: models.User):
    initialize_user(user)

    game_response = GameResponse(data={}, game_id="")

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



"""
To implement authorized S3 files, check out this stack overflow
https://stackoverflow.com/a/34918921
"""
# s3Client.generate_presigned_url(
#     "get_object",
#     Params={
#         "Bucket": "ultitracker-videos",
#         "Key": "Men's Highlight Reel--2019 National Championships-zt8jq7EaWxw.mp4"
#     },
#     ExpiresIn=60*60*2
# )