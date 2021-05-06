import logging
from asyncio import gather

from discord import Embed
from discord.ext import commands

from libs.constants import support_info
from libs.item_handler import Item, get_history_data, load_optimized_data, load_language_list_ls
from libs.utils import download_file_with_fallback, get_thumbnail_url, c_game_currency

log = logging.getLogger(__name__)


def load_crafting_data(data_url):
    """
    Download and format crafting data for items
    """
    itemdata = {}
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
    log.info("Item crafting data downloaded")
    return itemdata


class Crafting(commands.Cog):
    def __init__(self, client):
        self.client = client
        if not hasattr(self, 'item_url') or not hasattr(self, 'op_dict'):
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
            history_data = await gather(*task_list)
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
            await ctx.send(embed=support_info)
        return


def setup(client):
    client.add_cog(Crafting(client))


if __name__ == "__main__":
    pass
