import asyncio
import datetime
import logging
from time import time

import aiohttp

from libs.constants import BASE_URL_HISTORY, BASE_URL_CURRENT, LOCATIONS
from libs.search_algorithms import jw_search
from libs.utils import get_data, download_file_with_fallback

log = logging.getLogger(__name__)
session = aiohttp.ClientSession()


def load_optimized_data(data_url):
    # Get updated versions of item files and returns a trimmed version of the file.
    data = download_file_with_fallback(data_url, "data/item_data.json")
    log.info("Latest Items downloaded.")
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
        log.error(e)
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
        log.error(e)
        return None


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
        if results["suggestions"][0][0] is None:
            return
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


def load_language_list_ls(item_dictionary):
    items_in_all_lang = []
    for item_v2 in item_dictionary:
        for language in item_dictionary[item_v2]["LocalizedNames"]:
            items_in_all_lang.append(
                [item_dictionary[item_v2]["LocalizedNames"][language].upper(), item_v2]
            )
    return items_in_all_lang
