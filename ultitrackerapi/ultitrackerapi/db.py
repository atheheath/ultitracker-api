from .auth import User
from pydantic import BaseModel
from typing import Dict, List


class Game(BaseModel):
    authorized_users: List[str]
    data: Dict


class GameResponse(BaseModel):
    data: Dict


class GameList(BaseModel):
    game_list: List[Game]


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
                    "length": "02:21:34"
                }
            ),
            Game(
                authorized_users=["test"],
                data={
                    "home": "Team 1",
                    "away": "Team 3",
                    "date": "2019-11-01",
                    "thumbnail": "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.ytimg.com%2Fvi%2FSnidMSsk14Q%2Fmaxresdefault.jpg&f=1&nofb=1",
                    "length": "01:51:25"
                }
            )
        ]
    )
}


def get_game_list(user: User):
    if user.username not in db:
        db[user.username] = GameList(game_list=[])

    return GameListResponse(
        game_list=[
            GameResponse(data=game.data)
            for game in db[user.username].game_list
        ]
    )

"""
To implement authorized S3 files, check out this stack overflow
https://stackoverflow.com/a/34918921
"""