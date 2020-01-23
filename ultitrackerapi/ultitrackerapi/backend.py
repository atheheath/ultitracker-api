import psycopg2 as psql
import time

from abc import ABC
from typing import List
from ultitrackerapi import models
from ultitrackerapi import (
    NUM_CONNECTION_RETRIES,
    POSTGRES_USERNAME,
    POSTGRES_PASSWORD,
    POSTGRES_HOSTNAME,
    POSTGRES_PORT,
    POSTGRES_DATABASE,
)


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


class VizdbClient(object):
    def __init__(
        self,
        username=POSTGRES_USERNAME,
        password=POSTGRES_PASSWORD,
        hostname=POSTGRES_HOSTNAME,
        port=POSTGRES_PORT,
        database=POSTGRES_DATABASE,
        num_connection_retries=NUM_CONNECTION_RETRIES,
    ):
        self._username = username
        self._password = password
        self._hostname = hostname
        self._port = port
        self._database = database
        self._num_connection_retries = num_connection_retries
        self._conn = None

    def _establish_connection(self):
        if self._conn is not None:
            return

        for i in range(self._num_connection_retries):
            try:
                try:
                    self._conn = psql.connect(
                        user=self._username,
                        password=self._password,
                        host=self._hostname,
                        port=self._port,
                        database=self._database,
                    )
                except (Exception, psql.DatabaseError) as error:
                    print("Couldn't connect to database")
                    raise error
                except Exception as e:
                    raise e
            except Exception as e:
                if i == (self._num_connection_retries - 1):
                    raise e
                else:
                    time.sleep(1)

    def close_connection(self):
        if self._conn is not None:
            self._conn.close()

    def execute(self, commands):
        if self._conn is None:
            self._establish_connection()

        cursor = None
        result = None
        try:
            cursor = self._conn.cursor()
            if isinstance(commands, str):
                cursor.execute(commands)
            else:
                for command in commands:
                    cursor.execute(command)

            try:
                result = cursor.fetchall()
            except psql.ProgrammingError:
                """Happens when nothing to fetch"""
                pass

            cursor.close()
            self._conn.commit()
            return result

        except psql.DatabaseError as error:
            print("Could not complete the transaction")
            print(commands)
            raise error

        finally:
            if cursor is not None:
                cursor.close()
            self._conn.commit()


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


class PostgresBackend(Backend):
    def __init__(self, client: VizdbClient):
        self.client = client
