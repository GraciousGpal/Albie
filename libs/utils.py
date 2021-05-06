import json
from urllib import request

from aiohttp import ClientSession
from numpy.core import float64

session = ClientSession()


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


def get_thumbnail_url(item_name):
    return f"https://render.albiononline.com/v1/item/{item_name}.png?count=1&quality=1"


def download_file_with_fallback(url_, fallback_path):
    try:
        with request.urlopen(url_) as url:
            data = json.loads(url.read().decode())
    except Exception:
        # Use fallback list of local items if download fails
        with open(fallback_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    return data


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
