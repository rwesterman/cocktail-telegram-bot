#! python3

import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, Filters

import drinksSqlDb
import userSqlDb
import searchDB

# set state paths to integer numbers starting at 0
RECIPE, EXIT = range(2) # Used for /drinks command conversation (recipe_helper)
USER_PERMISSION, ALLOW_TRACKING,USER_SETUP = range(3) # Used for user startup conversation to track user data (start_helper)
ADD, REMOVE = range(2)

conv_keyboard = [['/Return', '/Exit']]
liquorLoopKeyboard = ReplyKeyboardMarkup(conv_keyboard, one_time_keyboard=True)

def start(bot, update):
    user = update.message.from_user
    bot.send_message(chat_id=update.message.chat_id,
                     text="Hello {}, let's get started"
                          "\nHere is a list of the commands I currently have implemented".format(user.first_name))
    help(bot,update)
    bot.send_message(chat_id=update.message.chat_id,
                     text ="You can type the command '/help' at any time to see a list of my commands.")

    # Check to see if user is already in database
    chk_usr, session= userSqlDb.check_for_user_id(user.id)
    if not chk_usr:
        bot.send_message(chat_id = update.message.chat_id,
                     text = "Now I'm going to ask for your permission to track your data (Username, Telegram User ID).\n"
                            "This data will only be used to keep track of your inventory and a list of your favorite drinks,"
                            "and it will be required to use some of my features.\n"
                            "Please type 'Yes' to give permission or 'No' to refuse")
        return USER_PERMISSION
    # If the user is already in the database, then end the conversation handler and don't send prompts
    else:
        logging.info("User already added to database")
        logging.info("User data: {}".format(chk_usr))
        return ConversationHandler.END

def setup_permission(bot, update):
    # Get user response to tracking permission
    text = update.message.text
    user = update.message.from_user
    if "yes" in text.lower():
        bot.send_message(chat_id = update.message.chat_id,
                         text = "Thanks! I will now begin monitoring your data. This will allow you to use the following commands:\n"
                                "/inv to fill in your inventory, /fav to get the recipes for your favorite drinks, and "
                                "/onhand to see a list of drinks that you can make with your current inventory\n\n"
                                "Please be patient as these commands are added and updated")

        store_user_data(bot, user, update.message.chat_id)
        return ConversationHandler.END
        # return ALLOW_TRACKING

    # User refused tracking at this time
    elif "no" in text.lower():
        bot.send_message(chat_id = update.message.chat_id,
                         text = "You have refused tracking. This will limit the commands that I am capable of using for you. "
                                "If you decide to allow tracking, you can send the /start command and go through this process again.")
        return ConversationHandler.END

    else:
        bot.send_message(chat_id = update.message.chat_id, text="Please respond either Yes or No")
        return USER_PERMISSION

def store_user_data(bot, user, chat_id):
    session = userSqlDb.add_user(user_id = user.id, first_name=user.first_name, last_name= user.last_name, chat_id= chat_id)
    if userSqlDb.check_for_user_id(user.id):
        bot.send_message(chat_id = chat_id, text = "Your username and ID have been added to the database")

def add_fav_command(bot, update):
    # Todo: Check that user is being tracked (in user database), if not, offer to add them or exit
    bot.send_message(chat_id = update.message.chat_id,
                     text = "You have chosen to add a drink to your favorites list. "
                            "Please respond with the drink you want to add or type 'exit' to quit")
    return ADD

def add_fav_drink(bot,update):
    """
    This method adds one drink to a user's favorites list
    :param bot:
    :param update:
    :return:
    """
    logging.debug("Reached add_fav_drink")
    drnk_session = drinksSqlDb.get_session()
    # If drink is exact match, adds drink and prompts to add another
    check_text = update.message.text
    chat_user = update.message.from_user

    # If LIKE search gives a match, add it to the database
    drink_exists= drinksSqlDb.query_drink_first(check_text, drnk_session)[0] #index 0 of tuple is first return, Drink object
    drink_contain = drinksSqlDb.query_drink_contains(check_text, drnk_session)[0]
    if drink_exists:
        user, usr_session = userSqlDb.check_for_user_id(chat_user.id)
        userSqlDb.set_user_favorite(user,drink_exists.drink_name,usr_session)
        bot.send_message(chat_id = update.message.chat_id,
                         text = "Great! I've added {} to your favorites".format(drink_exists.drink_name))
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
        logging.debug(suggestions)
        message = "Did you mean to send one of these drinks?:\n{}" \
                  "\nIf so, please send the drink name again, or type 'exit' to leave".format("\n".join(suggestions))
        bot.send_message(chat_id = update.message.chat_id, text = message)

        return ADD
    else:
        bot.send_message(chat_id = update.message.chat_id, text = "Sorry, I was unable to find a drink that matched")
        drnk_session.close()
        return ConversationHandler.END


def rem_fav_command(bot,update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="You have chosen to remove a drink to your favorites list.")
    return REMOVE

