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
        self.react_data = json.load(open('data/AutoRole/ReactRole.json'))
        self.data = self.ez.copy()

    @commands.command(pass_context=True, description="Automatically Sets a Role when user joins")
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

    @commands.command(pass_context=True, description="Automatically Sets a Role")
    async def reactrole(self, ctx, msgid, role):
        errs = []
        role_s1 = role.split(",")
        rolelist = [role.name for role in ctx.message.author.guild.roles]
        xx = ctx.message
        self.react_data[msgid] = {}
        for text in role_s1:
            emoji = text.split('-')[0]
            role = text.split('-')[1]

            try:
                match = get_close_matches(role, rolelist)
                if len(match) != 0:
                    found = discord.utils.get(ctx.message.guild.roles, name=match[0])
                    self.react_data[msgid][found.id] = emoji
                else:
                    await ctx.send(f"{role} not found in the role list")
            except Exception as e:
                errs.append(e)
                print(e)
        if len(errs) == 0:
            with open('data/AutoRole/ReactRole.json', 'w', encoding='utf-8') as outfile:
                json.dump(self.react_data, outfile, indent=4)
        msg = await ctx.fetch_message(msgid)
        print(msg.reactions)
        for reaction in msg.reactions:
            try:
                for keys in self.react_data[msgid]:
                    if reaction.emoji in self.react_data[msgid][keys]:
                        role = keys
                        print(f'-----------{role} , {reaction.emoji}')

                        users = await reaction.users().flatten()
                        for user in users:
                            member = discord.utils.get(ctx.guild.members, id=user.id)
                            if member:
                                found = discord.utils.get(ctx.guild.roles, id=role)
                                logg.info("Adding {} to {}".format(found.name, user.name))
                                try:
                                    await member.add_roles(found, reason=f"Reacted to {reaction.emoji} emoji")
                                except AttributeError:
                                    pass
            except Exception as e:
                logg.error("errrrrrrrrrrror", e)

        '''
        if ctx.message.author.guild_permissions.administrator:
            match = get_close_matches(role, rolelist)
            found = discord.utils.get(ctx.message.guild.roles, name=match[0])'''

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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not self.react_data:
            logg.error("Warning Dict Empty for ReactRole!")
            self.react_data = json.load(open('data/AutoRole/ReactRole.json'))
        for keys in self.react_data[str(payload.message_id)]:
            if str(payload.emoji) in self.react_data[str(payload.message_id)][keys]:
                guild = self.bot.get_guild(int(payload.guild_id))
                found = discord.utils.get(guild.roles, id=int(keys))
                found2 = discord.utils.get(guild.members, id=int(payload.user_id))
                logg.info("Adding {} to {}".format(found.name, found2.name))
                await found2.add_roles(found, reason="Joined the Server")
                logg.info("Added {} to {}".format(found.name, found2.name))


def setup(bot):
    if not os.path.exists("data/AutoRole"):
        os.makedirs("data/AutoRole")
    fn = "data/AutoRole/AutoRole.json"
    fn1 = "data/AutoRole/ReactRole.json"
    data = {}
    try:
        file = open(fn, 'r')
        file1 = open(fn1, 'r')
    except IOError:
        with open(fn, 'w') as outfile:
            json.dump(data, outfile, indent=4)
        with open(fn1, 'w') as outfile:
            json.dump(data, outfile, indent=4)
    bot.add_cog(Autorole(bot))
