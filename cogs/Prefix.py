import logging

from discord import Embed
from discord.ext import commands

from libs.db import create_connection

log = logging.getLogger(__name__)


def is_guild_owner():
    def predicate(ctx):
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id

    return commands.check(predicate)


class Prefix(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.sqlite_prefix = None
        self.client.command_prefix = self.get_prefix
        self.connect()
        self.create_table()

    @is_guild_owner()
    @commands.command()
    async def setPrefix(self, ctx, prefix):
        """
        Choose the way the bot can be called,
        this command sets a prefix that the bot listens for. e.g. .prefix +
        will change the way the bot is called when using commands to +command...
        Note: Only Guild Owner can change the Prefix.
        Args:
            prefix ([string]): [The Prefix the bot is called with]
        """
        try:
            log.info(f"{ctx.prefix}{ctx.invoked_with} {ctx.message.content}")
        except TypeError:
            pass
        if ctx.guild is not None:
            pref = self.get(ctx.guild.id)
        else:
            pref = self.get(ctx.channel.id)

        pref = pref if pref is not None else "."

        if prefix.isnumeric():
            embed = Embed(color=0xFF0000)
            embed.add_field(
                name="Cannot use a number for prefix!",
                value=f"Example usage: {str(pref)}prefix <your prefix> ",
                inline=False,
            )
            await ctx.send(embed=embed)
            return

        if prefix != "" or None:
            self.write(ctx.guild.id, str(prefix))
            embed = Embed(color=0x98FB98)
            embed.add_field(
                name=f"Albie Bot Prefix Set to `{prefix}`",
                value=f"All future commands can only be called with this `{prefix}` Prefix e.g. {prefix}help ",
                inline=False,
            )
            await ctx.send(embed=embed)
        else:
            embed = Embed(color=0xFF0000)
            embed.add_field(
                name="Invalid Input",
                value=f"Example usage: {str(pref)}prefix <your prefix>",
                inline=False,
            )
            await ctx.send(embed=embed)

    def get_prefix(self, ctx, message):  ##first we define get_prefix
        if message.guild is not None:
            pref = self.get(message.guild.id)
        else:
            pref = self.get(message.channel.id)
        return pref if pref is not None else "."

    def connect(self):
        self.sqlite_prefix = create_connection("data/prefix.sqlite")

    def create_table(self):
        sql_c = "CREATE TABLE IF NOT EXISTS prefix (id int PRIMARY KEY,prefix string NOT NULL) WITHOUT ROWID;"
        try:
            c = self.sqlite_prefix.cursor()
            c.execute(sql_c)
        except Exception as e:
            log.error(e)
        finally:
            self.sqlite_prefix.commit()
            c.close()

    def get(self, server_id):
        try:
            c = self.sqlite_prefix.cursor()
            row = c.execute("SELECT prefix FROM prefix WHERE id = ?", (int(server_id),))
            prefix = [x[0] for x in row][0]
            return prefix
        except IndexError:
            return None
        finally:
            c.close()

    def write(self, server_id, prefix):
        try:
            c = self.sqlite_prefix.cursor()
            c.execute(
                "REPLACE INTO prefix (id, prefix) VALUES(?, ?);",
                (int(server_id), prefix),
            )
        except Exception as e:
            log.error(e)
        finally:
            self.sqlite_prefix.commit()
            c.close()


def setup(client):
    client.add_cog(Prefix(client))


def teardown(client):
    log.info("Unloading Prefix...")
    client.command_prefix = commands.when_mentioned_or(*".")


if __name__ == "__main__":
    # Quick Testing.
    p = Prefix("blank")
    log.info("WRITING 99000 ", p.write(99000, "+"))
    assert None is p.write(99000, "+")
    log.info("GETTING 99000 ", p.get(99000))
    assert p.get(99000) == "+"
