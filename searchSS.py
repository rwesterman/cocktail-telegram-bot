import logging
import pygsheets


'''
/ing has a bug that returns all drinks
'''


def drink_search(df, drink_list):
    """Searches through spreadsheet for up to 4 drink names; Returns ingredients in list format"""
    response = []  # this will hold return list
    df_drink = df.copy()  # Copy the passed dataframe
    df_drink = df_drink.reset_index()  # Reset dataframe index so 'Drink Name' search is valid


    #decompress drink list

    if len(drink_list) >3:
        drink4 = drink_list[3]
        drink3 = drink_list[2]
        drink2 = drink_list[1]
        drink1 = drink_list[0]
    elif len(drink_list) == 3:
        drink4 = 'N/A'
        drink3 = drink_list[2]
        drink2 = drink_list[1]
        drink1 = drink_list[0]
    elif len(drink_list) == 2:
        drink4 = 'N/A'
        drink3 = 'N/A'
        drink2 = drink_list[1]
        drink1 = drink_list[0]
    else:
        drink4 = 'N/A'
        drink3 = 'N/A'
        drink2 = 'N/A'
        try:
            drink1 = drink_list[0]
        except IndexError:
            drink1 = ''

    if drink1 == '':
        return []


    # Searches for up to 4 names, optional drinks default to 'N/A' so they won't be found
    df_drink = df_drink[df_drink['Drink Name'].str.contains(drink1, case=False) |
                        df_drink['Drink Name'].str.contains(drink2, case=False) |
                        df_drink['Drink Name'].str.contains(drink3, case=False) |
                        df_drink['Drink Name'].str.contains(drink4, case=False)]

    # Add remaining df rows to response list
    for row in df_drink.iterrows():
        index, data = row
        response.append(data.tolist())
        logging.debug(response)

    # Delete any empty strings from lists
    for i, drinks in enumerate(response):
        response[i] = list(filter(None, response[i]))       #What does this do? Filters empty values from list?

    logging.debug(response)

    # return list of recipes
    return response


def get_df(has_header, index_comlumn, start, end, wks):
    """Returns dataframe with given specifications"""
    df = wks.get_as_df(has_header= has_header, index_colum= index_comlumn, start= start, end= end)
    return df


def ing_search(df, ing_name):
    """Returns all drinks that contain given ing_name"""
    ing_cols = ['Ingredients','ing2','ing3', 'ing4', 'ing5', 'ing6', 'ing7', 'ing8', 'ing9', 'ing10']
    dft = df.copy()
    dft = dft[dft[ing_cols[0]].str.contains(ing_name, case=False) |
              dft[ing_cols[1]].str.contains(ing_name, case=False) |
              dft[ing_cols[2]].str.contains(ing_name, case=False) |
              dft[ing_cols[3]].str.contains(ing_name, case=False) |
              dft[ing_cols[4]].str.contains(ing_name, case=False) |
              dft[ing_cols[5]].str.contains(ing_name, case=False) |
              dft[ing_cols[6]].str.contains(ing_name, case=False) |
              dft[ing_cols[7]].str.contains(ing_name, case=False) |
              dft[ing_cols[8]].str.contains(ing_name, case=False) |
              dft[ing_cols[9]].str.contains(ing_name, case=False)]


    dft  = dft.reset_index()
    logging.info(dft['Drink Name'].values)
    return list(dft['Drink Name'].values)

def get_random(df, num):
    response = []
    df2 = df.reset_index()  # Reset dataframe index so 'Drink Name' search is valid
    df2 = df2.sample(num)

    for row in df2.iterrows():          #Put the remaining dataframe rows into a list
        index, data = row
        response.append(data.tolist())
        logging.debug(response)

    for i, drinks in enumerate(response):
        response[i] = list(filter(None, response[i]))

    return response

def openSheet(sheet_name, wks_name, gc):
    """Opens sheet 'sheet_name' and creates new sheet if not found. Returns sheet and worksheet"""
    try:
        sh = gc.open(sheet_name)
    except:
        gc.create(sheet_name)
        sh = gc.open(sheet_name)
    wks = sh.worksheet_by_title(wks_name) #changed this over night
    return sh, wks


#Look into updting dataframe more frequently
def sheetsInit():
    """Initializes google sheets, returns dataframe and sheet object"""
    client_secret = 'client_secret_11971016162-198la1sa3dvcin75tnq8nhsdrepeh8nl.apps.googleusercontent.com.json'
    sheet_name = 'Death & Co Cocktails'
    gc = pygsheets.authorize(client_secret)
    sh, wks = openSheet(sheet_name, 'AllDrinks', gc)  #Open sheet with given name, or create if not found
    last_row = 'N' + str(wks.rows)
    df = get_df(True, 1, 'A1', last_row, wks) #get dataframe from AllDrinks worksheet
    return df, sh


def recipe_string(recipe, offset):
    botString = '{} on page {} has {} ingredients:'.format(recipe[offset + 0], recipe[offset + 1], recipe[offset -1])

    #Include redundancies for missing last element (number of ingredients element)
    #This will show up as a string if it is blank. Test for this exception.

    #logging.info('string is ' + botString)
    #logging.info('recipe[-1] ' + str(recipe[-1]))
    #logging.info('recipe[-2] ' + str(recipe[-2]))
    #logging.info('recipe[0] ' + str(recipe[0]))
    for i in range(recipe[- 1]):
        botString += '\n' + recipe[i+2].title()
    return botString

def base_liquor(wks_name, sheet):
    wks = sheet.worksheet_by_title(wks_name) #opens worksheet of given name, ie Whiskey
    #Todo: get values of column A. remove first entry as header, remove all null values, return list.
    drink_names = wks.get_col(1, include_empty= False)
    drink_names = drink_names[1:]
    return drink_names

