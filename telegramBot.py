#! python3

# Todo: Add "Admin" accounts and functionality. Create /admin command and require password, then mark user as admin
# Allow admin accounts to do things like add drinks to table. Can make a prompt to add drinks and ingredients from phone?

import logging

from telegram import ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, Filters

import drinksSqlDb
import userSqlDb
import searchDB

from readJSON import Secrets, Loggers

# set state paths to integer numbers starting at 0
RECIPE, EXIT = range(2)  # Used for /drinks command conversation (recipe_helper)
USER_PERMISSION, ALLOW_TRACKING, USER_SETUP = range(3)  # Used for user /start conversation
ADD, REMOVE = range(2)
INV, ADD_INV, REM_INV = range(3)


def start(bot, update):
    user = update.message.from_user
    bot.send_message(chat_id=update.message.chat_id,
                     text="Hello {}, let's get started\n"
                          "You can type the command '/help' "
                          "at any time to see a list of my commands.".format(user.first_name))
    # help(bot, update)
    # Check to see if user is already in database
    chk_usr, session = userSqlDb.check_for_user_id(user.id)
    if not chk_usr:
        bot.send_message(chat_id=update.message.chat_id,
                         text="Now I'm going to ask for permission to track your data (Username, Telegram User ID).\n"
                              "This data will be used to keep track of your inventory and a list of your favorite drinks,"
                              "and it will be required to use some of my features.\n"
                              "Please type 'Yes' to give permission or 'No' to refuse")
        return USER_PERMISSION
    # If the user is already in the database, then end the conversation handler and don't send prompts
    else:
        info_log.debug("User already added to database")
        info_log.debug("User data: {}".format(chk_usr))
        return ConversationHandler.END


def setup_permission(bot, update):
    # Get user response to tracking permission
    text = update.message.text
    user = update.message.from_user
    if "yes" in text.lower():
        bot.send_message(chat_id=update.message.chat_id,
                         text="Thanks! I will now begin storing your data. This will allow you to use the following commands:\n"
                              "/inv to fill in your inventory, /fav to get the recipes for your favorite drinks, and "
                              "/makeable to see a list of drinks that you can make with your current inventory")

        store_user_data(bot, user, update.message.chat_id)
        return ConversationHandler.END

    # User refused tracking at this time
    elif "no" in text.lower():
        bot.send_message(chat_id=update.message.chat_id,
                         text="You have refused tracking. This will limit the commands that I am capable of using for you. "
                              "If you decide to allow tracking, you can send the /start command and go through this process again.")
        return ConversationHandler.END

    else:
        bot.send_message(chat_id=update.message.chat_id, text="Please respond either Yes or No")
        return USER_PERMISSION


def store_user_data(bot, user, chat_id):
    session = userSqlDb.add_user(user_id=user.id, first_name=user.first_name, last_name=user.last_name, chat_id=chat_id)
    if userSqlDb.check_for_user_id(user.id):
        info_log.info("Added user to database."
                      "\nFirst Name: {}\nLast Name: {}\nUser ID: {}".format(user.first_name, user.last_name, user.id))
        bot.send_message(chat_id=chat_id, text="Your username and ID have been added to the database")


def add_fav_command(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="You have chosen to add a drink to your favorites list. "
                          "Please respond with the drink you want to add or type 'exit' to quit")
    return ADD


def add_fav_drink(bot, update):
    """
    This method adds one drink to a user's favorites list
    :param bot:
    :param update:
    :return:
    """
    drnk_session = drinksSqlDb.get_drink_session()
    # If drink is exact match, adds drink and prompts to add another
    check_text = update.message.text
    chat_user = update.message.from_user

    # If LIKE search gives a match, add it to the database
    drink_exists = drinksSqlDb.query_drink_first(check_text, drnk_session)[0] # Only take first return item
    drink_contain = drinksSqlDb.query_drink_contains(check_text, drnk_session)[0]
    if drink_exists:
        user, usr_session = userSqlDb.check_for_user_id(chat_user.id)
        userSqlDb.set_user_favorite(user, drink_exists.drink_name, usr_session)
        bot.send_message(chat_id=update.message.chat_id,
                         text="Great! I've added {} to your favorites".format(drink_exists.drink_name))
        # Close the session now that the drink has been added
        drnk_session.close()
        usr_session.close()
        return ConversationHandler.END
    # If the text isn't close enough for a LIKE search, try a contains search, and show results
    elif drink_contain:
        suggestions = []
        # Extract drink name from list and output through bot message
        for drink in drink_contain:
            suggestions.append(drink.drink_name)
        info_log.debug(suggestions)
        message = "Did you mean to send one of these drinks?:\n{}" \
                  "\nIf so, please send the drink name again, or type 'exit' to leave".format(
            "\n".join(suggestions).title())
        bot.send_message(chat_id=update.message.chat_id, text=message)

        return ADD
    else:
        bot.send_message(chat_id=update.message.chat_id, text="Sorry, I was unable to find a drink that matched")
        drnk_session.close()
        return ConversationHandler.END

