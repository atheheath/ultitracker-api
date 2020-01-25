import boto3
import datetime
import json
import uuid

from enum import Enum
from pydantic import BaseConfig, BaseModel
from typing import Dict, List, Set, Type, Optional
from ultitrackerapi import backend, get_s3Client, models, sql_models

import psycopg2 as psql
import time
from ultitrackerapi import (
    get_logger,
    NUM_CONNECTION_RETRIES,
    POSTGRES_USERNAME,
    POSTGRES_PASSWORD,
    POSTGRES_HOSTNAME,
    POSTGRES_PORT,
    POSTGRES_DATABASE,
)

# get logger
logger = get_logger(__name__, level="DEBUG")

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
                    logger.error("Couldn't connect to database")
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
            logger.error("Could not complete the transaction: {}".format(commands))
            raise error

        finally:
            if cursor is not None:
                cursor.close()
            self._conn.commit()


class SQLBackend(backend.Backend):
    def __init__(self, client: SQLClient):
        self.client = client

    def get_user(self, username: str, include_password: bool = False) -> models.UserInDB:
        command = """
        SELECT {columns}
        FROM {table}
        WHERE 1=1
            AND username='{username}'
        """.format(
            columns=", ".join(sql_models.TableUsers.columns),
            table=sql_models.TableUsers.full_name,
            username=username
        )

        result = self.client.execute(command)
        logger.debug("SQLBackend.get_user result: {}".format(result))
        
        if include_password:
            model = models.UserInDBwPass
        else:
            model = models.UserInDB
        
        if len(result) == 1:
            return model(**dict(
                zip(sql_models.TableUsers.columns, result[0])
            ))
        elif len(result) > 1:
            logger.error("SQLBackend.get_user returns multiple results for username: {}".format(username))
            return model(**dict(
                zip(sql_models.TableUsers.columns, result[0])
            ))
        else:
            return None

    def add_user(self, user: models.User, salted_password: str) -> bool:
        if self.get_user(user.username):
            return False

        user.disabled = False
        user_id = str(uuid.uuid4())

        command = """
        INSERT INTO {table_name} {table_columns}
        VALUES {table_values}
        """.format(
            table_name=sql_models.TableUsers.full_name,
            table_columns="(" + ", ".join(sql_models.TableUsers.columns) + ")",
            table_values=tuple([
                user_id,
                user.username,
                user.email,
                user.full_name,
                salted_password,
                user.disabled
            ])
        )

        result = self.client.execute(command)
        logger.debug("SQLBackend.add_user result: {}".format(result))

        return result

    def username_exists(self, username: str) -> bool:
        if self.get_user(username) is not None:
            return True
        else:
            return False

    def get_game(self, game_id: str, user: models.User) -> models.GameResponse:
        command = """
        SELECT {columns}
        FROM {table_name} games
        JOIN {authorization_name} auth
            ON games.game_id = auth.game_id
        WHERE 1=1
            AND games.game_id='{game_id}'
            AND auth.user_id='{user_id}'
        """.format(
            columns=", ".join(["games.{}".format(col) for col in sql_models.TableGameMetadata.columns]),
            table_name=sql_models.TableGameMetadata.full_name,
            authorization_name=sql_models.TableAuthorizationScheme.full_name,
            game_id=game_id,
            user_id=self.get_user(user.username).user_id
        )

        result = self.client.execute(command)
        logger.debug("SQLBackend.get_game result: {}".format(result))

        if len(result) == 1:
            return models.GameResponse(**dict(
                zip(sql_models.TableGameMetadata.columns, result[0])
            ))
        elif len(result) > 1:
            logger.error("SQLBackend.get_game returns multiple results for game_id: {}".format(game_id))
            return models.GameResponse(**dict(
                zip(sql_models.TableGameMetadata.columns, result[0])
            ))
        else:
            return None

    def get_game_list(self, user: models.User) -> models.GameListResponse:
        command = """
        SELECT {columns}
        FROM {table_name} games
        JOIN {authorization_name} auth
            ON games.game_id = auth.game_id
        WHERE 1=1
            AND auth.user_id='{user_id}'
        """.format(
            columns=", ".join(["games.{}".format(col) for col in sql_models.TableGameMetadata.columns]),
            table_name=sql_models.TableGameMetadata.full_name,
            authorization_name=sql_models.TableAuthorizationScheme.full_name,
            user_id=self.get_user(user.username).user_id
        )

        result = self.client.execute(command)
        logger.debug("SQLBackend.get_game result: {}".format(result))

        return models.GameListResponse(
            game_list=[
                models.GameResponse(**dict(
                    zip(sql_models.TableGameMetadata.columns, game)
                ))
                for game in result
            ]
        )

    def add_game(
        self,
        user: models.User,
        game_id: str,
        authorized_users: List[str] = [],
        data: dict = {},
        thumbnail_key: str = "",
        video_key: str = ""
    ) -> bool:
        game_command = """
        INSERT INTO {table_name} {table_columns}
        VALUES {table_values}
        """.format(
            table_name=sql_models.TableGameMetadata.full_name,
            table_columns="(" + ", ".join(sql_models.TableGameMetadata.columns) + ")",
            table_values=tuple([
                game_id,
                json.dumps(data),
                thumbnail_key,
                video_key
            ])
        )

        auth_command = """
        INSERT INTO {table_name} {table_columns}
        VALUES {table_values}
        """.format(
            table_name=sql_models.TableAuthorizationScheme.full_name,
            table_columns="(" + ", ".join(sql_models.TableAuthorizationScheme.columns) + ")",
            table_values=tuple([
                game_id,
                self.get_user(user.username).user_id
            ])
        )

        result = self.client.execute([
            game_command,
            auth_command
        ])

        if result:
            return result
        else:
            return None