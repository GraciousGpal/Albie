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
from libs.optimized_libs import simple_distance_algorithm
from numpy import float64
from numpy import nan

log = logging.getLogger(__name__)
session = aiohttp.ClientSession()

# ------- PACKAGE CONSTANTS ------- #


BASE_URL_HISTORY = "https://www.albion-online-data.com/api/v2/stats/history/"
BASE_URL_CURRENT = "https://www.albion-online-data.com/api/v2/stats/prices/"
LOCATIONS = [
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
TIERS = [
    "Beginner's",
    "Novice's",
    "Journeyman's",
    "Adept's",
    "Expert's",
    "Master's",
    "Grandmaster's",
    "Elder's",
]
QUALITY_TIERS = [
    "Normal",
    "Good",
    "Outstanding",
    "Excellent",
    "Masterpiece",
]
CITY_COLOURS = {
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

support_info = Embed(
    color=0x98FB98,
    description="឵឵💬 Feedback: [Discord](https://discord.gg/RzerS7X) | \
		[Albion Forums](https://forum.albiononline.com/index.php/Thread/135629-RELEASE-Albie-An-Dedicated-Discord-Bot-For-Albion/)\
				| Support: [Buy me a Coffee](https://ko-fi.com/gracious) ☕",
)


# -------------------------------- #


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
    if isinstance(no, (float, int, float64)):
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


def strip_enchant(item_id: str):
    enchants = ["@1", "@2", "@3"]
    for enchant in enchants:
        if enchant in item_id:
            item_id = item_id.replace(enchant, "")
    return item_id


def get_suggestions(initial_list):
    suggestions = []
    cleared = []
    for s_item in initial_list:
        if strip_enchant(s_item[0]) not in cleared:
            suggestions.append(s_item)
        cleared.append(strip_enchant(s_item[0]))
        if len(suggestions) > 5:
            break
    return suggestions


def get_tier(string):
    """
    Checks for tier info in string and returns tier as an int and tier string
    in a tuple
    :param string:
    :return:
    """
    lower_case = ["t" + str(no) for no in range(1, 9)]
    upper_case = ["T" + str(no) for no in range(1, 9)]
    for lower, upper in zip(lower_case, upper_case):
        if upper in string:
            return upper_case.index(upper) + 1, upper
        if lower in string:
            return lower_case.index(lower) + 1, lower

    # Just get Numbers for tiers
    for letter in string:
        if letter.isdigit():
            index = string.index(letter)
            if "." in string:
                dot_indx = string.index(".")
                if (dot_indx - index) == 1:
                    return int(letter), f"T{letter}"
            else:
                return int(letter), f"T{letter}"

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
    return ""


def jw_search(name: str, item_score, language_list):
    found_list = []
    name = name.upper()

    item_keys = item_score.keys()

    # ID CHECK
    if name in item_score:
        return {name: 100}

    # tier and enchant detection
    tier, enchant = feature_extraction(name)

    # Preprocessing the search varibles and filtering.
    if tier is not None:
        item_keys = [key for key in item_score if f"T{tier[0]}" in key]
        name = name.replace(f"T{tier[0]}", "")
        name = name.replace(f"t{tier[0]}", "")
    if enchant is not None:
        item_keys = [key for key in item_keys if f"@{enchant}" in key]
        name = name.replace(f".{enchant} ", "")
    name = name if name[0] != " " else name[1:]

    # Searching through all language versions and scoring
    for item_languages in language_list:
        if item_languages[1] not in item_keys:
            continue
        # score = simple_distance_algorithm(name, item_languages[0])
        score = simple_distance_algorithm(name, item_languages[0])
        if score != 0:
            found_list.append((item_languages[1], score))

    found_list = sorted(found_list, key=lambda tup: tup[1], reverse=True)
    suggestions = get_suggestions(found_list)
    return {"suggestions": suggestions, "tier": tier, "enchant": enchant}


def download_file_with_fallback(url_, fallback_path):
    try:
        with request.urlopen(url_) as url:
            data = json.loads(url.read().decode())
    except Exception:
        # Use fallback list of local items if download fails
        with open(fallback_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    return data


def load_optimized_data(data_url):
    # Get updated versions of item files and returns a trimmed version of the file.
    print("Getting Latest Items:)")
    data = download_file_with_fallback(data_url, "data/item_data.json")
    print("Latest Items downloaded)")
    trimmed_data = {}
    for item in data:
        meta = {}
        try:
            meta["LocalizedNames"] = item["LocalizedNames"]
            meta["LocalizedDescriptions"] = item["LocalizedDescriptions"]
        except KeyError:
            pass

        if meta["LocalizedNames"] is None:
            continue
        meta["UniqueName"] = item["UniqueName"]

        trimmed_data[item["UniqueName"]] = meta
    return trimmed_data, data


def load_crafting_data(data_url):
    """
    Download and format crafting data for items
    """
    itemdata = {}
    print("Getting Item crafting data:)")
    data = download_file_with_fallback(data_url, "data/items_crafting.json")
    for category in data["items"]:
        if category in (
                "shopcategories",
                "@xmlns:xsi",
                "@xsi:noNamespaceSchemaLocation",
        ):
            continue
        if isinstance(data["items"][category], list):
            for item in data["items"][category]:
                if "craftingrequirements" in item:
                    itemdata[item["@uniquename"]] = {"tier": item["@tier"]}
                    if "currency" in item["craftingrequirements"]:
                        itemdata[item["@uniquename"]]["faction_cost"] = {
                            "name": item["craftingrequirements"]["currency"][
                                "@uniquename"
                            ],
                            "amount": item["craftingrequirements"]["currency"][
                                "@amount"
                            ],
                        }
                    if "silver" in item["craftingrequirements"]:
                        itemdata[item["@uniquename"]]["silver"] = item[
                            "craftingrequirements"
                        ]["@silver"]
                    if "craftresource" in item["craftingrequirements"]:
                        itemdata[item["@uniquename"]]["craft_requirements"] = item[
                            "craftingrequirements"
                        ]["craftresource"]
        elif isinstance(data["items"][category], dict):
            item = data["items"][category]
            itemdata[item["@uniquename"]] = {
                "value": item["@itemvalue"],
                "tier": item["@tier"],
                "silver_cost": item["craftingrequirements"]["@silver"],
                "requirements": item["craftingrequirements"]["craftresource"],
            }
    print("Item crafting data downloaded)")
    return itemdata


def load_language_list_ls(item_dictionary):
    items_in_all_lang = []
    for item_v2 in item_dictionary:
        for language in item_dictionary[item_v2]["LocalizedNames"]:
            items_in_all_lang.append(
                [item_dictionary[item_v2]["LocalizedNames"][language].upper(), item_v2]
            )
    return items_in_all_lang


async def get_current_data(item_name):
    try:
        currurl = (
                BASE_URL_CURRENT
                + item_name
                + "?locations="
                + f"{LOCATIONS[0]}"
                + "".join(["," + "".join(x) for x in LOCATIONS if x != LOCATIONS[0]])
        )
        return await get_data(currurl)
    except Exception as e:
        print(e)
        return None


async def get_history_data(item_name, scale=6):
    date_months_ago = (
            datetime.date.today() - datetime.timedelta(6 * 365 / 12)
    ).strftime("%m-%d-%Y")
    todays_date = datetime.date.today().strftime("%m-%d-%Y")
    try:
        full_hisurl = (
                BASE_URL_HISTORY
                + item_name
                + f"?date={date_months_ago}&end_date={todays_date}&locations="
                + f"{LOCATIONS[0]}"
                + "".join(["," + "".join(x) for x in LOCATIONS if x != LOCATIONS[0]])
                + f"&time-scale={scale}"
        )
        return await get_data(full_hisurl)
    except Exception as e:
        print(e)
        return None


def get_thumbnail_url(item_name):
    return f"https://render.albiononline.com/v1/item/{item_name}.png?count=1&quality=1"


class Item:
    def __init__(self, cog_self=None, ctx=None, item=None):
        self.item_w = item[0:]
        self.cog_self = cog_self
        self.ctx = ctx
        self.start_f_time = None
        self.match_time = None
        self.matched = None
        self.name = None
        self.results = None
        self.current_prices = None
        self.price_history = None
        self.enchant = None
        self.tier = None

    def get_matches(self):
        start_t = time()
        results = jw_search(
            self.item_w, self.cog_self.item_id_score.copy(), self.cog_self.language_list
        )
        self.matched = results["suggestions"][0][0]
        self.name = (
            self.cog_self.op_dict[self.matched]["LocalizedNames"]["EN-US"]
            if self.matched is not None
            else None
        )
        self.results = results["suggestions"]
        self.tier = results["tier"]
        if results["enchant"] is None:
            self.enchant = 0
        else:
            self.enchant = results["enchant"]
        self.match_time = time() - start_t

    async def get_data(self):
        self.current_prices, self.price_history = await asyncio.gather(
            get_current_data(self.matched), get_history_data(self.matched)
        )


class NoInfoSentToAlbie(Exception):
    """
    Looks like the Albion-Data Project didnt send anything to Poor Albie Bot, They might be under heavy load.
    Try searching again, if this error persists drop me discord message.
    """


class Market(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.item_url = "https://raw.githubusercontent.com/broderickhyman/ao-bin-dumps/master/formatted/items.json"
        self.op_dict, self.dict = load_optimized_data(self.item_url)
        self.language_list = load_language_list_ls(self.op_dict)
        self.item_id_score = {
            key.upper(): 0
            for (key, value) in self.op_dict.items()
            if "NONTRADABLE" not in key
        }
        self.craft_data = load_crafting_data(
            "https://raw.githubusercontent.com/broderickhyman/ao-bin-dumps/master/items.json"
        )
        self.id_list = [item["UniqueName"] for item in self.dict]

    @commands.command(aliases=["c"])
    async def craft(self, ctx, amount=1, *, item=None):
        """
        Calculate the estimated cost of crafting a certain amount of items.
        """
        if item is None:
            await ctx.send(
                "Please enter an object to be searched:\n e.g  ```.c 10 Minor Healing Potion\n.c <amount> <item> ```"
            )
            return
        item = Item(self, ctx, item=item)
        async with ctx.channel.typing():
            item.get_matches()
            if "@" in item.matched:
                await ctx.send("Enchanted Items are not supported at the moment")
                return
            embed = Embed(title=f"Crafting: {item.name}")

            embed.set_thumbnail(url=get_thumbnail_url(item.matched))
            try:
                items_needed = self.craft_data[item.matched]
            except KeyError:
                await ctx.send("This Item is not supported")
            if isinstance(items_needed["craft_requirements"], dict):
                items_needed["craft_requirements"] = [
                    items_needed["craft_requirements"]
                ]

            task_list = [
                get_history_data(x["@uniquename"])
                for x in items_needed["craft_requirements"]
            ]
            history_data = await asyncio.gather(*task_list)
            item_meta = {}
            text2 = ""
            total = 0
            for ingred in history_data:
                for locationdata in ingred:
                    item_meta[locationdata["item_id"]] = {}
                for locationdata in ingred:
                    prices = [x["avg_price"] for x in locationdata["data"]]
                    item_count = [x["item_count"] for x in locationdata["data"]]
                    avg_p = sum(prices) / len(prices)
                    avg_count = sum(item_count) / len(item_count)
                    item_meta[locationdata["item_id"]][locationdata["location"]] = {
                        "avg_price": avg_p,
                        "volume": avg_count,
                    }
            for ingre in items_needed["craft_requirements"]:
                location_p = {}
                item_amount = int(ingre["@count"]) * amount
                text = f"Amount: {item_amount} Cost:\n"
                item_id_ = ingre["@uniquename"]
                for location in item_meta[item_id_]:
                    cost = round(item_meta[item_id_][location]["avg_price"])
                    total_cost = cost * item_amount
                    location_p[location] = total_cost
                    text += f"{location}: {c_game_currency(cost)} Volume Sold:\
					 {c_game_currency(round(item_meta[item_id_][location]['volume'], 1))} Total Cost: {c_game_currency(total_cost)}\n"
                embed.add_field(
                    name=self.op_dict[ingre["@uniquename"]]["LocalizedNames"]["EN-US"],
                    value=text,
                    inline=False,
                )

                cheapest_location = min(
                    [(location_p[x], x) for x in location_p], key=lambda t: t[0]
                )
                total += cheapest_location[0]
                text2 += f"**{self.op_dict[ingre['@uniquename']]['LocalizedNames']['EN-US']} x{item_amount}**\n \
				Cheapest location: {cheapest_location[1]} Price: {c_game_currency(round(cheapest_location[0]))}\n"
            text2 += (
                f"\n ***Total Silver Cost***: ```py\n{c_game_currency(round(total))}```"
            )
            embed.add_field(name="Totals:", value=text2, inline=False)
            await ctx.send(embed=embed)
        return

    @commands.command(aliases=["pt"])
    async def pricestext(self, ctx, *, item=None):
        """
        Gets the price of an item and its history (text format)
        Example usage: .p t6.1 hunter hood or .price t4  hide
        """
        if item is None:
            await ctx.send(
                "Please enter an object to be searched:\n e.g  ```.p t6.1 hunter hood\n.price t4 hide ```"
            )
            return
        item = Item(self, ctx, item=item)
        async with ctx.channel.typing():
            item.get_matches()
            await item.get_data()
            try:
                current_prices = await self.c_price_table(item.current_prices)
            except json.decoder.JSONDecodeError:
                raise NoInfoSentToAlbie
            thumb_url = f"https://render.albiononline.com/v1/item/{item.matched}.png?count=1&quality=1"
            pass

    @commands.command(aliases=["price", "p"])
    async def prices(self, ctx, *, item_i=None):
        """
        Gets the price of an item and its history
        Example usage: .p t6.1 hunter hood or .price t4  hide
        :param ctx:
        :param item:
        :return:
        """
        if item_i is None:
            await ctx.send(
                "Please enter an object to be searched:\n e.g  ```.p t6.1 hunter hood\n.price t4 hide ```"
            )
            return
        start_measuring_time = time()
        item = Item(self, ctx, item=item_i)
        async with ctx.channel.typing():
            item.get_matches()
            await item.get_data()
            thumb_url = f"https://render.albiononline.com/v1/item/{item.matched}.png?count=1&quality=1"
            print(item_i, item.matched, item.name, "...matched...")
            try:
                current_prices = await self.c_price_table(item.current_prices)
            except json.decoder.JSONDecodeError:
                embed = Embed(color=0xFF0000)
                embed.set_thumbnail(
                    url="http://clipart-library.com/images/kTMK4787c.jpg"
                )
                embed.add_field(
                    name="No Information Sent to Albie Bot",
                    value="Looks like the Albion-Data Project didnt send anything to Poor Albie Bot,\
						 They might be under heavy load. Try seaching again, if this error persists drop me discord message.",
                    inline=False,
                )
                await ctx.send(embed=embed)

            current_buffer = await self.create_sell_buy_order(current_prices)

            # Historical Data
            try:
                history_buffer, h_data = await self.full_graph(item.price_history)
            except json.decoder.JSONDecodeError:
                embed = Embed(color=0xFF0000)
                embed.set_thumbnail(
                    url="http://clipart-library.com/images/kTMK4787c.jpg"
                )
                embed.add_field(
                    name="No Information Sent to Albie Bot",
                    value="Looks like the Albion-Data Project didnt send anything to Poor Albie Bot,\
						 They might be under heavy load. Try seaching again, if this error persists drop me discord message.",
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
            title = f"{item.name} (Enchant:{item.enchant})\n"
            buyorder_embed = Embed(
                color=0x98FB98,
                title=title,
                url=f"https://www.albiononline2d.com/en/item/id/{item.matched}",
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

            filename = f'{item.matched.replace("@", "_")}_{datetime.datetime.today().strftime("%Y_%m_%d")}'

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
                text=f"ID: {item.matched} || Best City Sales : {best_cs_str} ||\
					 |>\nSuggested Searches: {str([self.op_dict[x[0]]['LocalizedNames']['EN-US'] for x in item.results]).replace('[', '').replace(']', '')}"
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
                    text=f"ID: {item.matched} || Best City Sales : {best_cs_str}|| Time: {stop_measuring_time}s\nSuggested Searches: {str([self.op_dict[x[0]]['LocalizedNames']['EN-US'] for x in item.results]).replace('[', '').replace(']', '')}"
                )
                await ctx.send(embed=history_embed)
            else:
                history_embed.set_footer(
                    text=f"ID: {item.matched} || Best City Sales : {best_cs_str}|| Time: {stop_measuring_time}s\nSuggested Searches: {str([self.op_dict[x[0]]['LocalizedNames']['EN-US'] for x in item.results]).replace('[', '').replace(']', '')}"
                )
                await ctx.send(file=history_file, embed=history_embed)
            await ctx.send(embed=support_info)

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
        for city in CITY_COLOURS:
            city_table[city] = [nan, nan, nan, nan, nan]
            city_table_last_updated[city] = [nan, nan, nan, nan, nan]

        for city in CITY_COLOURS:
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
        sell_data = pd.DataFrame(city_table, index=QUALITY_TIERS)
        buy_data = pd.DataFrame(city_buy_order_table, index=QUALITY_TIERS)
        city_table_last_updated = pd.DataFrame(
            city_table_last_updated, index=QUALITY_TIERS
        )
        city_buy_table_last_updated = pd.DataFrame(
            city_buy_table_last_updated, index=QUALITY_TIERS
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
                    color=CITY_COLOURS[city],
                    data=w_data[city],
                )
                city_ls.append(city)

            locs, labels = plt.xticks()
            plt.title("Average Item Price")
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


if __name__ == "__main__":
    pass
    # from libs.optimized_libs import simple_distance_algorithm
