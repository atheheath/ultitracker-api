import argparse
import psycopg2 as psql

from passlib.hash import pbkdf2_sha256
from ultitrackerapi import get_backend, models, sql_backend, sql_models


def initialize_schema(client: sql_backend.SQLClient):
    create_schema_command = """
    CREATE SCHEMA ultitracker
    """
    client.execute([
        create_schema_command
    ])


def initialize_tables(client: sql_backend.SQLClient):
    initialization_order = [
        sql_models.TableUsers,
        sql_models.TableGameMetadata,
        sql_models.TableAuthorizationScheme,
        sql_models.TableImgLocation,
        sql_models.TablePlayerBbox,
        sql_models.TableFieldLines,
        sql_models.TableCameraAngle,
        sql_models.TableAnnotationTransaction,
    ]
    for table in initialization_order:
        # try to initialize tables if not made yet
        try:
            client.execute(table.create_commands)
        except psql.errors.DuplicateObject:
            pass
        except psql.errors.DuplicateTable:
            pass
        except Exception as e:
            print("Couldn't initialize tables")
            raise e


def main():
    # parser = argparse.ArgumentParser()

    client = sql_backend.SQLClient()

    initialize_schema(client)
    initialize_tables(client)

    backend = get_backend()

    backend.add_user(
        models.User(
            username="test",
            email="test@test.com",
            full_name="Jane Doe"
        ),
        salted_password=pbkdf2_sha256.hash("test"),
    )

    backend.add_game(
        user=backend.get_user(username="test"),
        game_id="test_vid_1.mp4",
        data={
            "home": "Team 1",
            "away": "Team 2",
            "date": "2019-10-31",
            "length": "00:00:10",
            "bucket": "ultitracker-videos-test",
            "name": "Chicago",
        },
        thumbnail_key="chicago.jpeg",
        video_key="test_vid_1.mp4",
    )

    backend.add_game(
        user=backend.get_user(username="test"),
        game_id="test_vid_2",
        data={
            "home": "Team 1",
            "away": "Team 3",
            "date": "2019-11-01",
            "length": "00:00:10",
            "bucket": "ultitracker-videos-test",
            "name": "Madison",
        },
        thumbnail_key="madison.jpeg",
        video_key="test_vid_2.mp4",
    )


if __name__ == "__main__":
    main()