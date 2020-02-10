# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
import os
from difflib import get_close_matches

import discord
from discord.ext import commands

logg = logging.getLogger(__name__)


class Autorole(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.modname = __name__
        self.Description = "Automatically Sets a Role to incoming Members"
        self.ez = json.load(open('data/AutoRole/AutoRole.json'))
        self.data = self.ez.copy()

    @commands.command(pass_context=True, description="Automatically Sets a Role", hidden=True)
    async def autorole(self, ctx, role):
        """
        Automatically assigns the specified role to a new member.
        :param ctx:
        :param role:
        :return:
        """
        rolelist = []
        if ctx.message.author.guild_permissions.administrator:
            roles = ctx.message.author.guild.roles
            for rolea in roles:
                rolelist.append(rolea.name)
            match = get_close_matches(role, rolelist)
            found = discord.utils.get(ctx.message.guild.roles, name=match[0])
            if found is not None:
                self.data[str(ctx.message.author.guild.id)] = found.id
                with open('data/AutoRole/AutoRole.json', 'w') as outfile:
                    json.dump(self.data, outfile, indent=4)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not self.data:
            logg.error("Warning Dict Empty for AutoRole!")
            self.data = json.load(open('data/AutoRole/AutoRole.json'))
        autorole = self.data[str(member.guild.id)]
        found = discord.utils.get(member.guild.roles, id=autorole)
        logg.info("Adding {} to {}".format(found.name, member.name))
        await member.add_roles(found, reason="Joined the Server")
        logg.info("Added {} to {}".format(found.name, member.name))


def setup(bot):
    if not os.path.exists("data/AutoRole"):
        os.makedirs("data/AutoRole")
    fn = "data/AutoRole/AutoRole.json"
    data = {}
    try:
        file = open(fn, 'r')
    except IOError:
        with open(fn, 'w') as outfile:
            json.dump(data, outfile, indent=4)
    bot.add_cog(Autorole(bot))
