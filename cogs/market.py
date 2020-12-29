import asyncio
import datetime
import io
import json
import logging
import math
from functools import wraps
from time import time
from timeit import default_timer as timer
from urllib import request

import aiohttp
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from discord import Embed, File
from discord.ext import commands
from libs.optimized_libs import item_search
from numpy import float64
from numpy import nan

log = logging.getLogger(__name__)
session = aiohttp.ClientSession()


def timing(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        start = timer()
        result = await f(*args, **kwargs)
        elapsed_time = timer() - start
        print(f"Elapsed time: {elapsed_time}")
        return result

    return wrapper


def average(lst):
    """
    Gets average of a list
    """
    if len(lst) == 0:
        return 0
    return sum(lst) / len(lst)


def c_game_currency(no):
    """
    Converts numbers to a shorter and more presentable format ie. 100000 go to 100k
    """
    if type(no) == float or type(no) == int or type(no) == float64:
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


def c_game_series(number):
    """
    Apply game currency function to Series
    """
    return number.apply(c_game_currency)


def c_last_updated_series(number):
    """
    Apply last updated function to Series
    """
    return number.apply(last_updated)


async def get_data(url):
    """
    Gets the data from the url and converts to Json
    :param url:
    :return:
    """
    # data = r.get(url).json()

    async with session.get(url) as resp:
        data = await resp.json()

    return data


def get_tier(string):
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
            return upper_case.index(upper) + 1, upper
        elif lower in string:
            return lower_case.index(lower) + 1, lower
    return None


def sort_sim(val):
    """
    Returns the first variable in tuple or list
    """
    return val[0]


def feature_extraction(item):
    """
    Get tier and enchant information from string
    """
    enchant = None
    for lvl in [".1", ".2", ".3", "@1", "@2", "@3"]:
        if lvl in item:
            enchant = int(lvl[1])

    tier = get_tier(item)

    return tier, enchant


def enchant_processing(item):
    """
    Detect if there is enchantment input in string
    :param item:
    :return:
    """
    enchant_lvl = 0
    for lvl in [".1", ".2", ".3"]:
        if lvl in item:
            item = item.replace(lvl, "")
            enchant_lvl = lvl.replace(".", "@")
    return item, enchant_lvl


def get_avg_stats(h_data):
    """
    Calculate average stats for items
    """
    # Initiate Avg price variables
    avg_price = []
    avg_sell_volume = []
    for city in h_data:
        avg_price.append(int(h_data[city]["avg_price"].mean()))
        avg_sell_volume.append((city, int(h_data[city]["item_count"].mean())))

    avg_p = c_game_currency(int(average(avg_price)))
    avg_sv = c_game_currency(int(average([x[1] for x in avg_sell_volume])))

    if len(avg_sell_volume) == 0:
        best_cs = (None, 0)
    else:
        best_cs = max(avg_sell_volume, key=lambda item: item[1])

    return avg_p, avg_sv, best_cs


def last_updated(date_):
    """
    Convert time string to datetime and get the duration between now and date.
    """
    if date_ == "":
        return ""
    d1 = datetime.datetime.today()
    td_object = d1 - datetime.datetime.strptime(date_, "%Y-%m-%dT%H:%M:%S")
    seconds = int(td_object.total_seconds())
    periods = [
        ("y", 60 * 60 * 24 * 365),
        ("m", 60 * 60 * 24 * 30),
        ("d", 60 * 60 * 24),
        ("h", 60 * 60),
        ("min", 60),
        ("s", 1),
    ]
    time_ = {"y": 0, "m": 0, "d": 0, "h": 0, "min": 0, "s": 0}
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            time_[period_name] = period_value

    lis = "\n"
    index = 0
    for key in time_:
        if time_[key] != 0:
            if index == 2:
                return lis  # + 'ago'
            index += 1
            if key == "min":
                lis += f"{time_[key]}m "
            else:
                lis += f"{time_[key]}{key} "
            if key == "s":
                return lis


class Market(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.base_url = "https://www.albion-online-data.com/api/v2/stats/history/"
        self.base_url_current = (
            "https://www.albion-online-data.com/api/v2/stats/prices/"
        )
        self.locations = [
            "Thetford",
            "Martlock",
            "Caerleon",
            "Lymhurst",
            "Bridgewatch",
            "FortSterling",
            "ArthursRest",
            "MerlynsRest",
            "MorganasRest",
            "BlackMarket",
        ]
        self.scale = 6
        self.itemList = "https://raw.githubusercontent.com/broderickhyman/ao-bin-dumps/master/formatted/items.json"

        # Get updated verions of item files
        try:
            print("Getting Latest Items:)")
            with request.urlopen(self.itemList) as url:
                self.dict = json.loads(url.read().decode())
            print("Latest Items downloaded)")
        except Exception as e:
            # Use fallback list of local items if download fails
            self.dict = json.load(open("data/item_data.json", "r", encoding="utf-8"))

        self.item_list = [
            item["LocalizedNames"]["EN-US"]
            for item in self.dict
            if item["LocalizedNames"] is not None
        ]
        self.id_list = [item["UniqueName"] for item in self.dict]
        self.city_colours = {
            "Thetford": "purple",
            "Martlock": "skyblue",
            "Caerleon": "red",
            "Lymhurst": "green",
            "Bridgewatch": "orange",
            "Fort Sterling": "grey",
            "Black Market": "white",
            "Arthurs Rest": "dodgerblue",
            "Merlyns Rest": "lawngreen",
            "Morganas Rest": "midnightblue",
        }

        self.tiers = [
            "Beginner's",
            "Novice's",
            "Journeyman's",
            "Adept's",
            "Expert's",
            "Master's",
            "Grandmaster's",
            "Elder's",
        ]
        self.quality_tiers = [
            "Normal",
            "Good",
            "Outstanding",
            "Excellent",
            "Masterpiece",
        ]

    @commands.command(aliases=["price", "p"])
    async def prices(self, ctx, *, item=None):
        """
        Gets the price of an item and its history
        Example usage: .p t6.1 hunter hood or .price t4  hide
        :param ctx:
        :param item:
        :return:
        """
        if item is None:
            await ctx.send(
                "Please enter an object to be searched:\n e.g  ```.p t6.1 hunter hood\n.price t4 hide ```"
            )
            return

        item_w = item[0:]
        id_c = False

        start_measuring_time = start = time()

        # Id code detection
        if item_w in self.id_list:
            item_f = [(11, item) for item in self.dict if item["UniqueName"] == item_w]
            tier, enchant = feature_extraction(item_w)
            id_c = True

        item_f, tier, enchant = self.search_processing(id_c, item_w)

        support_info = Embed(
            color=0x98FB98,
            description="឵឵💬 Feedback: [Discord](https://discord.gg/RzerS7X) | [Albion Forums](https://forum.albiononline.com/index.php/Thread/135629-RELEASE-Albie-An-Dedicated-Discord-Bot-For-Albion/) | Support: [Buy me a Coffee](https://ko-fi.com/gracious) ☕",
        )
        print(item_w, "...Searching...")
        try:
            item_name = item_f[0][1]["UniqueName"]
        except TypeError:
            embed = Embed(color=0xFF0000)
            embed.set_thumbnail(url="http://clipart-library.com/images/kTMK4787c.jpg")
            embed.add_field(
                name="Item Not Found",
                value="Looks like the item could not be found ! Try searching again with different spelling."
                " If this error persists drop me discord message from the link below.",
                inline=False,
            )
            await ctx.send(embed=embed)
            await ctx.send(embed=support_info)
            return
        thumb_url = (
            f"https://render.albiononline.com/v1/item/{item_name}.png?count=1&quality=1"
        )
        print(item_w, f"found item {item_name}")
        async with ctx.channel.typing():
            # Get all the data
            current_data, history_data = await asyncio.gather(
                self.get_current_data(item_name), self.get_history_data(item_name)
            )

            try:
                current_prices = await self.c_price_table(current_data)
            except json.decoder.JSONDecodeError:
                embed = Embed(color=0xFF0000)
                embed.set_thumbnail(
                    url="http://clipart-library.com/images/kTMK4787c.jpg"
                )
                embed.add_field(
                    name="No Information Sent to Albie Bot",
                    value="Looks like the Albion-Data Project didnt send anything to Poor Albie Bot, They might be under heavy load. Try seaching again, if this error persists drop me discord message.",
                    inline=False,
                )
                await ctx.send(embed=embed)

            current_buffer = await self.create_sell_buy_order(current_prices)

            # Historical Data
            try:
                history_buffer, h_data = await self.full_graph(history_data)
            except json.decoder.JSONDecodeError:
                embed = Embed(color=0xFF0000)
                embed.set_thumbnail(
                    url="http://clipart-library.com/images/kTMK4787c.jpg"
                )
                embed.add_field(
                    name="No Information Sent to Albie Bot",
                    value="Looks like the Albion-Data Project didnt send anything to Poor Albie Bot, They might be under heavy load. Try seaching again, if this error persists drop me discord message.",
                    inline=False,
                )
                await ctx.send(embed=embed)

            # Get avg_stats
            average_sell_price, avg_sell_volume, best_city_to_sell = get_avg_stats(
                h_data
            )

            best_cs_str = (
                f"{best_city_to_sell[0]} ({c_game_currency(best_city_to_sell[1])})"
            )

            # Start embed object
            title = f"{item_f[0][1]['LocalizedNames']['EN-US']} (Enchant:{enchant})\n"
            buyorder_embed = Embed(
                color=0x98FB98,
                title=title,
                url=f"https://www.albiononline2d.com/en/item/id/{item_name}",
            )
            buyorder_embed.set_thumbnail(url=thumb_url)

            # Current Data
            if len(current_prices[0].index) != 0:

                normalcheck_s = [str(x) for x in current_prices[0].T]
                if len(normalcheck_s) != 0:
                    avg_s_current_price = [
                        x
                        for x in current_prices[0].loc[normalcheck_s[0], :]
                        if not math.isnan(x)
                    ]
                    avg_s_cp = c_game_currency(int(average(avg_s_current_price)))
                    buyorder_embed.add_field(
                        name=f"Avg Current Sell Price ({normalcheck_s[0]})",
                        value=avg_s_cp,
                        inline=True,
                    )

            if len(current_prices[2].index) != 0:
                normalcheck_b = [str(x) for x in current_prices[2].T]
                if "Normal" in normalcheck_b:
                    avg_b_current_price = [
                        x
                        for x in current_prices[2].loc[normalcheck_b[0], :]
                        if not math.isnan(x)
                    ]
                    avg_b_cp = c_game_currency(int(average(avg_b_current_price)))
                    buyorder_embed.add_field(
                        name=f"Avg Current Buy Price ({normalcheck_b[0]})",
                        value=avg_b_cp,
                        inline=True,
                    )

            filename = f'{item_name.replace("@", "_")}_{datetime.datetime.today().strftime("%Y_%m_%d")}'

            if current_buffer is not None:
                current_buffer.seek(0)
                current_file = File(current_buffer, filename=f"{filename}.png")
                current_buffer.close()
                buyorder_embed.set_image(url=f"attachment://{filename}.png")
            else:
                buyorder_embed.description = "No Current Data Available!"
                buyorder_embed.colour = 0xFF0000

            history_embed = Embed(color=0x98FB98)
            if history_buffer is not None:
                history_buffer.seek(0)
                history_file = File(history_buffer, filename=f"{filename}H.png")
                history_buffer.close()
                history_embed.set_image(url=f"attachment://{filename}H.png")

                history_embed.add_field(
                    name="Avg Historical Price (Normal)",
                    value=average_sell_price,
                    inline=True,
                )
                history_embed.add_field(
                    name="Avg Sell Volume", value=avg_sell_volume, inline=True
                )
            history_embed.set_footer(
                text=f"ID: {item_f[0][1]['UniqueName']} || Best City Sales : {best_cs_str} || |>\nSuggested Searches: {str([x[1]['LocalizedNames']['EN-US'] for x in item_f[1:4]]).replace('[', '').replace(']', '')}"
            )
            if current_buffer is not None:
                await ctx.send(file=current_file, embed=buyorder_embed)
            else:
                await ctx.send(embed=buyorder_embed)

            stop_measuring_time = round(time() - start_measuring_time, 1)
            if history_buffer is None:
                history_embed.colour = 0xFF0000
                history_embed.description = "No History Data available!"
                history_embed.set_footer(
                    text=f"ID: {item_f[0][1]['UniqueName']} || Best City Sales : {best_cs_str} || Time Taken: {stop_measuring_time}s\nSuggested Searches: {str([x[1]['LocalizedNames']['EN-US'] for x in item_f[1:4]]).replace('[', '').replace(']', '')}"
                )
                await ctx.send(embed=history_embed)
            else:
                history_embed.set_footer(
                    text=f"ID: {item_f[0][1]['UniqueName']} || Best City Sales : {best_cs_str} || Time Taken: {stop_measuring_time}s\nSuggested Searches: {str([x[1]['LocalizedNames']['EN-US'] for x in item_f[1:4]]).replace('[', '').replace(']', '')}"
                )
                await ctx.send(file=history_file, embed=history_embed)
            await ctx.send(embed=support_info)

    async def get_current_data(self, item_name):
        try:
            currurl = (
                self.base_url_current
                + item_name
                + "?locations="
                + f"{self.locations[0]}"
                + "".join(
                    ["," + "".join(x) for x in self.locations if x != self.locations[0]]
                )
            )
            return await get_data(currurl)
        except Exception as e:
            print(e)
            return None

    async def get_history_data(self, item_name):
        date_6months_ago = (
            datetime.date.today() - datetime.timedelta(3 * 365 / 12)
        ).strftime("%m-%d-%Y")
        todays_date = datetime.date.today().strftime("%m-%d-%Y")
        try:
            full_hisurl = (
                self.base_url
                + item_name
                + f"?date={date_6months_ago}&end_date={todays_date}&locations="
                + f"{self.locations[0]}"
                + "".join(
                    ["," + "".join(x) for x in self.locations if x != self.locations[0]]
                )
                + f"&time-scale={self.scale}"
            )
            return await get_data(full_hisurl)
        except Exception as e:
            print(e)
            return None

    def search_processing(self, condition, item_w):
        # Search Processing --
        if not condition:
            tier, enchant = feature_extraction(item_w)
            list_v = [s for s in self.dict if s["LocalizedNames"] is not None]
            # Remove non tradable items
            list_v = [s for s in list_v if not "NONTRADABLE" in s["UniqueName"]]
            if tier is not None:
                list_v = [x for x in list_v if f"T{tier[0]}" in x["UniqueName"]]
                item_w = item_w.replace(f"T{tier[0]}", "")
            if enchant is not None:
                list_v = [x for x in list_v if f"@{enchant}" in x["UniqueName"]]
                item_w = item_w.replace(f".{enchant} ", "")

            item_f = item_search(item_w, list_v, self.id_list, self.dict)

            return item_f, tier, enchant
        else:
            return None, None, None

    async def c_price_table(self, cdata):
        """
        Generates an ASCII table with current price information
        :param cdata:
        :return:
        """

        # Table Creation
        city_table = {}
        city_table_last_updated = {}
        city_buy_order_table = {}
        city_buy_table_last_updated = {}
        for city in self.city_colours:
            city_table[city] = [nan, nan, nan, nan, nan]
            city_table_last_updated[city] = [nan, nan, nan, nan, nan]

        for city in self.city_colours:
            city_buy_order_table[city] = [nan, nan, nan, nan, nan]
            city_buy_table_last_updated[city] = [nan, nan, nan, nan, nan]

        for city in cdata:
            if city["sell_price_min"] == 0:
                city["sell_price_min"] = nan
            if city["buy_price_min"] == 0:
                city["buy_price_min"] = nan
            if city["sell_price_min_date"] == "0001-01-01T00:00:00":
                city["sell_price_min_date"] = nan
            if city["buy_price_min_date"] == "0001-01-01T00:00:00":
                city["buy_price_min_date"] = nan

            city_table[city["city"]][city["quality"] - 1] = city["sell_price_min"]
            city_buy_order_table[city["city"]][city["quality"] - 1] = city[
                "buy_price_min"
            ]
            city_table_last_updated[city["city"]][city["quality"] - 1] = city[
                "sell_price_min_date"
            ]
            city_buy_table_last_updated[city["city"]][city["quality"] - 1] = city[
                "buy_price_min_date"
            ]

        # Set up as DataFrame for Processing
        sell_data = pd.DataFrame(city_table, index=self.quality_tiers)
        buy_data = pd.DataFrame(city_buy_order_table, index=self.quality_tiers)
        city_table_last_updated = pd.DataFrame(
            city_table_last_updated, index=self.quality_tiers
        )
        city_buy_table_last_updated = pd.DataFrame(
            city_buy_table_last_updated, index=self.quality_tiers
        )

        # Remove empty columns and rows
        sell_data = sell_data.dropna(axis=0, how="all")
        sell_data = sell_data.dropna(axis=1, how="all")

        # Buy order
        buy_data = buy_data.dropna(axis=0, how="all")
        buy_data = buy_data.dropna(axis=1, how="all")

        # Clear Null updated values
        city_table_last_updated = city_table_last_updated.dropna(axis=0, how="all")
        city_table_last_updated = city_table_last_updated.dropna(axis=1, how="all")
        city_table_last_updated = city_table_last_updated.fillna("")
        city_table_last_updated = city_table_last_updated.apply(
            c_last_updated_series, axis=0
        )

        city_buy_table_last_updated = city_buy_table_last_updated.dropna(
            axis=0, how="all"
        )
        city_buy_table_last_updated = city_buy_table_last_updated.dropna(
            axis=1, how="all"
        )
        city_buy_table_last_updated = city_buy_table_last_updated.fillna("")
        city_buy_table_last_updated = city_buy_table_last_updated.apply(
            c_last_updated_series, axis=0
        )

        # Remove Nan and convert number into the game format
        sell_annotation = sell_data.apply(c_game_series, axis=0)
        sell_annotation = sell_annotation.fillna("")
        sell_annotation = sell_annotation.add(city_table_last_updated, fill_value="")

        # buy orders
        buy_annotation = buy_data.apply(c_game_series, axis=0)
        buy_annotation = buy_annotation.fillna("")
        buy_annotation = buy_annotation.add(city_buy_table_last_updated, fill_value="")

        return sell_data, sell_annotation, buy_data, buy_annotation

    async def create_sell_buy_order(self, current_data):
        sns.set(
            rc={
                "axes.facecolor": "black",
                "axes.grid": True,
                "grid.color": ".1",
                "text.color": ".65",
            }
        )

        if current_data[0].empty and current_data[2].empty:
            return None
        elif not current_data[0].empty and not current_data[2].empty:
            fig, ax = plt.subplots(1, 2, figsize=(20, 6))
            index_ = 0
            axx = 0
            for h_map in current_data:
                if (index_ % 2) == 0 or index_ == 0:
                    title = "Sell Order" if index_ == 0 else "Buy Order"
                    sb_map = sns.heatmap(
                        h_map,
                        annot=current_data[index_ + 1].to_numpy(),
                        ax=ax[axx],
                        fmt="",
                        cbar=False,
                    )
                    sb_map.set_xticklabels(sb_map.get_xticklabels(), rotation=30)
                    sb_map.set_yticklabels(sb_map.get_yticklabels(), rotation=0)
                    sb_map.set_title(title)
                    axx += 1
                index_ += 1
        else:
            fig, ax = plt.subplots(1, figsize=(20, 6))
            index_ = 0
            for h_map in current_data:
                if (index_ % 2) == 0 or index_ == 0:
                    title = "Sell Order" if index_ == 0 else "Buy Order"
                    if not h_map.empty:
                        sb_map = sns.heatmap(
                            h_map,
                            annot=current_data[index_ + 1].to_numpy(),
                            ax=ax,
                            fmt="",
                            cbar=False,
                        )
                        sb_map.set_xticklabels(sb_map.get_xticklabels(), rotation=30)
                        sb_map.set_yticklabels(sb_map.get_yticklabels(), rotation=0)
                        sb_map.set_title(title)
                index_ += 1
        # Save to Memory
        try:
            current_order_buffer = io.BytesIO()
            plt.savefig(current_order_buffer, format="png")
        finally:
            plt.close()

        return current_order_buffer

    async def full_graph(self, cdata):
        """
        Generates an average price history chart and returns history data
        :param cdata:
        :return:
        """
        # PreProcess Json Data
        data = {}
        for city_obj in cdata:
            data[city_obj["location"]] = pd.DataFrame(city_obj["data"])

        for city in data:
            data[city].timestamp = pd.to_datetime(data[city].timestamp)

        if len(data) == 0:
            return None, {}

        # Removing Outliers
        w_data = data.copy()
        for city in data:
            a = w_data[city]

            # Remove sets with less than 10 data points
            if a["avg_price"].size < 10:
                del w_data[city]
            else:
                # Remove values that do not lie within the 5% and 95% quantile
                w_data[city] = a[
                    a["avg_price"].between(
                        a["avg_price"].quantile(0.1), a["avg_price"].quantile(0.9)
                    )
                ]

        # if no data left, just show the points
        if len(w_data) == 0:
            w_data = data

        sns.set(
            rc={
                "axes.facecolor": "black",
                "axes.grid": True,
                "grid.color": ".1",
                "text.color": ".65",
                "lines.linewidth": 1,
            }
        )

        # Plotting avg_prices --------------------
        # ax.patch.set_facecolor('black')
        city_ls = []
        if len(w_data) != 0:
            for city in w_data:
                sns.lineplot(
                    x="timestamp",
                    y="avg_price",
                    color=self.city_colours[city],
                    data=w_data[city],
                )
                city_ls.append(city)

            locs, labels = plt.xticks()
            plt.title("Average Item Price (Past 3 Months)")
            plt.ylabel("")
            plt.setp(labels, rotation=20)
            plt.legend(labels=city_ls)

        labels = [c_game_currency(x) for x in plt.yticks()[0]]

        plt.yticks(plt.yticks()[0], labels)

        # Save to Memory
        buf_p1 = io.BytesIO()
        plt.savefig(buf_p1, format="png")
        plt.close()
        return buf_p1, w_data

    def tier_processing(self, item):
        """
        Detect Tier info in string and formats it to the correct search term
        :param item:
        :return:
        """
        tier = get_tier(item)
        if tier is not None:
            item = item.replace(tier[1], self.tiers[tier[0]])
        return item


def setup(client):
    client.add_cog(Market(client))
