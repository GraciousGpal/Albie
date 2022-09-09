import datetime
import io
import json
import logging
import math
from functools import wraps
from time import time
from timeit import default_timer as timer

import aiohttp
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from discord import Embed, File
from discord.errors import Forbidden
from discord.ext import commands
from numpy import nan, isnan

from libs.constants import CITY_COLOURS, QUALITY_TIERS
from libs.errors import NoInfoSentToAlbie, ItemNotFound
from libs.item_handler import Item, load_optimized_data, load_language_list_ls
from libs.utils import c_game_currency

log = logging.getLogger(__name__)
session = aiohttp.ClientSession()


# -------------------------------- #


def timing(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        start = timer()
        result = await f(*args, **kwargs)
        elapsed_time = timer() - start
        log.info(f"Elapsed time: {elapsed_time}")
        return result

    return wrapper


def average(lst):
    """
    Gets average of a list
    """
    if len(lst) == 0:
        return 0
    return sum(lst) / len(lst)


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


def sort_sim(val):
    """
    Returns the first variable in tuple or list
    """
    return val[0]


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
    if len(h_data) != 0:
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


async def c_price_table(cdata):
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


def process_history_data(history_data):
    # PreProcess Json Data
    data = {}
    for city_obj in history_data:
        data[city_obj["location"]] = pd.DataFrame(city_obj["data"])

    for city in data:
        data[city].timestamp = pd.to_datetime(data[city].timestamp)

    if len(data) == 0:
        return {}

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
    return data


async def full_graph(cdata):
    """
    Generates an average price history chart and returns history data
    :param cdata:
    :return:
    """
    # PreProcess Json Data
    w_data = process_history_data(cdata)

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
    if w_data is not None:
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


async def create_sell_buy_order(current_data):
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


def get_current_average_s(current_prices):
    # Current Data
    avg_s_cp = None
    avg_b_cp = None
    normalcheck_s = None
    normalcheck_b = None
    if len(current_prices[0].index) != 0:

        normalcheck_s = [str(x) for x in current_prices[0].T]
        if len(normalcheck_s) != 0:
            avg_s_current_price = [
                x
                for x in current_prices[0].loc[normalcheck_s[0], :]
                if not math.isnan(x)
            ]
            avg_s_cp = int(average(avg_s_current_price))
    if len(current_prices[2].index) != 0:
        normalcheck_b = [str(x) for x in current_prices[2].T]
        if "Normal" in normalcheck_b:
            avg_b_current_price = [
                x
                for x in current_prices[2].loc[normalcheck_b[0], :]
                if not math.isnan(x)
            ]
            avg_b_cp = int(average(avg_b_current_price))
    return avg_s_cp, avg_b_cp, normalcheck_s, normalcheck_b


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
        self.id_list = [item["UniqueName"] for item in self.dict]

    @commands.hybrid_command(aliases=["pt"])
    async def pricestext(self, ctx, *, item) -> None:
        """
        Gets the price of an item and its history (text format)
        Example usage: .p t6.1 hunter hood or .price t4  hide
        """
        try:
            log.info(f"{ctx.message.content}")
        except TypeError:
            pass
        if item is None:
            await ctx.send(
                "Please enter an object to be searched:\n e.g  ```/pricestext t6.1 hunter hood\n```"
            )
            return
        item = Item(self, ctx, item=item)
        try:
            async with ctx.channel.typing():
                item.get_matches()
                await item.get_data()
                try:
                    current_prices = await c_price_table(item.current_prices)
                except json.decoder.JSONDecodeError:
                    raise NoInfoSentToAlbie
                thumb_url = f"https://render.albiononline.com/v1/item/{item.matched}.png?count=1&quality=1"
                # Start embed object
                title = f"{item.name} (Enchant:{item.enchant})\n"
                buyorder_embed = Embed(
                    color=0x98FB98,
                    title=title,
                    url=f"https://www.albiononline2d.com/en/item/id/{item.matched}",
                )
                text = ''
                buyorder_embed.set_thumbnail(url=thumb_url)
                buyorder_embed.add_field(name='Sell Orders:', value='======', inline=False)
                for city, city_u in zip(current_prices[0], current_prices[1]):
                    for quality in current_prices[0][city].index:
                        value = current_prices[0][city][quality]
                        if isnan(value):
                            continue
                        updated_ss = current_prices[1][city_u][quality]
                        updated = updated_ss.split('\n')[1]
                        text += f"[{quality[0]}]: `{int(value)}` {updated}\n"
                    buyorder_embed.add_field(name=city, value=text, inline=True)
                    text = ""

                buyorder_embed.add_field(name='Buy Orders:', value='======', inline=False)
                for city, city_u in zip(current_prices[2], current_prices[3]):
                    for quality in current_prices[2][city].index:
                        value = current_prices[2][city][quality]
                        if isnan(value):
                            continue
                        updated_s = current_prices[3][city_u][quality]
                        updated = updated_s.split('\n')[1]
                        text += f"[{quality[0]}]: `{int(value)}` {updated}\n"
                    buyorder_embed.add_field(name=city, value=text, inline=True)
                    text = ""

                avg_s, avg_b, n_s, n_b = get_current_average_s(current_prices)
                sell_buy_text = f""
                if avg_s is not None:
                    sell_buy_text += f"Sell Orders({n_s[0][0]}):`{str(avg_s)}`\n"
                elif avg_b is not None:
                    sell_buy_text += "Buy Orders({n_b[0][0]}):`{str(avg_b)}`"
                buyorder_embed.add_field(name='Averages:',
                                         value=sell_buy_text,
                                         inline=False)

                history_data = process_history_data(item.price_history)
                if history_data is not None:
                    avg_p, avg_sv, best_cs = get_avg_stats(history_data)
                    info_text = f""
                    if n_s is not None:
                        info_text += f"Sell Orders({n_s[0][0]}):`{str(avg_p)}`"
                    elif n_b is not None:
                        info_text += f"Buy Orders({n_b[0][0]}):"
                    buyorder_embed.add_field(name='Historical Averages:',
                                             value=f"{info_text}\nSell Volume({n_s[0][0] if n_s is not None else None}):"
                                                   f"`{str(avg_sv)}`\n Best City Sales: {best_cs[0]}: `{c_game_currency(best_cs[1])}` (Sell Volume)",
                                             inline=False)
                buyorder_embed.set_footer(text="💬 Want to help Improve the bot ? Go to: github.com/GraciousGpal/Albie")
                await ctx.channel.send(embed=buyorder_embed)
        except Forbidden:
            await ctx.author.send(
                "Albie was unable to finish the command, due to missing permissions. Check your discord Settings")

    @commands.hybrid_command(aliases=["price", "p"])
    async def prices(self, ctx, *, item_i) -> None:
        """
        Gets the price of an item and its history
        Example usage: .p t6.1 hunter hood or .price t4  hide
        :param ctx:
        :param item_i:
        :return:
        """
        try:
            log.info(f"{ctx.message.content}")
        except TypeError:
            pass
        if item_i is None:
            await ctx.send(
                "Please enter an object to be searched:\n e.g  ```/prices t4 hide ```"
            )
            return
        start_measuring_time = time()
        item = Item(self, ctx, item=item_i)
        try:
            async with ctx.channel.typing():
                item.get_matches()
                await item.get_data()
                if item.matched is None:
                    raise ItemNotFound(ctx)
                thumb_url = f"https://render.albiononline.com/v1/item/{item.matched}.png?count=1&quality=1"
                log.info(f"{item.matched}, {item.name}, ...matched...")
                try:
                    current_prices = await c_price_table(item.current_prices)
                except json.decoder.JSONDecodeError:
                    embed = Embed(color=0xFF0000)
                    embed.set_thumbnail(
                        url="http://clipart-library.com/images/kTMK4787c.jpg"
                    )
                    embed.add_field(
                        name="No Information Sent to Albie Bot",
                        value="Looks like the Albion-Data Project didn't send anything to Poor Albie Bot,\
                             They might be under heavy load. Try searching again,\
                             if this error persists drop me discord message.",
                        inline=False,
                    )
                    await ctx.send(embed=embed)

                current_buffer = await create_sell_buy_order(current_prices)

                # Historical Data
                try:
                    history_buffer, h_data = await full_graph(item.price_history)
                except json.decoder.JSONDecodeError:
                    embed = Embed(color=0xFF0000)
                    embed.set_thumbnail(
                        url="http://clipart-library.com/images/kTMK4787c.jpg"
                    )
                    embed.add_field(
                        name="No Information Sent to Albie Bot",
                        value="Looks like the Albion-Data Project didnt send anything to Poor Albie Bot,\
                             They might be under heavy load.\
                             Try seaching again, if this error persists drop me discord message.",
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
                avg_s_current_price, avg_b_current_price, normalcheck_s, normalcheck_b = get_current_average_s(
                    current_prices)
                if avg_s_current_price is not None:
                    avg_s_cp = c_game_currency(avg_s_current_price)
                    buyorder_embed.add_field(
                        name=f"Avg Current Sell Price ({normalcheck_s[0]})",
                        value=avg_s_cp,
                        inline=True,
                    )
                if avg_b_current_price is not None:
                    avg_b_cp = c_game_currency(avg_b_current_price)
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
                if history_buffer is not None and h_data:
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
                    await ctx.channel.send(file=current_file, embed=buyorder_embed)
                else:
                    await ctx.channel.send(embed=buyorder_embed)

                stop_measuring_time = round(time() - start_measuring_time, 1)
                if history_buffer is None or not h_data:
                    history_embed.colour = 0xFF0000
                    history_embed.description = "No History Data available!"
                    history_embed.set_footer(
                        text=f"ID: {item.matched} || Best City Sales : {best_cs_str}|| Time: {stop_measuring_time}s\nSuggested Searches: {str([self.op_dict[x[0]]['LocalizedNames']['EN-US'] for x in item.results]).replace('[', '').replace(']', '')}"
                    )
                    await ctx.channel.send(embed=history_embed)
                else:
                    history_embed.set_footer(
                        text=f"ID: {item.matched} || Best City Sales : {best_cs_str}|| Time: {stop_measuring_time}s\nSuggested Searches: {str([self.op_dict[x[0]]['LocalizedNames']['EN-US'] for x in item.results]).replace('[', '').replace(']', '')}"
                    )
                    history_embed.set_footer(
                        text="💬 Want to help Improve the bot ? Go to: github.com/GraciousGpal/Albie")
                    await ctx.channel.send(file=history_file, embed=history_embed)
        except Forbidden:
            await ctx.author.send(
                "Albie was unable to finish the command, due to missing permissions. Check your discord Settings")


async def setup(client):
    await client.add_cog(Market(client))
