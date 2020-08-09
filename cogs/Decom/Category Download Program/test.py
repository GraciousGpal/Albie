import json

import requests
from bs4 import BeautifulSoup

# Opening JSON file
f = open('data.json')
import re

# returns JSON object as
# a dictionary
data = json.load(f)

rootdir = 'https://www.albiononline2d.com'

DataStore = {}
for entries in data['categoriesTree']:
	if entries['text'] == 'Resource':
		for types in entries['nodes']:
			httpdoc = requests.get(rootdir + types['href'])
			bs = BeautifulSoup(httpdoc.content, 'html.parser')
			data = bs.find_all("script")[29].string
			p = re.compile('var config = (.*?);')
			m = p.match(data)
			DataStore[types['id']] = json.loads(m.groups()[0])['itemsForMarketData']

print(DataStore)
with open('category.json', 'w') as f:
	json.dump(DataStore, f, indent=4)

# Closing file
f.close()
