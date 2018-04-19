#! python3

import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, Filters

import userSqlDb
import searchDB
# set state paths to integer numbers starting at 0

CHOOSE, LOOP = range(2) # Used for liquor_helper conversation
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
    if not userSqlDb.check_for_user_id(user.id):
        bot.send_message(chat_id = update.message.chat_id,
                     text = "Now I'm going to ask for your permission to track your data (Username, Telegram User ID).\n"
                            "This data will only be used to keep track of your inventory and a list of your favorite drinks,"
                            "and it will be required to use some of my features.\n"
                            "Please type 'Yes' to give permission or 'No' to refuse")
        return USER_PERMISSION
    # If the user is already in the database, then end the conversation handler and don't send prompts
    else:
        logging.info("User already added to database")
        logging.info("User data: {}".format(userSqlDb.check_for_user_id(user.id)))
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
    bot.send_message(chat_id = update.message.chat_id,
                     text = "You have chosen to add a drink to your favorites list. "
                            "Please respond with the drink you want to add or type 'exit' to quit")

def rem_fav_command(bot,update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="You have chosen to remove a drink to your favorites list.")
    return REMOVE

def favorite_recipes(bot,update):
    # Todo: Send a list of recipes for each drink in the favorites list
    # This can be done by modifying the drinks method to accept multi-word search terms, or else it could be done manually
    ...


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
        entry_points=[CommandHandler('addfav', add_fav_command), CommandHandler('remfav', rem_fav_command)],
        # Todo: Fill out states here to allow removing and adding favorites. Maybe add a list fave drinks option as well
        states = {
            ADD:[MessageHandler(filters = Filters.regex("[eE]xit"), callback=exit_list), ],
            REMOVE:[MessageHandler(filters = Filters.regex("[eE]xit"), callback=exit_list)],
        },
        fallbacks = [MessageHandler(filters = Filters.regex("[eE]xit"), callback=exit_list)]
    )
    dispatcher.add_handler(fav_handler)

    # Todo: Fillout favorite_recipes method to list each drink in favorites
    fav_recipe_handler = CommandHandler('fav', favorite_recipes)
    dispatcher.add_handler(fav_recipe_handler)


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Bottender Token
    # token = '391638807:AAGqCR37_1y9uxMTZfAlnKromKhS0J0XsZc'

    # Debugbot Token
    token = '563248703:AAGiRYnpZ_vFuG_ycowZ4qRH7vt63Wc3j58'
    global updater
    updater = Updater(token=token)  # pass bot api token
    dispatcher = updater.dispatcher

    # This method creates and adds all handlers for the bot
    create_handlers(updater, dispatcher)

    updater.idle()
    print('Idle Signal Received')

if __name__ == '__main__':
    main()