def rem_fav_command(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="You have chosen to remove a drink to your favorites list. "
                          "Please respond to this message with the name of the drink you'd like to remove, "
                          "or send 'exit' to stop")

    return REMOVE

def rem_fav_drinks(bot, update):
    chat_id = update.message.chat_id
    drink_name = update.message.text
    user, usr_sess = validate_user(bot, update)
    if not user:
        return ConversationHandler.END
    try:
        userSqlDb.rem_user_favorites(user, usr_sess, drink_name)
        bot.send_message(chat_id = chat_id, text = "Removed {} from your favorites".format(drink_name.title()))
    except ValueError as e:
        bot.send_message(chat_id = chat_id,
                         text = "{} is not in your favorites list. "
                                "Please send another drink name or type 'exit' to stop".format(drink_name.title()))
        return REMOVE

    return ConversationHandler.END


def validate_user(bot, update):
    try:
        user, session = userSqlDb.check_for_user_id(update.message.from_user.id)
        return user, session
    except TypeError as e:
        # Will receive TypeError if the check_for_user_id fails to return a user, NoneType not iterable
        warn_log.warning("User is not in the user database, needs to be added to use this functionality")
        user_not_added(bot, update)
        return "", ""


def user_not_added(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="You have not been added to the user database, so this command is currently unavailable."
                          "\nIf you want to use this function, please send the '/start' command and allow "
                          "tracking your user info.")


def manage_inv(bot, update):
    """Entry point to conversation handler to manage inventory. Prompts user to send 'add', 'remove', or 'list' """
    bot.send_message(chat_id=update.message.chat_id,
                     text="You've chosen to manage your inventory. Please respond with one of the following options:"
                          "\n'add' - Add items to your inventory"
                          "\n'rem' - Remove items from your inventory"
                          "\n'list' - See a list of items currently in your inventory"
                          "\n'exit' - Exit this prompt")
    return INV


def add_user_inv(bot, update):
    """ ConversationHandler state that allows adding to user's inventory log."""
    user, usr_sess = validate_user(bot, update)
    # if user isn't in database, return from command
    if not user:
        return ConversationHandler.END

    msg_txt = update.message.text
    drnk_session = drinksSqlDb.get_drink_session()
    # if the message simply says 'add', then send the inital bot message prompting them for the ingredient
    if msg_txt.lower() == "add" or msg_txt.lower() == "/addinv":
        bot.send_message(chat_id=update.message.chat_id,
                         text="You've chosen to add to your inventory. Please respond with the item you want to add."
                              " When you are finished, respond 'exit' to exit.")
        return ADD_INV
    # if message text doesn't just say 'add', then try adding the ingredients that the user sent
    else:
        # sanitize the input, then add it to the inventory if it matches
        check_ing = drinksSqlDb.verify_ing_for_inv(msg_txt, drnk_session)

        # if check_ing is empty sting, then the user input doesn't match an ingredient.
        # next test is to see if it's similar to anything and display that to the user
        if not check_ing:
            # similar_ing will hold the ingredient names to send the user as suggestions
            similar_ing = []
            for ingredient in drinksSqlDb.ing_contains_all(msg_txt, drnk_session):
                similar_ing.append(ingredient.ing.title())
            for simple in drinksSqlDb.simple_contains_all(msg_txt, drnk_session):
                similar_ing.append(simple.ing.title())
            # If similar ingredients were found, send a list of them to user
            if similar_ing:
                bot_text = "No ingredient uses that name. Did you mean one of the following?\n" \
                           "{}".format("\n".join(similar_ing))
            # If none, found, prompt user to try again or type exit to leave the interaction
            else:
                bot_text = "Sorry, couldn't find any ingredients with similar names. Please try again or type exit to leave"
            bot.send_message(chat_id=update.message.chat_id,
                             text=bot_text)
            return ADD_INV

        # if check_ing does exist, it means there was a direct match. Add this to inventory and tell user
        elif check_ing:
            userSqlDb.add_inventory(user, check_ing, usr_sess)
            bot.send_message(chat_id=update.message.chat_id,
                             text="Added {} to your inventory\n"
                                  "Continue sending inventory items to add, "
                                  "or type 'exit' to stop".format(check_ing.title()))
            return ADD_INV


