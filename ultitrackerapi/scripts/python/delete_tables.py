from ultitrackerapi import sql_backend


def delete_schema(client: sql_backend.SQLClient):
    create_schema_command = """
    DROP SCHEMA ultitracker CASCADE
    """
    client.execute([
        create_schema_command
    ])


def main():
    # parser = argparse.ArgumentParser()

    client = sql_backend.SQLClient()

    delete_schema(client)


if __name__ == "__main__":
    main()