import logging

from libs.complied_libs.optimized_libs import simple_distance_algorithm

log = logging.getLogger(__name__)


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
        score = simple_distance_algorithm(name, item_languages[0])
        if score != 0:
            found_list.append((item_languages[1], score))

    found_list = sorted(found_list, key=lambda tup: tup[1], reverse=True)
    suggestions = get_suggestions(found_list)
    return {"suggestions": suggestions, "tier": tier, "enchant": enchant}
