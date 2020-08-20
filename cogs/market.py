import asyncio
import io
import json
import logging
import math
from datetime import date
from functools import wraps
from timeit import default_timer as timer
from urllib import request

import jellyfish as j
import matplotlib.pyplot as plt
import pandas as pd
import requests as r
import seaborn as sns
from discord import Embed, File
from discord.ext import commands
from libs.token_match import token_set_ratio
from numpy import nan
from tabulate import tabulate

log = logging.getLogger(__name__)


def timing(f):
	@wraps(f)
	async def wrapper(*args, **kwargs):
		start = timer()
		result = await f(*args, **kwargs)
		elapsed_time = timer() - start
		print(f'Elapsed time: {elapsed_time}')
		return result

	return wrapper


async def multi(item_, name):
	return [token_set_ratio(item_['UniqueName'].lower(), name.lower()), item_, None]


async def multi2(item_, name):
	return [token_set_ratio(item_[0], name.lower()), item_[1], None]


def average(lst):
	if len(lst) == 0:
		return 0
	return sum(lst) / len(lst)


def c_game_currency(no):
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


def c_game_series(number):
	return number.apply(c_game_currency)


def get_data(url):
	"""
	Gets the data from the url and converts to Json
	:param url:
	:return:
	"""
	data = r.get(url).json()
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
	return val[0]


def feature_extraction(item):
	enchant = None
	for lvl in [".1", ".2", ".3", '@1', '@2', '@3']:
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
			enchant_lvl = lvl.replace('.', '@')
	return item, enchant_lvl


