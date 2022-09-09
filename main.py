import asyncio
import logging
import os

from discord import Game, Intents
from discord.ext import commands

# Load config.ini
current_path = os.path.dirname(os.path.realpath(__file__))

# Set up logging to discord.log
logFormatter = logging.Formatter("%(asctime)s [%(name)s] [%(levelname)s]  %(message)s")
log = logging.getLogger()
log.setLevel(logging.INFO)
file_handler = logging.FileHandler(filename="data/logs/discord.log", encoding="utf-8", mode="w")
log.addHandler(file_handler)
# Set up logging to Console
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
log.addHandler(consoleHandler)


class Server(commands.AutoShardedBot):
    def __init__(self, command_prefix, intents, *args, **kwargs):
        super().__init__(command_prefix=command_prefix, intents=intents, *args, **kwargs)


client = Server(command_prefix='.', intents=Intents.default(), case_insensitive=True)


async def get_total_users() -> int:
    count = 0
    for _guild in client.guilds:
        for _ in _guild.members:
            count += 1
    return count


async def update_albie_presence(client):
    while True:
        no_of_users = await get_total_users()
        no_of_guilds = len(client.guilds)
        await client.change_presence(
            activity=Game(f"Albion with {no_of_guilds} guilds and serving {no_of_users}+ users"))
        await asyncio.sleep(360)


@client.event
async def on_ready():
    """Things to do when bot is ready.

    - Load all cogs in folder /cogs.
    - Change activity to 'Ready'.
    - Login messages in console:
        Logged in username.
        List of joined guilds.
    """

    # Remove default help command (before loading of cogs)
    # client.remove_command("help")

    # Load cogs in folder /cogs
    try:
        for filename in os.listdir(current_path + "/cogs"):
            if filename.endswith(".py"):
                await client.load_extension(f"cogs.{filename[:-3]}")
                log.info(f"Loaded: [{filename[:-3]}]")
    except Exception as e:
        log.error(e)

    # After everything is loaded sync commands
    await client.tree.sync()

    # Activity to 'Albie Stats'
    client.loop.create_task(update_albie_presence(client))

    # Login message in console
    log.info(f"Logged in as {client.user}.\nConnected to:")
    for (i, guild) in enumerate(client.guilds):

        # Only list up to 10 guilds
        log.info(guild.name)
        if i == 9:
            log.info(f"and {len(client.guilds) - 10} other guilds.")
            break


if __name__ == "__main__":
    token = os.environ['DISCORDAPI']
    client.run(token)
