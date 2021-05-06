import asyncio

from discord import Embed

from libs.constants import support_info


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
        await self.ctx.send(embed=self.embed)
        await self.ctx.send(embed=support_info)
