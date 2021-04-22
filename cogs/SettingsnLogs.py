from discord.ext import commands

from libs.db import create_connection


def create_prefix_table():
    pass


def get_table(name):
    pass


def write_to_table(name):
    pass


class Error:
    def __init__(self, client):
        self.client = client
        pass


class Prefix(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.sqlite_prefix = None
        self.connect()
        self.create_table()

    def connect(self):
        self.sqlite_prefix = create_connection("data/prefix.sqlite")

    def create_table(self):
        sql_c = "CREATE TABLE IF NOT EXISTS prefix (id int PRIMARY KEY,prefix string NOT NULL) WITHOUT ROWID;"
        try:
            c = self.sqlite_prefix.cursor()
            c.execute(sql_c)
        except Exception as e:
            print(e)
        finally:
            self.sqlite_prefix.commit()

    def get(self, server_id):
        pass

    def write(self, server_id, prefix):
        pass


class Settings(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.sqlite = create_connection("data/settings_data.sqlite")


def setup(client):
    client.add_cog(Prefix(client))
    client.add_cog(Settings(client))
