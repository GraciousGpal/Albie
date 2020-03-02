from discord.ext import commands
import io
import json
import discord

import PIL
import jellyfish as j
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests as r
import seaborn as sns
from PIL import Image
from datetime import datetime
from numpy import nan


class Market(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.base_url = "https://www.albion-online-data.com/api/v2/stats/history/"
        self.base_url_current = "https://www.albion-online-data.com/api/v2/stats/prices/"
        self.locations = ['Thetford', 'Martlock', 'Caerleon', 'Lymhurst', 'Bridgewatch', 'FortSterling',
                          'BlackMarket']
        self.scale = 6
        self.dict = json.load(open("data/item_data.json", 'r', encoding='utf-8'))
        self.item_list = [item['LocalizedNames']["EN-US"] for item in self.dict if item['LocalizedNames'] is not None]
        self.id_list = [item['UniqueName'] for item in self.dict]
        self.city_colours = {'Thetford': 'purple', 'Martlock': 'skyblue', 'Caerleon': 'red', 'Lymhurst': 'green',
                             'Bridgewatch': 'orange', 'Fort Sterling': 'grey', 'Black Market': 'white'}

    @commands.command(aliases=["price", "p"])
    async def prices(self, ctx, *, item):
        total_imgs = []
        item = self.search(item)
        if len(item) == 1:
            item_name = item[0]['UniqueName']
        else:
            item_name = item[0][1]['UniqueName']

        full_hisurl = self.base_url + item_name + '?date=1-1-2020&locations=' + f"{self.locations[0]}" + "".join(
            ["," + "".join(x) for x in self.locations if
             x != self.locations[0]]) + f"&time-scale={self.scale}"
        print(full_hisurl)

        raw_data = self.get_data(full_hisurl)

        # PreProcess Data
        data = {}
        # Use the cheapest available quality
        for city_obj in raw_data:
            pass

        for city_obj in raw_data:
            data[city_obj['location']] = pd.DataFrame(city_obj['data'])

        for city in data:
            data[city].timestamp = pd.to_datetime(data[city].timestamp)

        if len(raw_data) == 0:
            await ctx.send('No Price History Information Available')
        else:
            # Plotting avg_prices --------------------
            sns.set(rc={'axes.facecolor': 'black', 'axes.grid': True, 'grid.color': '.1',
                        'text.color': '.65', "lines.linewidth": 1})

            fig, ax = plt.subplots()
            # ax.patch.set_facecolor('black')
            city_ls = []
            for city in data:
                avg_prices = sns.lineplot(x='timestamp', y='avg_price', color=self.city_colours[city], data=data[city])
                city_ls.append(city)

            locs, labels = plt.xticks()
            plt.title('Average Item Price')
            plt.ylabel('')
            plt.setp(labels, rotation=20)
            plt.legend(labels=city_ls)

            # Store file in memory
            buf_p1 = io.BytesIO()
            plt.savefig(buf_p1, format='png')

            # Plotting Items sold
            sns.set(rc={'axes.facecolor': 'black', 'axes.grid': True, 'grid.color': '.1',
                        'text.color': '.65'})

            fig, ax = plt.subplots()
            for city in data:
                item_counts = plt.fill_between(data[city]['timestamp'], data[city]['item_count'],
                                               color=self.city_colours[city],
                                               alpha=0.3)
            locs, labels = plt.xticks()
            plt.title('Volume Sold')
            plt.ylabel('Items Sold')
            plt.setp(labels, rotation=20)
            plt.legend(labels=city_ls)
            # Store file in memory
            buf_p2 = io.BytesIO()
            plt.savefig(buf_p2, format='png')

            # Combine Graphs
            imgs = []
            for i in [buf_p1, buf_p2]:
                i.seek(0)
                imgs.append(Image.open(i).copy())
                i.close()
            # Pick the image which is the smallest, and resize the others to match it (can be arbitrary image shape here)
            min_shape = sorted([(np.sum(i.size), i.size) for i in imgs], reverse=True)[0][1]
            imgs_comb = np.hstack((np.asarray(i.resize(min_shape)) for i in imgs))
            total_imgs.append(PIL.Image.fromarray(imgs_comb))

        # Get Current Prices -----------------

        currurl = self.base_url_current + item_name + "?locations=" + f"{self.locations[0]}" + "".join(
            ["," + "".join(x) for x in self.locations if x != self.locations[0]])

        cdata = self.get_data(currurl)
        # print(currurl)

        Current_data = {}
        Current_date_data = {}
        # PreProcess
        for city in cdata:
            # print(Current_data)
            Current_data[city['city']] = [nan for x in range(5)]
            Current_date_data[city['city']] = [nan for x in range(5)]

        for city in cdata:
            if city['quality'] == 0:
                Current_data[city['city']][city['quality']] = city['sell_price_min']
                end = datetime.now()
                elapsed = end - datetime.strptime(city['sell_price_min_date'], "%Y-%m-%dT%H:%M:%S")
                # print(elapsed)
                # print(type(elapsed))
                Current_date_data[city['city']][city['quality']] = elapsed.total_seconds()
            else:
                Current_data[city['city']][city['quality'] - 1] = city['sell_price_min']
                end = datetime.now()
                elapsed = end - datetime.strptime(city['sell_price_min_date'], "%Y-%m-%dT%H:%M:%S")
                Current_date_data[city['city']][city['quality'] - 1] = elapsed.total_seconds()

        cdf = pd.DataFrame(Current_data, index=['Normal', 'Good', 'Outstanding', 'Excellent', 'Masterpiece'])
        cdf2 = pd.DataFrame(Current_date_data, index=['Normal', 'Good', 'Outstanding', 'Excellent', 'Masterpiece'])
        mask = cdf == 0
        fig, ax = plt.subplots(1, 2, figsize=(20, 6))
        a1 = sns.heatmap(cdf, annot=True, fmt='g', ax=ax[0], mask=mask)
        ax[0].set_title("Current Prices (Silver)")
        a1.set_xticklabels(a1.get_xticklabels(), rotation=30)
        a2 = sns.heatmap(cdf2, annot=True, fmt='g', ax=ax[1])
        ax[1].set_title("Last Updated")
        a2.set_xticklabels(a2.get_xticklabels(), rotation=30)

        # Store file in memory
        buf_p3 = io.BytesIO()
        plt.savefig(buf_p3, format='png')

        # Combine Graphs
        buf_p3.seek(0)
        total_imgs.append(Image.open(buf_p3).copy())
        buf_p3.close()
        min_shape = sorted([(np.sum(i.size), i.size) for i in total_imgs], reverse=True)[0][1]
        imgs_comb = np.vstack((np.asarray(i.resize(min_shape)) for i in total_imgs))

        # save that beautiful picture
        imgs_comb = PIL.Image.fromarray(imgs_comb)
        buf_3 = io.BytesIO()
        imgs_comb.save(buf_3, format='png')
        buf_3.seek(0)
        plotFile = discord.File(buf_3, filename="plot.png")
        buf_3.close()

        # Finally send the embed
        msg = await ctx.send(file=plotFile)

    def sort_sim(self, val):
        return val[0]

    def search(self, name):
        if name in self.id_list:
            return [(item) for item in self.dict if item['UniqueName'] == name]
        else:
            r = [(j.jaro_winkler(item['LocalizedNames']["EN-US"].lower(), name.lower()), item) for item in self.dict if
                 item['LocalizedNames'] is not None]
        r.sort(key=self.sort_sim, reverse=True)
        return r[0:5]

    def get_data(self, url):
        data = r.get(url).json()
        return data


def setup(client):
    client.add_cog(Market(client))
