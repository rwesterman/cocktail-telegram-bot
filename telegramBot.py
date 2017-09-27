#! python3

#Todo: user_data
import logging, dropbox
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

import searchSS
#from cocktails import dropbox_init

CHOOSE, LOOP = range(2)
conv_keyboard = [['/Return', '/Exit']]
liquorLoopKeyboard = ReplyKeyboardMarkup(conv_keyboard, one_time_keyboard=True)


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, play with me!")


# This is passed a list of strings in variable args
# use this to call drink_search with the arguments that are passed
def drinks(bot, update, args):
    df, sh = searchSS.sheetsInit()
    recipes = searchSS.drink_search(df, args)
    if recipes == []:
        bot.send_message(chat_id=update.message.chat_id, text='Sorry, no recipes found for that name')
    else:
        for recipe in recipes:
            botString = searchSS.recipe_string(recipe, 0)       #offset of zero for drinks call
            bot.send_message(chat_id=update.message.chat_id, text=botString)

def ing(bot, update, args):
    ing_name = ' '.join(args)
    bot.send_message(chat_id = update.message.chat_id, text = "Searching for drinks that use {}".format(ing_name))
    drink_list = searchSS.ing_search(df, ing_name)
    bot.send_message(chat_id = update.message.chat_id, text = '\n'.join(drink_list))



def help(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='Here are the available commands:'
                                                          '\n/help - Lists available commands'
                                                          '\n/drinks - send a drink name and get recipe'
                                                          '\n/list - Returns list of drink names for given liquor'
                                                          '\n\nMore commands coming soon!')


def listRandom(bot, update, args):
    """This function will send X random receipes, where X is the number following the command signal"""
    #bot.send_message(chat_id = update.message.chat_id, text = 'This is a heartbeat')    #Check to see that function is called


    #Start by checking for acceptable input after /random

    try:
        number = int(args[0])           #test not passing an argument
    except IndexError:
        number = 5
    if number > 10:
        number = 10
    elif number < 1:                #Don't allow negative or zero numbers
        number = 1

    df, sh = searchSS.sheetsInit()  #Reinitialize the dataframe to avoid failures

    randRecipes = searchSS.get_random(df, number)
    

    for recipe in randRecipes:
        botString = searchSS.recipe_string(recipe, 0)           #Fix this number
        bot.send_message(chat_id=update.message.chat_id, text=botString)

#def dbxInit(bot, update):
#    dropbox_init()




def listDrinks(bot, update):
    baseLiquorKeyboard = [['/Whiskey', '/Gin'],
                          ['/Tequila', '/Brandy']]
    reply_markup = ReplyKeyboardMarkup(baseLiquorKeyboard, one_time_keyboard= True)
    bot.send_message(chat_id= update.message.chat_id, text = "I'll help you find cocktail names, but first, what base liquor are you interested in?", reply_markup = reply_markup)

    return CHOOSE

def whiskey(bot,update):
    #write function to return all whiskey drink names in a list
    #join them as a string with '\n' as the divider
    #output as text from Bot
    #df, sh = searchSS.sheetsInit()
    drink_names = searchSS.base_liquor('Whiskey',sh)
    bot.send_message(chat_id = update.message.chat_id, text = 'Here is a list of whiskey drinks:\n' + '\n'.join(drink_names), reply_markup = liquorLoopKeyboard)

    return LOOP

def tequila(bot, update):
    # write function to return all tequila drink names in a list
    # join them as a string with '\n' as the divider
    # output as text from Bot
    df, sh = searchSS.sheetsInit()
    drink_names = searchSS.base_liquor('Agave', sh)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Here is a list of tequila drinks:\n' + '\n'.join(drink_names),
                     reply_markup=liquorLoopKeyboard)

    return LOOP

def gin(bot, update):
    # write function to return all Gin drink names in a list
    # join them as a string with '\n' as the divider
    # output as text from Bot
    df, sh = searchSS.sheetsInit()
    drink_names = searchSS.base_liquor('Gin', sh)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Here is a list of gin drinks:\n' + '\n'.join(drink_names),
                     reply_markup=liquorLoopKeyboard)

    return LOOP

def brandy(bot, update):
    # write function to return all Brandy drink names in a list
    # join them as a string with '\n' as the divider
    # output as text from Bot
    df, sh = searchSS.sheetsInit()
    drink_names = searchSS.base_liquor('Brandy', sh)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Here is a list of brandy drinks:\n' + '\n'.join(drink_names),
                     reply_markup=liquorLoopKeyboard)

    return LOOP

def exitList(bot,update):
    update.message.reply_text('Bye!', reply_markup = ReplyKeyboardRemove())
    return ConversationHandler.END

def kill(bot, update, args):
    logging.info('Process stopped')
    updater.stop()


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # constants located here
    token = '391638807:AAGqCR37_1y9uxMTZfAlnKromKhS0J0XsZc'
    global updater
    updater = Updater(token=token)  # pass bot api token
    dispatcher = updater.dispatcher
    global df
    df, sheet = searchSS.sheetsInit()

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    updater.start_polling()

    drinks_handler = CommandHandler('drinks', drinks, pass_args=True)
    dispatcher.add_handler(drinks_handler)

    help_handler = CommandHandler('help', help)
    dispatcher.add_handler(help_handler)

    ing_handler = CommandHandler('ing', ing, pass_args= True)
    dispatcher.add_handler(ing_handler)

    kill_handler = CommandHandler('kill', kill, pass_args = True)
    dispatcher.add_handler(kill_handler)

    random_handler = CommandHandler('random', listRandom, pass_args= True)
    dispatcher.add_handler(random_handler)

    #dbx_handler = CommandHandler('dbxinit', dbxInit)
    #dispatcher.add_handler(dbx_handler)

    conv_handler = ConversationHandler(
        entry_points= [CommandHandler('list', listDrinks)],

        states = {
            CHOOSE: [CommandHandler('Whiskey', whiskey),
                     CommandHandler('Tequila', tequila),
                     CommandHandler('Gin', gin),
                     CommandHandler('Brandy', brandy)],

            LOOP:   [CommandHandler('Return', listDrinks),
                     CommandHandler('Exit', exitList)]
        },

        fallbacks = [CommandHandler('Exit', exitList)]
    )

    dispatcher.add_handler(conv_handler)
    #

    updater.idle()
    print('Idle Signal Received')

if __name__ == '__main__':
    main()
