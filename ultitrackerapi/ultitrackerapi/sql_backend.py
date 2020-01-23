import boto3
import datetime

from enum import Enum
from pydantic import BaseConfig, BaseModel
from typing import Dict, List, Set, Type, Optional
from ultitrackerapi import backend, get_s3Client, models, sql_models

import psycopg2 as psql
import time
from ultitrackerapi import (
    NUM_CONNECTION_RETRIES,
    POSTGRES_USERNAME,
    POSTGRES_PASSWORD,
    POSTGRES_HOSTNAME,
    POSTGRES_PORT,
    POSTGRES_DATABASE,
)

# start s3 client
s3Client = get_s3Client()


class SQLClient(object):
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


class SQLBackend(backend.Backend):
    def __init__(self, client: SQLClient):
        self.client = client

    def get_user(self, username: str) -> models.User:
        command = """
        SELECT username, email, full_name 
        FROM {table}
        WHERE 1=1
            AND username={username}
        """.format(
            table=sql_models.TableUsers.full_name,
            username=username
        )

        result = self.client.execute(command)
        if result:
            return result
        else:
            return None

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