# import boto3
import datetime
import json
import uuid

# from enum import Enum
# from pydantic import BaseConfig, BaseModel
# from typing import Dict, Set, Type, Optional
from typing import List
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
            logger.error(
                "Could not complete the transaction: {}".format(commands)
            )
            raise error

        finally:
            if cursor is not None:
                cursor.close()
            self._conn.commit()


def annotation_to_sql_values(annotation: models.Annotation):
    if isinstance(annotation, models.AnnotationPlayerBboxes):
        init_string = ""
        for i, bbox in enumerate(annotation.bboxes):
            if i > 0:
                init_string += ",\n"

            init_string += "('{img_id}', '{bbox}'{player_id})".format(
                img_id=annotation.img_id,
                bbox=(
                    (bbox.x1, bbox.y1),
                    (bbox.x2, bbox.y2),
                ),
                player_id=", {}".format("'{}'".format(bbox.player_id if bbox.player_id else "NULL"))
            )

        return init_string

    elif isinstance(annotation, models.AnnotationFieldLines):
        values = [
            "('{img_id}', '{line_coords}', '{line_type}')".format(
                img_id=annotation.img_id,
                line_coords=(
                    (coords.x1, coords.y1),
                    (coords.x2, coords.y2),
                ),
                line_type=coords.line_id.name,
            )
            for coords in annotation.line_coords
        ]

        values_string = ""
        for i, value in enumerate(values):
            if i > 0:
                values_string += ", "
            
            values_string += value

        return values_string

    elif isinstance(annotation, models.AnnotationGameplayState):
        return "('{img_id}', '{is_valid}')".format(
            img_id=annotation.img_id, is_valid=annotation.is_valid
        )