def rem_user_inv(bot, update):
    """ ConversationHandler state that allows removing from user's inventory log."""
    user, usr_sess = validate_user(bot, update)
    chat_id = update.message.chat_id
    # if user isn't in database, return from command
    if not user:
        return ConversationHandler.END

    msg_txt = update.message.text
    drnk_session = drinksSqlDb.get_drink_session()
    # if the message simply says 'rem', then send the inital bot message prompting them for the ingredient
    if msg_txt.lower() == "rem" or msg_txt.lower() == "/reminv":
        # Send user's current inventory through the bots
        bot.send_message(chat_id = chat_id, text = list_user_inv(user))

        # Initial prompt telling user to type the name of the item they want to remove
        bot.send_message(chat_id= chat_id, text="You've chosen to remove from  your inventory. "
                              "Please respond with the item you want to remove."
                              " When you are finished, respond 'exit' to exit.")
        return REM_INV

    else:
        try:
            userSqlDb.rem_inventory(user, usr_sess,msg_txt)
            bot.send_message(chat_id=chat_id,
                            text="Removing {} from inventory.".format(msg_txt.title()))
        except ValueError as e:
            warn_log.warning("{} is not in inventory, and can't be removed".format(msg_txt.title()))
            bot.send_message(chat_id = chat_id, text = "{} is not in your inventory".format(msg_txt.title()))
        finally:
            bot.send_message(chat_id = chat_id,
                             text = "Type another item to remove from your inventory. \n{}".format(list_user_inv(user)))

            return REM_INV


def list_inv_command(bot, update):
    """This is the bot callback function to list the user's inventory"""
    # message_text = update.message.text
    user, usr_sess = validate_user(bot, update)
    # If the user isn't inthe database, exit the loop
    if not user:
        return ConversationHandler.END

    # Call method to receive list of strings representing user's inventory
    bot_text = list_user_inv(user)
    bot.send_message(chat_id=update.message.chat_id, text=bot_text)

    # Testing this blank return statement to see if it exists the conversation handler
    return ConversationHandler.END

def list_user_inv(user):
    """Takes user and returns list of strings representing their inventory"""
    # user_stock is a list of Inventory objects
    user_stock = userSqlDb.get_user_inv(user)
    # stock_list holds the string values taken from Inventory objects
    stock_list = []
    for item in user_stock:
        stock_list.append(item.stock.title())
    bot_text = "Here is your current inventory:\n{}".format("\n".join(stock_list))
    info_log.debug(bot_text)
    return bot_text

def favorite_recipes(bot, update):
    # Todo: Send a list of recipes for each drink in the favorites list
    user, usr_session = validate_user(bot, update)
    if not user:
        return ConversationHandler.END

    user_favs = userSqlDb.get_user_favorites(user)
    # If user has not added any favorite drinks, return "No favorites found"
    if not user_favs:
        bot.send_message(chat_id=update.message.chat_id,
                         text="You haven't added any favorites yet. try typing /addfav to get started")
        usr_session.close()
        return ConversationHandler.END
    for fav in user_favs:
        # for each drink name in favorites, find the drink in the drinks database, then print the output
        recipe, drink_session = drinksSqlDb.query_drink_first(fav.favorites)
        bot_text = searchDB.recipe_string(recipe, drink_session)
        bot.send_message(chat_id=update.message.chat_id, text=bot_text)
    return ConversationHandler.END


def makeable(bot, update):
    user, usr_sess = validate_user(bot, update)
    if not user:
        return ConversationHandler.END
    # This will throw a TypeError if the user isn't added to the database first
    makeable_drink_set = makeable_from_inv(user, usr_sess)
    bot_text = "With your current inventory you can make {} drinks:\n".format(len(makeable_drink_set))
    bot_text += "\n".join(makeable_drink_set)
    info_log.debug("Bot message as follows: \n{}".format(bot_text))
    bot.send_message(chat_id=update.message.chat_id, text=bot_text)


