from discord.ext import commands
import discord

class Roles(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def on_member_join(self, member):
        role = discord.utils.get(member.server.roles, id=675137499844182036)
        await self.client.add_roles(member, role)


def setup(client):
    client.add_cog(Roles(client))
