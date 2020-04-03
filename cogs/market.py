import io
import json
from datetime import date

import jellyfish as j
import matplotlib.pyplot as plt
import pandas as pd
import requests
import requests as r
import seaborn as sns
from discord import Embed
from discord.ext import commands
from numpy import nan
from tabulate import tabulate


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

        self.tiers = ["Beginner's", "Novice's", "Journeyman's", "Adept's", "Expert's", "Master's", "Grandmaster's",
                      "Elder's"]
        self.quality_tiers = ['Normal', 'Good', 'Outstanding', 'Excellent', 'Masterpiece']

    @commands.command(aliases=["price", "p"])
    async def prices(self, ctx, *, item):

        item_w = item[0:]
        id_c = False
        enchant_lvl = None

        # Id code detection
        if item_w in self.id_list:
            item_f = [(11, item) for item in self.dict if item['UniqueName'] == item_w]
            id_c = True

        # Search Processing --
        if not id_c:
            # Set Enchant Lvl
            processed_d = self.enchant_processing(item_w)
            enchant_lvl = processed_d[1]
            item_w = processed_d[0]

            # Tier Processing
            item_w = self.tier_processing(item_w)

            # Item Search
            item_f = self.search(item_w)

        item_name = item_f[0][1]['UniqueName']

        # Form url
        if enchant_lvl is None:
            enchant_str = ""
        elif enchant_lvl == 0:
            enchant_str = ""
        else:
            enchant_str = enchant_lvl

        currurl = self.base_url_current + item_name + enchant_str + "?locations=" + f"{self.locations[0]}" + "".join(
            ["," + "".join(x) for x in self.locations if x != self.locations[0]])
        full_hisurl = self.base_url + item_name + enchant_str + '?date=1-1-2020&locations=' + f"{self.locations[0]}" + "".join(
            ["," + "".join(x) for x in self.locations if
             x != self.locations[0]]) + f"&time-scale={self.scale}"
        thumb_url = f"https://gameinfo.albiononline.com/api/gameinfo/items/{item_name + enchant_str}.png?count=1"

        current_prices = self.c_price_table(currurl)

        # Historical Data [Plotfile , Data]
        h_data = self.full_graph(full_hisurl, current_prices)

        # Calculate Avg price
        avg_price = []
        avg_sell_volume = []
        for city in h_data[1]:
            avg_price.append(int(h_data[1][city]['avg_price'].mean()))
            avg_sell_volume.append((city, int(h_data[1][city]['item_count'].mean())))

        title = f"Item Data for {item_f[0][1]['LocalizedNames']['EN-US']} {enchant_str.replace('@', '')}"
        embed = Embed(title=title)
        embed.set_thumbnail(url=thumb_url)
        avg_p = self.c_game_currency(int(self.average(avg_price)))
        avg_sv = self.c_game_currency(self.average([x[1] for x in avg_sell_volume]))

        if len(avg_sell_volume) == 0:
            best_cs = (None, 0)
        else:
            best_cs = max(avg_sell_volume, key=lambda item: item[1])
        best_cs_str = f'{best_cs[0]} ({self.c_game_currency(best_cs[1])})'
        embed.add_field(name="(1W) Avg Price", value=avg_p, inline=True)
        embed.add_field(name="Avg Sell Volume", value=int(avg_sv), inline=True)
        embed.add_field(name="Best City Sales", value=best_cs_str, inline=True)

        # Upload to temp.sh and get url
        today = date.today()
        filename = f'{item_name}-{today}'
        h_data[0].seek(0)
        r = requests.put(f'https://temp.sh/{filename}.png', data=h_data[0])
        h_data[0].close()
        x = str(r.content)
        x = x.replace("b'", "").replace("'", "")
        embed.set_image(url=x)

        await ctx.send(embed=embed)

    def c_price_table(self, currurl):
        '''
        Generates an ASCII table with current price information
        :param currurl:
        :return:
        '''
        # Get Data
        cdata = self.get_data(currurl)

        # Table Creation
        city_table = {}
        for city in self.city_colours:
            city_table[city] = [nan, nan, nan, nan, nan]

        for city in cdata:
            if city['sell_price_min'] == 0:
                city['sell_price_min'] = nan

            city_table[city['city']][city['quality'] - 1] = city['sell_price_min']

        # Set up as DataFrame for Processing
        frame = pd.DataFrame(city_table, index=self.quality_tiers)

        # Remove empty columns and rows
        frame = frame.dropna(axis=0, how='all')
        frame = frame.dropna(axis=1, how='all')

        # Remove Nan and convert number into the game format
        frame2 = frame.apply(self.c_game_series, axis=0)
        frame2 = frame2.fillna('')

        return tabulate(frame, headers="keys", tablefmt="fancy_grid"), frame, frame2

    def full_graph(self, url, current_price_data):
        '''
        Generates an average price history chart and returns history data
        :param url:
        :return:
        '''
        # Get Data
        cdata = self.get_data(url)

        # PreProcess Json Data
        data = {}
        for city_obj in cdata:
            data[city_obj['location']] = pd.DataFrame(city_obj['data'])

        for city in data:
            data[city].timestamp = pd.to_datetime(data[city].timestamp)

        # Removing Outliers
        rm_out = True
        w_data = data.copy()
        if rm_out:
            for city in data:
                a = w_data[city]

                # Remove sets with less than 10 data points
                if a['avg_price'].size < 10:
                    del w_data[city]
                else:
                    # Remove values that do not lie within the 5% and 95% quantile
                    a = a[a['avg_price'].between(a['avg_price'].quantile(.05), a['avg_price'].quantile(.95))]

        sns.set(rc={'axes.facecolor': 'black', 'axes.grid': True, 'grid.color': '.1',
                    'text.color': '.65', "lines.linewidth": 1})

        if len(w_data) != 0:
            no_plots = 2
            fig, ax = plt.subplots(1, no_plots, figsize=(20, 6))
            a1 = sns.heatmap(current_price_data[1], annot=current_price_data[2].to_numpy(), ax=ax[0], fmt='')
            a1.set_xticklabels(a1.get_xticklabels(), rotation=30)
            a1.set_yticklabels(a1.get_yticklabels(), rotation=0)
        else:
            no_plots = 0
            fig, ax = plt.subplots(1, figsize=(20, 6))
            a1 = sns.heatmap(current_price_data[1], annot=current_price_data[2].to_numpy(), fmt='')
            a1.set_xticklabels(a1.get_xticklabels(), rotation=30)
            a1.set_yticklabels(a1.get_yticklabels(), rotation=0)

        # Plotting avg_prices --------------------
        # ax.patch.set_facecolor('black')
        city_ls = []
        if len(w_data) != 0:
            for city in w_data:
                sns.lineplot(x='timestamp', y='avg_price', color=self.city_colours[city], data=w_data[city],
                             ax=ax[1])
                city_ls.append(city)

            locs, labels = plt.xticks()
            plt.title('Average Item Price')
            plt.ylabel('')
            plt.setp(labels, rotation=20)
            plt.legend(labels=city_ls)

        # Save to Memory
        buf_p1 = io.BytesIO()
        plt.savefig(buf_p1, format='png')
        return buf_p1, w_data

    def id_detection(self, string):
        """
        Detects Item ID codes in input
        :param string:
        :return:
        """
        if string in self.id_list:
            item_w = [(11, item) for item in self.dict if item['UniqueName'] == string][0]
        else:
            item_w = self.search(string)
        return item_w

    def enchant_processing(self, item):
        """
        Detect if there is enchantment input in string
        :param item:
        :return:
        """
        enchant_lvl = 0
        for lvl in [".1", ".2", ".3"]:
            if lvl in item:
                item = item.replace(lvl, "")
                enchant_lvl = lvl.replace('.', '@')
        return item, enchant_lvl

    def tier_processing(self, item):
        """
        Detect Tier info in string and formats it to the correct search term
        :param item:
        :return:
        """
        tier = self.get_tier(item)
        if tier is not None:
            item = item.replace(tier[1], self.tiers[tier[0]])
        return item

    def search(self, name):
        """
        Uses Jaro Winkler method to find the closest match for the input to a list of items.
        :param name:
        :return:
        """
        if name in self.id_list:
            return [(11, item) for item in self.dict if item['UniqueName'] == name]
        else:
            r = [(j.jaro_winkler(item['LocalizedNames']["EN-US"].lower(), name.lower()), item) for item in self.dict if
                 item['LocalizedNames'] is not None]
        r.sort(key=self.sort_sim, reverse=True)
        return r[0:5]

    def sort_sim(self, val):
        return val[0]

    def get_tier(self, string):
        """
        Checks for tier info in string and returns tier-1 as an int and tier string
        in a tuple
        :param string:
        :return:
        """
        lower_case = ["t" + str(no) for no in range(1, 9)]
        upper_case = ["T" + str(no) for no in range(1, 9)]
        for lower, upper in zip(lower_case, upper_case):
            if upper in string:
                return upper_case.index(upper), upper
            elif lower in string:
                return lower_case.index(lower), lower
        return None

    def get_data(self, url):
        """
        Gets the data from the url and converts to Json
        :param url:
        :return:
        """
        data = r.get(url).json()
        return data

    def c_game_series(self, number):
        return number.apply(self.c_game_currency)

    def c_game_currency(self, no):
        if type(no) == float or type(no) == int:
            if no >= 1000000000:
                return str(round(no / 1000000000, 2)) + "b"
            elif no >= 1000000:
                return str(round(no / 1000000, 2)) + "m"
            elif no >= 1000:
                return str(round(no / 1000, 2)) + "k"
            else:
                return str(no)
        else:
            return str(no)

    def average(self, lst):
        if len(lst) == 0:
            return 0
        return sum(lst) / len(lst)


def setup(client):
    client.add_cog(Market(client))


if __name__ == '__main__':
    m = Market(None)
    for item in ['t7.1 warbow', 'T5_2H_WARBOW', 'cabbage']:
        price = m.price(None, item)