class Market(commands.Cog):
	def __init__(self, client):
		self.client = client
		self.base_url = "https://www.albion-online-data.com/api/v2/stats/history/"
		self.base_url_current = "https://www.albion-online-data.com/api/v2/stats/prices/"
		self.locations = ['Thetford', 'Martlock', 'Caerleon', 'Lymhurst', 'Bridgewatch', 'FortSterling',
						  'BlackMarket']
		self.scale = 6
		self.itemList = "https://raw.githubusercontent.com/augusto501/ao-bin-dumps/master/formatted/items.json"

		# Get updated verions of item files
		try:
			print('Getting Latest Items:)')
			with request.urlopen(self.itemList) as url:
				self.dict = json.loads(url.read().decode())
			print('Latest Items downloaded)')
		except Exception as e:
			# Use fallback list of local items if download fails
			self.dict = json.load(open("data/item_data.json", 'r', encoding='utf-8'))

		self.item_list = [item['LocalizedNames']["EN-US"] for item in self.dict if item['LocalizedNames'] is not None]
		self.id_list = [item['UniqueName'] for item in self.dict]
		self.city_colours = {'Thetford': 'purple', 'Martlock': 'skyblue', 'Caerleon': 'red', 'Lymhurst': 'green',
							 'Bridgewatch': 'orange', 'Fort Sterling': 'grey', 'Black Market': 'white'}

		self.tiers = ["Beginner's", "Novice's", "Journeyman's", "Adept's", "Expert's", "Master's", "Grandmaster's",
					  "Elder's"]
		self.quality_tiers = ['Normal', 'Good', 'Outstanding', 'Excellent', 'Masterpiece']

	@commands.command(aliases=["price", "p"])
	@timing
	async def prices(self, ctx, *, item=None):
		"""
		Gets the price of an item and its history
		Example usage: .p t6.1 hunter hood or .price t4  hide
		:param ctx:
		:param item:
		:return:
		"""
		if item is None:
			await ctx.send('Please enter an object to be searched:\n e.g  ```.p t6.1 hunter hood\n.price t4 hide ```')
			return

		item_w = item[0:]
		id_c = False

		# Id code detection
		if item_w in self.id_list:
			item_f = [(11, item) for item in self.dict if item['UniqueName'] == item_w]
			tier, enchant = feature_extraction(item_w)
			id_c = True

		# Search Processing --
		if not id_c:
			tier, enchant = feature_extraction(item_w)
			list_v = [s for s in self.dict if s['LocalizedNames'] is not None]
			if tier is not None:
				list_v = [x for x in list_v if f'T{tier[0]}' in x['UniqueName']]
				item_w = item_w.replace(f'T{tier[0]}', '')
			if enchant is not None:
				list_v = [x for x in list_v if f'@{enchant}' in x['UniqueName']]
				item_w = item_w.replace(f'.{enchant} ', '')

			item_f = await self.search_v2(item_w, list_v)
		item_name = item_f[0][1]['UniqueName']

		async with ctx.channel.typing():
			currurl = self.base_url_current + item_name + "?locations=" + f"{self.locations[0]}" + "".join(
				["," + "".join(x) for x in self.locations if x != self.locations[0]])
			full_hisurl = self.base_url + item_name + '?date=1-1-2020&locations=' + f"{self.locations[0]}" + "".join(
				["," + "".join(x) for x in self.locations if
				 x != self.locations[0]]) + f"&time-scale={self.scale}"
			print(item, item_name, full_hisurl)
			thumb_url = f"https://render.albiononline.com/v1/item/{item_name}.png?count=1&quality=1"

			current_prices = self.c_price_table(currurl)

			# Start embed object
			title = f"Item Data for {item_f[0][1]['LocalizedNames']['EN-US']} (Enchant:{enchant}) (ID: {item_f[0][1]['UniqueName']})"
			embed = Embed(title=title, url=f"https://www.albiononline2d.com/en/item/id/{item_name}")
			embed.set_thumbnail(url=thumb_url)
			best_cs_str = None

			# Initiate Avg price variables
			avg_price = []
			avg_current_price = []
			avg_sell_volume = []

			# Current Data
			# Current Data
			if len(current_prices[1].index) != 0:

				normalcheck = [str(x) for x in current_prices[1].T]
				if 'Normal' in normalcheck:
					avg_current_price = [x for x in current_prices[1].loc['Normal', :] if not math.isnan(x)]
					avg_cp = c_game_currency(int(average(avg_current_price)))
					embed.add_field(name="Avg Current Price (Normal)", value=avg_cp, inline=True)

			# Historical Data

			# Historical Data [Plotfile , Data]
			try:
				h_data = self.full_graph(full_hisurl, current_prices)
				for city in h_data[1]:
					avg_price.append(int(h_data[1][city]['avg_price'].mean()))
					avg_sell_volume.append((city, int(h_data[1][city]['item_count'].mean())))

				avg_p = c_game_currency(int(average(avg_price)))
				avg_sv = c_game_currency(int(average([x[1] for x in avg_sell_volume])))

				if len(avg_sell_volume) == 0:
					best_cs = (None, 0)
				else:
					best_cs = max(avg_sell_volume, key=lambda item: item[1])

				best_cs_str = f'{best_cs[0]} ({c_game_currency(best_cs[1])})'

				embed.add_field(name="Avg Historical Price (Normal)", value=avg_p, inline=True)
				embed.add_field(name="Avg Sell Volume", value=avg_sv, inline=True)

			except Exception as e:
				print(e)

			embed.set_footer(
				text=f"Best City Sales : {best_cs_str}\nSuggested Searches: {str([x[1]['LocalizedNames']['EN-US'] for x in item_f[1:4]]).replace('[', '').replace(']', '')}")

			if h_data[0] is not None:
				# Upload to discord
				today = date.today()
				filename = f'{today}'
				h_data[0].seek(0)
				file = File(h_data[0], filename=f"{filename}.png")
				h_data[0].close()
				embed.set_image(url=f"attachment://{filename}.png")
				await ctx.send(file=file, embed=embed)
			else:
				await ctx.send(embed=embed)
				await ctx.send(
					'```Error Fetching history, No data in the Albion Data Project directory.\nThis happens because no one has seen this item in the market with the albion data tool installed.``` To help us get more accurate results and more data please check out albion data project and install their client. \nhttps://www.albion-online-data.com/')

	def c_price_table(self, currurl):
		'''
		Generates an ASCII table with current price information
		:param currurl:
		:return:
		'''
		# Get Data
		cdata = get_data(currurl)

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
		frame2 = frame.apply(c_game_series, axis=0)
		frame2 = frame2.fillna('')

		return tabulate(frame, headers="keys", tablefmt="fancy_grid"), frame, frame2

	def full_graph(self, url, current_price_data):
		'''
		Generates an average price history chart and returns history data
		:param url:
		:return:
		'''
		# Get Data
		cdata = get_data(url)

		# PreProcess Json Data
		data = {}
		for city_obj in cdata:
			data[city_obj['location']] = pd.DataFrame(city_obj['data'])

		for city in data:
			data[city].timestamp = pd.to_datetime(data[city].timestamp)

		# Removing Outliers
		w_data = data.copy()
		for city in data:
			a = w_data[city]

			# Remove sets with less than 10 data points
			if a['avg_price'].size < 10:
				del w_data[city]
			else:
				# Remove values that do not lie within the 5% and 95% quantile
				w_data[city] = a[a['avg_price'].between(a['avg_price'].quantile(.1), a['avg_price'].quantile(.9))]

		sns.set(rc={'axes.facecolor': 'black', 'axes.grid': True, 'grid.color': '.1',
					'text.color': '.65', "lines.linewidth": 1})

		if len(w_data) != 0:
			no_plots = 2
			fig, ax = plt.subplots(1, no_plots, figsize=(20, 6))
			a1 = sns.heatmap(current_price_data[1], annot=current_price_data[2].to_numpy(), ax=ax[0], fmt='',
							 cbar=False)
			a1.set_xticklabels(a1.get_xticklabels(), rotation=30)
			a1.set_yticklabels(a1.get_yticklabels(), rotation=0)
		elif len(current_price_data[1].index) != 0:
			no_plots = 0
			fig, ax = plt.subplots(1, figsize=(20, 6))
			a1 = sns.heatmap(current_price_data[1], annot=current_price_data[2].to_numpy(), fmt='', cbar=False)
			a1.set_xticklabels(a1.get_xticklabels(), rotation=30)
			a1.set_yticklabels(a1.get_yticklabels(), rotation=0)
		else:
			return None, []

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

	async def search(self, name, list_v):
		"""
		Uses Jaro Winkler method to find the closest match for the input to a list of items.
		:param list_v:
		:param name:
		:return:
		"""
		if name in self.id_list:
			return [(11, item) for item in self.dict if item['UniqueName'] == name]
		else:
			rating = [[j.jaro_winkler_similarity(item_['UniqueName'].lower(), name.lower()), item_, None] for
					  item_ in list_v]
			for s in list_v:
				for language in s['LocalizedNames']:
					rating.append(
						[j.jaro_winkler_similarity(s['LocalizedNames'][language].lower(), name.lower()), s, language])

			rating.sort(key=sort_sim, reverse=True)
			most_likely_lang = rating[0][2]

			for nolang in [x for x in rating if x[2] is None]:
				nolang[2] = most_likely_lang
			return rating[0:5]

	async def search_v2(self, name, list_v):
		"""
		Improved search with better accuracy at the cost of speed,
		To reduce the speed cost multiple async tasks are used.
		:param name:
		:param list_v:
		:return:
		"""

		if name in self.id_list:
			return [(11, item) for item in self.dict if item['UniqueName'] == name]
		else:
			task_1 = (multi(term, name=name) for term in list_v)
			list_v2 = []
			for item in list_v:
				for language in item['LocalizedNames']:
					list_v2.append((item['LocalizedNames'][language].lower(), item))

			task_2 = (multi2(term, name=name) for term in list_v2)

			rating = await asyncio.gather(*task_1, return_exceptions=True)
			rating2 = await asyncio.gather(*task_2, return_exceptions=True)

			for item in rating2:
				rating.append(item)

			rating.sort(key=sort_sim, reverse=True)
			most_likely_lang = rating[0][2]

			for nolang in [x for x in rating if x[2] is None]:
				nolang[2] = most_likely_lang
			return rating[0:5]


def setup(client):
	client.add_cog(Market(client))