def favorite_recipes(bot,update):
    # Todo: Send a list of recipes for each drink in the favorites list
    chat_user = update.message.from_user
    user, session = userSqlDb.check_for_user_id(chat_user.id)
    user_favs = userSqlDb.get_user_favorites(user)
    # If user has not added any favorite drinks, return "No favorites found"
    if not user_favs:
        bot.send_message(chat_id = update.message.chat_id,
                         text = "You haven't added any favorites yet. try typing /addfav to get started")
        session.close()
        return ConversationHandler.END
    for fav in user_favs:
        # for each drink name in favorites, find the drink in the drinks database, then print the output
        recipe = drinksSqlDb.query_drink_first(fav.favorites, session)[0] #first return is drink name, so index 0
        bot_text = searchDB.recipe_string(recipe, session)
        bot.send_message(chat_id = update.message.chat_id, text = bot_text)
    return ConversationHandler.END


# This is passed a list of strings in variable args
# use this to call drink_search with the arguments that are passed
def drinks(bot, update, args):
    #If user sent drink names, return drinks. Else, set drink_search to True
    if args:
        recipe_return(bot, update, args)
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
        find_recipes(bot,update,drinks_list)
    # End conversation handler after returning recipes
    return ConversationHandler.END

def find_recipes(bot, update, drinks_list):
    recipes, session = searchDB.drink_search(drinks_list)
    if recipes == []:
        bot.send_message(chat_id=update.message.chat_id, text='Sorry, no recipes found for that name')
    else:
        for recipe in recipes:
            botString = searchDB.recipe_string(recipe, session)  # offset of zero for drinks call
            bot.send_message(chat_id=update.message.chat_id, text=botString)


def ing(bot, update, args):
    ing_name = ' '.join(args)
    bot.send_message(chat_id = update.message.chat_id, text = "Searching for drinks that use {}".format(ing_name))
    drink_list = searchDB.ing_search(ing_name)
    bot.send_message(chat_id = update.message.chat_id, text = '\n'.join(drink_list))

def help(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='Here are the available commands:'
                                                          '\n/drinks - send a drink name and get recipe'
                                                          '\n/ing - Returns list of drinks that use an ingredient'
                                                          '\n\nMore commands coming soon!')

def exit_list(bot, update):
    update.message.reply_text('Bye!', reply_markup = ReplyKeyboardRemove())
    return ConversationHandler.END

def kill(bot, update, args):
    logging.info('Process stopped')
    updater.stop()

def create_handlers(updater, dispatcher):
    help_handler = CommandHandler('help', help)
    dispatcher.add_handler(help_handler)
    updater.start_polling()

    ing_handler = CommandHandler('ing', ing, pass_args=True)
    dispatcher.add_handler(ing_handler)

    kill_handler = CommandHandler('kill', kill, pass_args=True)
    dispatcher.add_handler(kill_handler)

    # random_handler = CommandHandler('random', list_random, pass_args= True)
    # dispatcher.add_handler(random_handler)

    # Begin conversation with start command to introduce new user to bot functionality
    start_handler = ConversationHandler(
        entry_points= [CommandHandler('start', start)],
        states={
            # USER_PERMISSION lets user accept or deny tracking their data
            USER_PERMISSION:[MessageHandler(Filters.text,setup_permission)],
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
        fallbacks=[CallbackQueryHandler(exit_list),
                   MessageHandler(filters=Filters.regex("[eE]xit"), callback=exit_list)]
    )
    dispatcher.add_handler(recipe_handler)

    fav_handler = ConversationHandler(
        entry_points=[CommandHandler('addfav', add_fav_command), CommandHandler('remfav', rem_fav_command),
                      CommandHandler('fav', favorite_recipes)],
        # Todo: Fill out states here to allow removing and adding favorites. Maybe add a list fave drinks option as well
        states = {
            # ADD state can either go through once and end, exit with command, or loop back to itself
            ADD:[MessageHandler(filters = Filters.regex("[eE]xit"), callback=exit_list),
                 MessageHandler(filters = Filters.text, callback = add_fav_drink)],
            REMOVE:[MessageHandler(filters = Filters.regex("[eE]xit"), callback=exit_list)],
        },
        fallbacks = [MessageHandler(filters = Filters.regex("[eE]xit"), callback=exit_list)]
    )
    dispatcher.add_handler(fav_handler)


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Bottender Token
    token = '391638807:AAGqCR37_1y9uxMTZfAlnKromKhS0J0XsZc'

    # Debugbot Token
    # token = '563248703:AAGiRYnpZ_vFuG_ycowZ4qRH7vt63Wc3j58'
    global updater
    updater = Updater(token=token)  # pass bot api token
    dispatcher = updater.dispatcher

    # This method creates and adds all handlers for the bot
    create_handlers(updater, dispatcher)

    updater.idle()
    print('Idle Signal Received')

if __name__ == '__main__':
    main()