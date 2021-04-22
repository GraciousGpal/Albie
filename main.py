import logging
import os

from discord import Game
from discord.ext import commands

# Load config.ini
current_path = os.path.dirname(os.path.realpath(__file__))

command_prefix = '+'  # TODO revert back to .

client = commands.Bot(
    command_prefix=commands.when_mentioned_or(*command_prefix), case_insensitive=True
)

# Set up logging to discord.log
logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)


# keep_alive.keep_alive()


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
                print(f"Loading...{filename[:-3]}")
                client.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded {filename[:-3]}")
    except Exception as e:
        print(e)

    # Activity to 'Ready'
    await client.change_presence(activity=Game("Ready"))

    # Login message in console
    print(f"Logged in as {client.user}.\nConnected to:")
    for (i, guild) in enumerate(client.guilds):

        # Only list up to 10 guilds
        print(guild.name)
        if i == 9:
            print(f"and {len(client.guilds) - 10} other guilds.")
            break


@client.command(hidden=True)
async def extension(ctx, option, extension):
    """Reload, load, or unload extensions.

    - Usage: <command-prefix> extension <option> <cog's name>
    - <option> : load, unload, reload
    - Only allowable if user is adminUser.
    """

    # Check if user is in adminUsers
    if str(ctx.author.id) not in [str(138684247853498369)]:
        await ctx.send(f"You do not have permission to {option} extensions.")
        return
    # hello
    try:
        if option == "reload":
            client.reload_extension(f"cogs.{extension}")
        elif option == "load":
            client.load_extension(f"cogs.{extension}")
        elif option == "unload":
            client.unload_extension(f"cogs.{extension}")

        # Prompt usage method if option is wrong
        else:
            await ctx.send(
                f"Usage: `{command_prefix[0]}extension <option> <extension>`\nOptions: `reload, load, unload`"
            )
            return

    except Exception:
        await ctx.send(f"{extension} extension {option} FAILED.")
        return

    # Success message
    await ctx.send(f"{extension} extension {option.upper()}ED.")


# Copy from your Discord developer portal
token = "NDY0Mzk2NzkxODk1NTU2MTA3.Wz4FNw.-47uKHe8KP6ifW62-8KYBQhTwMo"
client.run(token)
