import asyncio

from discord import Embed


class NoInfoSentToAlbie(Exception):
    """
    Looks like the Albion-Data Project didnt send anything to Poor Albie Bot, They might be under heavy load.
    Try searching again, if this error persists drop me discord message.
    """


class ItemNotFound(Exception):
    """
    Looks like the item could not be found ! Try searching again with different spelling.
    If this error persists drop me discord message from the link below.
    """

    def __init__(self, ctx):
        self.embed = Embed(color=0xff0000)
        self.embed.set_thumbnail(
            url="http://clipart-library.com/images/kTMK4787c.jpg")
        self.embed.add_field(name="Item Not Found",
                             value="Looks like the item could not be found ! Try searching again with different spelling."
                                   " If this error persists drop me discord message from the link below.",
                             inline=False)
        self.ctx = ctx
        self.loop = asyncio.get_running_loop()
        self.loop.create_task(self.send_discord_msg())

    async def send_discord_msg(self):
        self.embed.set_footer(text="💬 Want to help Improve the bot ? Go to: github.com/GraciousGpal/Albie")
        await self.ctx.send(embed=self.embed)


class NoHistoryDataAvailable(Exception):
    """
    Looks like there is no History data available for this Item.
    If this error persists drop me discord message from the link below.
    """

    def __init__(self, ctx):
        self.embed = Embed(color=0xff0000)
        self.ctx = ctx
        self.embed.colour = 0xFF0000
        self.embed.add_field(name="No History Data Available !",
                             value="Looks like there is no History data available for this Item,"
                                   " Consider contributing to the albion data client project,"
                                   " buy downloading their client and running it while you play the game."
                                   " It uploads all item prices for everyone to use when you browse the marketplace.",
                             inline=False)
        self.loop = asyncio.get_running_loop()
        self.loop.create_task(self.send_discord_msg())

    async def send_discord_msg(self):
        self.embed.set_footer(text="💬 Want to help Improve the bot ? Go to: github.com/GraciousGpal/Albie")
        await self.ctx.send(embed=self.embed)
