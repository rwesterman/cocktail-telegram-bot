import logging
from drinksSqlDb import query_drink_contains, get_formatted_ingredients, get_drink_session, close_session, ing_contains_all

log = logging.getLogger("info." + __name__)

def drink_search(drink_list):
    """Returns Drink objects corresponding to searched drink names"""
    # Start a new SQL session, pass it as return
    session = get_drink_session()
    result_list = []

    # Number of drinks is currently capped at 4
    num_drinks = min(len(drink_list), 4)

    # If no drink names sent, return empty string
    if num_drinks == 0:
        close_session(session)
        return []

    # Iterate through all the searched drinks (or at least the first four)
    for index in range(num_drinks):
        # Get a list of drink names that contain the searched term for each index
        # session remains consistent throughout this loop
        recipe, session = query_drink_contains(drink_list[index], session)
        # list.extend concatenates the list so it's one dimensional
        result_list.extend(recipe)

    log.debug(result_list)
    return result_list, session

def ing_search(ing_name):
    """Returns list of drinks that use given ingredient"""
    # list of drinks that use the ingredient
    use_list = []
    session = get_drink_session()
    # lstoflst_drinks is a list of lists containing drink objects
    lstoflst_drinks = ing_contains_all(ing_name, session)
    for lst in lstoflst_drinks:
        # lst.drinks is a list of Drink objects
        for drink in lst.drinks:
            # append each drink name to existing list
            use_list.append(drink.drink_name)
    log.debug("{} results for ingredient {}: {}".format(len(use_list), ing_name, use_list))
    close_session(session)
    return use_list


def recipe_string(recipe, session):
    """Takes recipe (instance of Drink), and builds string for output"""
    botString = "{} is found on page {}:\n".format(recipe.drink_name, recipe.page)
    botString += '\n'.join(get_formatted_ingredients(recipe)).title()
    # If the drink has a garnish, add it to the bottom of the string
    if recipe.garnishes:
        log.debug("return from Drink.garnishes: {}".format(recipe.garnishes))
        botString += "\nGarnish with {}".format(recipe.garnishes[0].gar.title())
    log.debug("botstring output: {}".format(botString))
    return botString
