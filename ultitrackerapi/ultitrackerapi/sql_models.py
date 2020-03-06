# import boto3
import datetime

# from enum import Enum
# from pydantic import BaseConfig, BaseModel
from typing import Dict, Set, Optional
from ultitrackerapi import models, POSTGRES_SCHEMA


TableUsers = models.Table(
    table_name="users",
    schema_name=POSTGRES_SCHEMA,
    columns=[
        "user_id",
        "username",
        "email",
        "full_name",
        "salted_password",
        "disabled",
    ],
    # column_types=[str, str, str, str, str, Optional[bool]],
    column_types=[str, str, str, str, str, bool],
    create_commands=[
        """
        CREATE TABLE {full_name} (
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            full_name TEXT NOT NULL,
            salted_password TEXT NOT NULL,
            disabled BOOL,
            PRIMARY KEY (user_id)
        )
        """.format(full_name=models.Table.construct_full_name(POSTGRES_SCHEMA, "users"))
    ],
)


TableGameMetadata = models.Table(
    table_name="game_metadata",
    schema_name=POSTGRES_SCHEMA,
    columns=[
        "game_id",
        "data",
        "thumbnail_key",
        "video_key",
    ],
    column_types=[
        str,
        dict,
        str,
        str
    ],
    create_commands=[
        """
        CREATE TABLE {full_name} (
            game_id TEXT,
            data JSONB NOT NULL,
            thumbnail_key TEXT,
            video_key TEXT,
            PRIMARY KEY (game_id)
        )
        """.format(full_name=models.Table.construct_full_name(POSTGRES_SCHEMA, "game_metadata"))
    ],
)


TableAuthorizationScheme = models.Table(
    table_name="authorization_scheme",
    schema_name=POSTGRES_SCHEMA,
    columns=["game_id", "user_id"],
    column_types=[str, str],
    create_commands=[
        """
        CREATE TABLE {full_name} (
            game_id TEXT REFERENCES {game_metadata_full_name}(game_id),
            user_id TEXT REFERENCES {users_full_name}(user_id)
        )
        """.format(
            full_name=models.Table.construct_full_name(POSTGRES_SCHEMA, "authorization_scheme"),
            game_metadata_full_name=TableGameMetadata.full_name,
            users_full_name=TableUsers.full_name
        )
    ],
)


TableImgLocation = models.Table(
    table_name="img_location",
    schema_name=POSTGRES_SCHEMA,
    columns=["img_id", "img_raw_path", "img_type", "img_metadata", "game_id", "frame_number"],
    column_types=[str, str, models.ImgEncoding, dict, str, int],
    create_commands=[
        """
        CREATE TYPE img_encoding AS ENUM('jpeg', 'png', 'tiff')
        """,
        """
        CREATE TABLE {full_name} (
            img_id TEXT NOT NULL,
            img_raw_path TEXT NOT NULL,
            img_type img_encoding NOT NULL,
            img_metadata JSONB NOT NULL,
            game_id TEXT REFERENCES {game_metadata_full_name}(game_id),
            frame_number INTEGER,
            PRIMARY KEY (img_id)
        )
        """.format(
            full_name=models.Table.construct_full_name(POSTGRES_SCHEMA, "img_location"),
            game_metadata_full_name=TableGameMetadata.full_name
        ),
    ],
)

TablePlayerBbox = models.Table(
    table_name="player_bbox",
    schema_name=POSTGRES_SCHEMA,
    columns=["img_id", "bbox", "player_id"],
    column_types=[str, models.Box, str],
    create_commands=[
        """
        CREATE TABLE {full_name} (
            img_id TEXT REFERENCES {img_location_full_name}(img_id),
            bbox BOX NOT NULL,
            player_id TEXT
        )
        """.format(
            full_name=models.Table.construct_full_name(POSTGRES_SCHEMA, "player_bbox"),
            img_location_full_name=TableImgLocation.full_name
        )
    ],
)

TableFieldLines = models.Table(
    table_name="field_lines",
    schema_name=POSTGRES_SCHEMA,
    columns=["img_id", "line_coords", "line_type"],
    column_types=[str, models.LineSegment, models.LineId],
    create_commands=[
        """
        CREATE TYPE line_id AS ENUM ('top_sideline', 'left_back_endzone', 'left_front_endzone', 'right_front_endzone', 'right_back_endzone', 'bottom_sideline')
        """,
        """
        CREATE TABLE {full_name} (
            img_id TEXT REFERENCES {img_location_full_name}(img_id),
            line_coords lseg NOT NULL,
            line_type line_id NOT NULL,
            PRIMARY KEY (img_id, line_type)
        )
        """.format(
            full_name=models.Table.construct_full_name(POSTGRES_SCHEMA, "field_lines"),
            img_location_full_name=TableImgLocation.full_name
        ),
    ],
)

TableGameplayState = models.Table(
    table_name="gameplay_state",
    schema_name=POSTGRES_SCHEMA,
    columns=["img_id", "is_valid"],
    column_types=[str, bool],
    create_commands=[
        """
        CREATE TABLE {full_name}(
            img_id TEXT REFERENCES {img_location_full_name}(img_id),
            is_valid BOOLEAN NOT NULL,
            PRIMARY KEY (img_id)
        )
        """.format(
            full_name=models.Table.construct_full_name(POSTGRES_SCHEMA, "gameplay_state"),
            img_location_full_name=TableImgLocation.full_name
        )
    ],
)

TableAnnotationTransaction = models.Table(
    table_name="annotation_transaction",
    schema_name=POSTGRES_SCHEMA,
    columns=[
        "img_id",
        "timestamp",
        "table_ref",
        "action"
    ],
    column_types=[str, datetime.datetime, models.AnnotationTable, models.AnnotationAction],
    create_commands=[
        """
        CREATE TYPE annotation_table AS ENUM ('player_bbox', 'field_lines', 'gameplay_state')
        """,
        """
        CREATE TYPE annotation_action AS ENUM ('sent', 'submitted')
        """,
        """
        CREATE TABLE {full_name}(
            img_id TEXT REFERENCES {img_location_full_name}(img_id),
            timestamp TIMESTAMP,
            table_ref annotation_table,
            action annotation_action,
            PRIMARY KEY (img_id, timestamp, table_ref)
        )
        """.format(
            full_name=models.Table.construct_full_name(POSTGRES_SCHEMA, "annotation_transaction"),
            img_location_full_name=TableImgLocation.full_name
        ),
    ],
)


# vizdb = models.Database(
#     name="ultitracker",
#     tables=set(
#         [
#             TableImgLocation,
#             TablePlayerBbox,
#             TableFieldLines,
#             TableGameplayState,
#             TableAnnotationAction,
#             TableGameMetadata,
#             TableUsers,
#             TableAuthorizationScheme,
#         ]
#     ),
# )