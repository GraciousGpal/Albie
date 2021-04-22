from discord.ext import commands

class Prefix(commands.Cog):
    def __init__(self, client):
        self.client = client





def setup(client):
    client.add_cog(Prefix(client))