def makeable_from_inv(user, usr_sess):
    # Create an empty set that will hold all drink possibilities
    # Initialize empty sets.
    drink_set = set()  # holds all drinks that use an ingredient from inventory
    simple_inventory = set()  # holds simplified inventory names

    # Create a set of simplified ingredients (Strings in uppercase)
    drink_sess = drinksSqlDb.get_drink_session()
    for item in user.stock:
        # ingredient_found is an Ingredient object associated with the user's inventory
        ingredient_found = drinksSqlDb.ing_contains_first(item.stock, drink_sess)
        # simple inventory simplifies this ingredient name for better searching
        simple_inventory.add(drinksSqlDb.simplify_ingredient(ingredient_found, drink_sess))

    # for each ingredient in inventory list, check what drinks can be
    for inv in simple_inventory:
        # call ing_search() to get every drink the ingredient shows up in
        # call set.update() on this to add distinct values
        drink_set.update(searchDB.ing_search(inv))

    # Return the set of Drink objects that can be made
    return compare_vs_inventory(drink_set, simple_inventory)


def compare_vs_inventory(drink_set, simple_inventory):
    """
    :param drink_set: a Set that contains names of drinks (not set of drink objects)
    :param simple_inventory: a Set that contains simplified inventory names
    :return: set of drink names (Strings)
    """
    # Subset approach won't work because inventory list is not exactly.
    # created a simplify table, associates to Ingredient objects. if given drink objects in set, I can replace ingredients
    # with their simple counterparts. This still might be slower than the simple nested for compare, since I'm having to
    # nest loops in order to make these replacements

    # Holds drinks that can be made
    final_drink_set = set()

    for current_drink in drink_set:
        # Initialize empty drink set for each drink that goes through this loop
        drink_ing_set = set()
        drink, drnk_session = drinksSqlDb.query_drink_first(current_drink)

        # Simplify the ingredients in the drink
        for ingredient in drink.ingredients:
            # Populate a set with the names of each ingredient (uppercase)
            drink_ing_set.add(drinksSqlDb.simplify_ingredient(ingredient, drnk_session))

        if drink_ing_set.issubset(simple_inventory):
            final_drink_set.add(drink.drink_name)
    info_log.debug("Found {} makeable drinks: {}".format(len(final_drink_set), final_drink_set))
    return final_drink_set


# use this to call drink_search with the arguments that are passed
def drinks(bot, update, args):
    # If user sent drink names, return drinks. Else, set drink_search to True
    if args:
        recipe_return(bot, update, args)
        return ConversationHandler.END
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Send up to four drink names (one word each), or send "Exit" to cancel')
        return RECIPE


def recipe_return(bot, update, args=""):
    # If the drink names are specified with the /drinks command, run the args given
    if args:
        find_recipes(bot, update, args)
    # If drinks are given in a separate message, split that message's contents and do the same action
    else:
        drinks_list = update.message.text.split(' ')
        find_recipes(bot, update, drinks_list)
    # End conversation handler after returning recipes
    return ConversationHandler.END


def find_recipes(bot, update, drinks_list):
    recipes, session = searchDB.drink_search(drinks_list)
    # If recipes is empty list, then send "No Recipes Found" message
    if not recipes:
        bot.send_message(chat_id=update.message.chat_id, text='Sorry, no recipes found for that name')
    else:
        for recipe in recipes:
            botString = searchDB.recipe_string(recipe, session)  # offset of zero for drinks call
            bot.send_message(chat_id=update.message.chat_id, text=botString)


def ing(bot, update, args):
    ing_name = ' '.join(args)
    bot.send_message(chat_id=update.message.chat_id, text="Searching for drinks that use {}".format(ing_name))
    drink_list = searchDB.ing_search(ing_name)
    bot.send_message(chat_id=update.message.chat_id, text='\n'.join(drink_list))


def help(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="Here are the available commands:"
                          "\n/drinks - send a drink name and get recipe"
                          "\n/ing - Returns list of drinks that use an ingredient"
                          "\n*/inv - Manage your drink inventory*"
                          "\n*/makeable - Show which drinks you can make with your inventory ingredients*"
                          "\n*/fav - Manage your favorite drinks, and get recipes for those you make most often"
                          "\n\n* Commands with an asterisk are only accessible if you have allowed your user data "
                          "to be tracked. If you want to allow this, send the command '/start' and "
                          "allow tracking.")


