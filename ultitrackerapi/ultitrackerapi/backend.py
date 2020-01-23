# import psycopg2 as psql
# import time

from abc import ABC
from typing import List
from ultitrackerapi import models


class Backend(ABC):
    def get_user(self, username: str) -> models.User:
        pass

    def add_user(self, user: models.UserInDB) -> bool:
        pass

    def username_exists(self, username: str) -> bool:
        pass

    def authenticate_user(self, username: str, password: str) -> models.User:
        pass

    def get_game(self, game_id: str, user: models.User) -> models.GameResponse:
        pass

    def get_game_list(self, user: models.User) -> models.GameListResponse:
        pass

    def add_game(
        self,
        user: models.User,
        game_id: str,
        authorized_users: List[str] = [],
        data: dict = {},
    ) -> bool:
        pass


class InMemoryBackend(Backend):
    def __init__(self, game_db: dict = {}, user_db: dict = {}):
        self._game_db = game_db
        self._user_db = user_db

    def get_user(self, username: str) -> models.User:
        return self._user_db.get(username, None)

    def initialize_user(self, user: models.User):
        if user.username not in self._game_db:
            self._game_db[user.username] = models.GameList(game_list=[])

    def add_user(self, user: models.UserInDB) -> bool:
        if user.username in self._user_db:
            return False

        user.disabled = False

        self._user_db.update({user.username: user})

        return True

    def username_exists(self, username: str) -> bool:
        return username in self._user_db

    def get_game(self, game_id: str, user: models.User) -> models.GameResponse:
        self.initialize_user(user)

        game_response = None

        user_game_list = self._game_db[user.username]
        for game in user_game_list.game_list:
            if game_id == game.game_id:
                game_response = models.GameResponse(
                    data=game.data, game_id=game.game_id
                )
                break

        return game_response

    def get_game_list(self, user: models.User) -> models.GameListResponse:
        self.initialize_user(user)

        return models.GameListResponse(
            game_list=[
                models.GameResponse(data=game.data, game_id=game.game_id)
                for game in self._game_db[user.username].game_list
            ]
        )

    def add_game(
        self,
        user: models.User,
        game_id: str,
        additional_authorized_users: List[str] = [],
        data: dict = {},
    ) -> bool:
        self.initialize_user(user)

        self._game_db[user.username].add_game(
            models.Game(
                authorized_users=[user.username] + additional_authorized_users,
                data=data,
                game_id=game_id,
            )
        )

        return True
