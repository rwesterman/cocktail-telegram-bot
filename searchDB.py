import logging
from drinksSqlDb import query_drink_contains, get_ing_list, get_drink_session, close_session, query_ing_contains

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

    logging.debug(result_list)
    return result_list, session

def ing_search(ing_name):
    """Returns list of drinks that use given ingredient"""
    # list of drinks that use the ingredient
    use_list = []
    session = get_drink_session()
    # lstoflst_drinks is a list of lists containing drink objects
    lstoflst_drinks = query_ing_contains(ing_name, session)
    for lst in lstoflst_drinks:
        # lst.drinks is a list of Drink objects
        for drink in lst.drinks:
            # append each drink name to existing list
            use_list.append(drink.drink_name)
    logging.debug("Resulting list from ing_search: {}".format(use_list))
    close_session(session)
    return use_list


def recipe_string(recipe, session):
    """Takes recipe (instance of Drink), and builds string for output"""
    botString = "{} is found on page {}:\n".format(recipe.drink_name, recipe.page)
    botString += '\n'.join(get_ing_list(recipe)).title()
    # If the drink has a garnish, add it to the bottom of the string
    if recipe.garnishes:
        logging.debug("return from Drink.garnishes: {}".format(recipe.garnishes))
        botString += "\nGarnish with {}".format(recipe.garnishes[0].gar.title())
    logging.debug("botstring output: {}".format(botString))
    return botString

#
#
# if __name__ == '__main__':
#     logging.basicConfig(level = logging.DEBUG)
