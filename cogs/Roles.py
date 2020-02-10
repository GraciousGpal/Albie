from discord.ext import commands


class Roles(commands.Cog):
    def __init__(self, client):
        self.client = client

    @bot.event
    async def on_member_join(member):
        role = discord.utils.get(member.server.roles, id="<role ID>")
        await bot.add_roles(member, role)

def setup(client):
    client.add_cog(Roles(client))
