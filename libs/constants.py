from discord import Embed
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