class SQLBackend(backend.Backend):
    def __init__(self, client: SQLClient):
        self.client = client

    def get_user(
        self, username: str, include_password: bool = False
    ) -> models.UserInDB:
        command = """
        SELECT {columns}
        FROM {table}
        WHERE 1=1
            AND username='{username}'
        """.format(
            columns=", ".join(sql_models.TableUsers.columns),
            table=sql_models.TableUsers.full_name,
            username=username,
        )

        result = self.client.execute(command)
        logger.debug("SQLBackend.get_user result: {}".format(result))

        if include_password:
            model = models.UserInDBwPass
        else:
            model = models.UserInDB

        if len(result) == 1:
            return model(**dict(zip(sql_models.TableUsers.columns, result[0])))
        elif len(result) > 1:
            logger.error(
                "SQLBackend.get_user returns multiple "
                "results for username: {}".format(username)
            )
            return model(**dict(zip(sql_models.TableUsers.columns, result[0])))
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
            table_values=tuple(
                [
                    user_id,
                    user.username,
                    user.email,
                    user.full_name,
                    salted_password,
                    user.disabled,
                ]
            ),
        )

        result = self.client.execute(command)
        logger.debug("SQLBackend.add_user result: {}".format(result))

        return True

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
            columns=", ".join([
                "games.{}".format(col) 
                for col in sql_models.TableGameMetadata.columns
            ]),
            table_name=sql_models.TableGameMetadata.full_name,
            authorization_name=sql_models.TableAuthorizationScheme.full_name,
            game_id=game_id,
            user_id=self.get_user(user.username).user_id,
        )

        result = self.client.execute(command)
        logger.debug("SQLBackend.get_game result: {}".format(result))

        if len(result) == 1:
            return models.GameResponse(
                **dict(zip(sql_models.TableGameMetadata.columns, result[0]))
            )
        elif len(result) > 1:
            logger.error(
                "SQLBackend.get_game returns multiple results "
                "for game_id: {}".format(game_id)
            )
            return models.GameResponse(
                **dict(zip(sql_models.TableGameMetadata.columns, result[0]))
            )
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
            columns=", ".join([
                "games.{}".format(col) 
                for col in sql_models.TableGameMetadata.columns
            ]),
            table_name=sql_models.TableGameMetadata.full_name,
            authorization_name=sql_models.TableAuthorizationScheme.full_name,
            user_id=self.get_user(user.username).user_id,
        )

        result = self.client.execute(command)
        logger.debug("SQLBackend.get_game result: {}".format(result))

        return models.GameListResponse(
            game_list=[
                models.GameResponse(
                    **dict(zip(sql_models.TableGameMetadata.columns, game))
                )
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
        video_key: str = "",
    ) -> bool:
        game_command = """
        INSERT INTO {table_name} {table_columns}
        VALUES {table_values}
        """.format(
            table_name=sql_models.TableGameMetadata.full_name,
            table_columns=(
                "(" 
                + ", ".join(sql_models.TableGameMetadata.columns) 
                + ")"
            ),
            table_values=tuple(
                [game_id, json.dumps(data), thumbnail_key, video_key]
            ),
        )

        auth_command = """
        INSERT INTO {table_name} {table_columns}
        VALUES {table_values}
        """.format(
            table_name=sql_models.TableAuthorizationScheme.full_name,
            table_columns=(
                "("
                + ", ".join(sql_models.TableAuthorizationScheme.columns)
                + ")"
            ),
            table_values=tuple(
                [game_id, self.get_user(user.username).user_id]
            ),
        )

        result = self.client.execute([game_command, auth_command])

        if result:
            return result
        else:
            return None

    def insert_annotation(
        self,
        user: models.User,
        img_id: str,
        annotation_table: models.AnnotationTable,
        annotation_data: dict,
    ) -> bool:
        current_time = datetime.datetime.utcnow()

        is_empty = False
        if annotation_table == models.AnnotationTable.player_bbox:
            table = sql_models.TablePlayerBbox
            model = models.AnnotationPlayerBboxes(**annotation_data)
            if len(model.bboxes) == 0:
                is_empty = True

        elif annotation_table == models.AnnotationTable.field_lines:
            table = sql_models.TableFieldLines
            model = models.AnnotationFieldLines(
                img_id=annotation_data['img_id'],
                line_coords=[
                    models.LineSegment(
                        x1=coord['x1'],
                        y1=coord['y1'],
                        x2=coord['x2'],
                        y2=coord['y2'],
                        line_id=models.LineId[coord['line_id']]
                    )
                    for coord in annotation_data['line_coords']
                ]
            )

        elif annotation_table == models.AnnotationTable.gameplay_state:
            table = sql_models.TableGameplayState
            model = models.AnnotationGameplayState(**annotation_data)

        else:
            raise ValueError("Invalid annotation_table: {}".format(annotation_table))

        annotation_transaction_command = """
            INSERT INTO {annotation_transaction_table} {annotation_transaction_columns}
            VALUES {annotation_transaction_values}
        """.format(
            annotation_transaction_table=sql_models.TableAnnotationTransaction.full_name,
            annotation_transaction_columns="("
            + ", ".join(sql_models.TableAnnotationTransaction.columns)
            + ")",
            annotation_transaction_values=(
                "(" + 
                ", ".join([
                    "'{}'".format(img_id),
                    "'{}'".format(current_time.strftime("%Y-%m-%d %H:%M:%S.%f")),
                    "'{}'".format(table.table_name),
                    "'{}'".format(models.AnnotationAction.submitted.name),
                ]) + 
                ")"
            ),
        )

        if is_empty:
            command = annotation_transaction_command
        else:
            command = """
                WITH insert_annotation_status AS (
                    {annotation_transaction_insert}
                )
                INSERT INTO {annotation_table} {annotation_columns}
                VALUES {annotation_values}
            """.format(
                annotation_transaction_insert=annotation_transaction_command,
                annotation_table=table.full_name,
                annotation_columns="(" + ", ".join(table.columns) + ")",
                annotation_values=annotation_to_sql_values(model),
            )

        result = self.client.execute(command)

        return result