def exit_list(bot, update):
    update.message.reply_text('Bye!', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def kill(bot, update, args):
    info_log.info('Process stopped')
    updater.stop()


def create_handlers(updater, dispatcher):
    help_handler = CommandHandler('help', help)
    dispatcher.add_handler(help_handler)
    updater.start_polling()

    ing_handler = CommandHandler('ing', ing, pass_args=True)
    dispatcher.add_handler(ing_handler)

    kill_handler = CommandHandler('kill', kill, pass_args=True)
    dispatcher.add_handler(kill_handler)

    makeable_handler = CommandHandler('makeable', makeable)
    dispatcher.add_handler(makeable_handler)

    # Begin conversation with start command to introduce new user to bot functionality
    start_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            # USER_PERMISSION lets user accept or deny tracking their data
            USER_PERMISSION: [MessageHandler(Filters.text, setup_permission)],
            # ALLOW_TRACKING:[CallbackQueryHandler()]
        },
        fallbacks=[MessageHandler(Filters.text, exit_list)]
    )
    dispatcher.add_handler(start_handler)

    # Setting up recipe_handler to return drink recipes in two steps. First send /drinks,
    # then you'll get a response from the bot asking to send up to four words to search for recipes
    # Any response will go to RECIPES state, but if the response contains "Exit", the process will be aborted
    recipe_handler = ConversationHandler(
        entry_points=[CommandHandler('drinks', drinks, pass_args=True)],
        # Want to use update.message.text, this will return the full text. Can split it from here.
        states={
            # Only state is RECIPE for now, but it first searches to see if "exit" was sent, then returns drinks if not
            RECIPE: [MessageHandler(filters=Filters.regex("[eE]xit"), callback=exit_list),
                     MessageHandler(filters=Filters.text, callback=recipe_return)],
        },
        fallbacks=[MessageHandler(filters=Filters.regex("[eE]xit"), callback=exit_list)]
    )
    dispatcher.add_handler(recipe_handler)

    fav_handler = ConversationHandler(
        entry_points=[CommandHandler('addfav', add_fav_command), CommandHandler('remfav', rem_fav_command),
                      CommandHandler('fav', favorite_recipes)],
        states={
            # ADD state can either go through once and end, exit with command, or loop back to itself
            ADD: [MessageHandler(filters=Filters.regex("[eE]xit"), callback=exit_list),
                  MessageHandler(filters=Filters.text, callback=add_fav_drink)],
            REMOVE: [MessageHandler(filters=Filters.regex("[eE]xit"), callback=exit_list),
                     MessageHandler(filters = Filters.text, callback = rem_fav_drinks)],
        },
        fallbacks=[MessageHandler(filters=Filters.regex("[eE]xit"), callback=exit_list)]
    )
    dispatcher.add_handler(fav_handler)

    inv_handler = ConversationHandler(
        entry_points=[CommandHandler('inv', manage_inv), CommandHandler('addinv', add_user_inv),
                      CommandHandler('reminv', rem_user_inv), CommandHandler('listinv', list_inv_command)],
        states={
            INV: [MessageHandler(filters=Filters.regex("[eE]xit"), callback=exit_list),
                  MessageHandler(filters=Filters.regex("[aA]dd"), callback=add_user_inv),
                  MessageHandler(filters=Filters.regex("[rR]em"), callback=rem_user_inv),
                  MessageHandler(filters=Filters.regex("[lL]ist"), callback=list_inv_command)],

            # Call to add_user_inv will repeat until user sends 'exit'
            ADD_INV: [MessageHandler(filters=Filters.regex("[eE]xit"), callback=exit_list),
                      MessageHandler(filters=Filters.text, callback=add_user_inv)],

            REM_INV: [MessageHandler(filters=Filters.regex("[eE]xit"), callback=exit_list),
                      MessageHandler(filters=Filters.text, callback=rem_user_inv)]
        },
        fallbacks=[MessageHandler(filters=Filters.regex("[eE]xit"), callback=exit_list)])
    dispatcher.add_handler(inv_handler)


if __name__ == '__main__':
    # Setup specific loggers from config.json
    setup_loggers = Loggers()
    setup_loggers.setup_logging(default_level=logging.INFO)

    # Setup default logger. telegram python module uses this, mostly at DEBUG level
    # This sets a root logger, which will cause duplicate outputs on all other logs while active.
    # Only use this to monitor telegram-python-bot debug messages
    # logging.basicConfig(level = logging.DEBUG, format= "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Get loggers from config.json setup, add file name to output for traceability
    info_log = logging.getLogger("info." + __name__)
    warn_log = logging.getLogger("warn." + __name__)

    info_log.info("Launching telegramBot.py now")
    # toggle this to show/hide debug level logs
    # info_log.setLevel(logging.DEBUG)

    auth = Secrets()
    # Bottender Token
    token = auth.bottender_token

    # Debugbot Token
    # token = auth.debug_token

    updater = Updater(token=token)  # pass bot api token
    dispatcher = updater.dispatcher

    # This method creates and adds all handlers for the bot
    create_handlers(updater, dispatcher)

    updater.idle()
    print('Idle Signal Received')
