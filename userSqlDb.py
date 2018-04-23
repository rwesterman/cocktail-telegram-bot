from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError, InvalidRequestError
import logging

import re

engine = create_engine('sqlite:///user.db')
Base = declarative_base()
# Bind the new Session to our engine
Session = sessionmaker(bind=engine)

fav_assc_table = Table('fav_asso', Base.metadata,
                       Column('User_user_id', Integer, ForeignKey('users.user_id')),
                       Column('Favorite_drink', String, ForeignKey('favorites.favorites')))

inv_assc_table = Table('inv_assc', Base.metadata,
                       Column('User_user_id', Integer, ForeignKey('users.user_id')),
                       Column('Inventory_stock', String, ForeignKey('inv.stock')))

class User(Base):
    __tablename__ = 'users'

    # id = Column(Integer, primary_key=True)
    user_id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    chat_id = Column(Integer)

    # favorites = relationship("Favorite", backref = "users")
    favorites = relationship("Favorite", secondary = fav_assc_table)
    stock = relationship("Inventory", secondary = inv_assc_table)

    def __repr__(self):
        return "<User(user_id = {}, first_name = {}, last_name = {}, chat_id = {})>".format(
            self.user_id, self.first_name, self.last_name, self.chat_id)


class Favorite(Base):
    __tablename__ = 'favorites'
    # id = Column(Integer, nullable= False)
    favorites = Column(String, primary_key= True)
    # user_id = Column(Integer, ForeignKey('users.user_id'))
    popularity = Column(Integer)

    def __repr__(self):
        return "<Favorite(favorite={}, popularity = {})>".format(self.favorites, self.popularity)


# For now, I am not keeping track of the amount each person has in their inventory
# I might try to add this later, but it will require an overhaul
class Inventory(Base):
    __tablename__ = 'inv'

    stock = Column(String, primary_key= True)
    # Amount will list number of bottles available, (Defaults to 1 when added to user)
    # amount = Column(Integer)

    def __repr__(self):
        return "<Inventory(stock = {})>".format(self.stock)
Base.metadata.create_all(engine)

def add_user(user_id, chat_id, first_name, last_name = ""):

    new_user = User(user_id = user_id, first_name = first_name, chat_id = chat_id, last_name = last_name)
    # create an instance of Session class
    session = Session()
    # Add our User object to our Session
    session.add(new_user)
        # Commit the changes to the database
    try:
        session.commit()
        return new_user, session
    except IntegrityError as e:
        session.rollback()
        existing_user = session.query(User).filter(User.user_id == user_id).first()
        print("Trying to add a non-unique row to database, returning existing user")
        return existing_user, session

def ing_regex(ingredient):
    """
    Uses regex to separate quantity from ingredients
    :param ingredient: Ingredient object, to be stripped to ingredient name value
    :return: Returns three variables: quantity (float), measurement (String), ing (String)
    """
    ing_name = ingredient.ing
    # logging.info("Starting ingredient name: {}".format(ing_name))
    # Initialize holder variables
    quantity, dash_hold, tsp_hold, special_flag, oz_hold = "", "", "", "", ""

    # Num pattern looks for numbers and periods at start of string, plus a space after
    num_pattern = r"^[1-9.]+ "
    match_num = re.match(num_pattern, ing_name)

    # If ing_name has a number at start of string, proceed
    if match_num:
        # float value for quantity specified
        quantity = float(match_num.group().strip())
        # Remove this number substring from ing_name
        ing_name = re.sub(num_pattern, "", ing_name)

    # Move on to checking for corner case values (TSP, DASHES, etc.)
    # These can be done simultaneously because they are mutually exclusive
    dash_pattern = r"^DASH[E]*[S]* "
    tsp_pattern = r"^TSP[S]* "
    match_dash = re.match(dash_pattern, ing_name,flags = re.IGNORECASE)
    match_tsp = re.match(tsp_pattern, ing_name, flags = re.IGNORECASE)
    if match_dash:
        dash_hold = match_dash.group().strip()
        ing_name = re.sub(dash_pattern, "", ing_name)
    elif match_tsp:
        tsp_hold = match_tsp.group().strip()
        ing_name = re.sub(tsp_pattern, "", ing_name)
    # For special cases, there will be no measurement given (Egg, Mint, etc)
    elif re.match(r"(MINT )+(EGG )+(FUJI )+(RIPE )+", ing_name, flags = re.IGNORECASE):
        # special_flag acts to show that the measurement should stay blank
        special_flag = True
    else:
        oz_hold = 'oz.'

    #First value
    # If no number matched, set quantity to zero (arbitrary number), else return quantity
    if not quantity:
        quantity = 0

    #Second value
    # OR the _hold vars, if all are None, then special_flag is true, and measurement = ""
    measurement = dash_hold or tsp_hold or oz_hold
    if not measurement:
        # This is the special case with no measurement given
        measurement = ""

    # logging.debug("Ending ingredient name: {}".format(ing_name))
    logging.debug("Converted Ingredient: {} {} {}".format(quantity, measurement, ing_name))
    return quantity, measurement, ing_name


def copy_ing_to_inv(ingredients):
    """
    Strip ingredients to grab their name, then put it in Inventory.stock
    :param ingredients: all Ingredient objects from table ingredients
    :return:
    """
    # Go through list of Ingredient objects and extract Ingredient.ing
    session = Session()
    # session = Session()
    for ingredient in ingredients:
        try:
            new_inv = Inventory(stock = ingredient.ing)
            logging.debug("New Inventory Item: {}".format(new_inv))
            session.add(new_inv)
            session.commit()
        except IntegrityError as e:
            logging.error("Error in copy_ing_to_inv: {}".format(e))
    logging.debug("Copied all ingredients to Inventory table")

    session.close()

def set_user_favorite(user, fav_drink, session):
    """
    :param user: User object, should already exist in database
    :param fav_drink: String, to be taken from Drink object in drinksSqlDb
    :param session: Session object
    :return:
    """
    """Adds drink to favorites table if not already in, then adds it to User's favorites list"""
    in_table = check_drink_in_table(fav_drink)
    # If the drink isn't in the table, add it (it will be an empty list if not in table)
    if not in_table:
        logging.debug("Adding {} to favorites table".format(fav_drink))
        drink = Favorite(favorites = fav_drink, popularity = 0) #popularity = 0 because not in anyones favorites yet
    #If the drink is in the table, simply add it to user
    else:
        logging.debug("Drink is already in table")
        drink = in_table #set to same variable as in "if" statement

    try:
        # Add drink to user's favorites and commit changes
        user.favorites.append(drink)
        # Increase drink popularity by one
        drink.popularity = drink.popularity + 1
        # session = Session()
        session.commit()
    except InvalidRequestError as e:
        logging.error("This drink is already associated with the user")
    except IntegrityError as e:
        session.rollback()
        logging.error("Encountered IntegrityError in set_user_favorite(). Rolling session back")

def get_user_favorites(user):
    return user.favorites

def check_drink_in_table(drink_name):
    """Checks to see if a drink is already in the favorites table, and returns it if so"""
    session = Session()
    favs =  session.query(Favorite).filter(Favorite.favorites == drink_name).first()
    session.close()
    return favs

def check_for_user_id(id, session = ""):
    """Check if a user_id exists in the database already"""
    # If no session is provided, create an instance of Session class
    if not session:
        session = Session()
    user = session.query(User).filter(User.user_id == id).first()
    # session.close()
    return user, session

def check_ing_in_inv(ing_name):
    """Checks for ingredient name in inventory table"""
    session = Session()
    ing_exists = session.query(Inventory).filter(Inventory.stock.like(ing_name)).first()
    session.close()
    return ing_exists

def add_inventory(user, session, ing_name):
    # Todo: Incorporate checking against Ing_No_Quantity names to confirm that it's a real ingredient
    # Todo: Consolidate this method with set_user_favorite
    """
    Adds an ingredient to the 'inventory' table of user.db, then adds to the user's stock
    :param user: a User object
    :param session:
    :return:
    """
    in_table = check_ing_in_inv(ing_name)
    if not in_table:
        logging.debug("Adding {} to inventory table".format(ing_name))
        inv = Inventory(stock = ing_name) # Add the ingredient to the inventory table
    #If the ingredient is in the table, simply add it to user
    else:
        logging.debug("Ingredient is already in inventory table")
        inv = in_table #set to same variable as in "if" statement

    try:
        # Add drink to user's favorites and commit changes
        user.stock.append(inv)
        session.commit()
        logging.info("Added {} to inventory of user {}".format(ing_name, user.first_name))
    except InvalidRequestError as e:
        logging.error("The user already has {} in their inventory".format(ing_name))
    except IntegrityError as e:
        session.rollback()
        logging.error("Encountered IntegrityError in add_inventory(). Rolling session back")


def rem_inventory(user, session, ing):
    """

    :param user: a User object
    :param session: an instance of Session()
    :param ing: The ingredient that should be removed from the user's inventory
    :return:
    """
    inv_item = session.query(Inventory).filter(Inventory.stock.like(ing)).first()
    try:
        user.stock.remove(inv_item)
        session.commit()
        logging.info("Removed {} from inventory of user {}".format(ing, user.first_name))
    except ValueError as e:
        logging.warning("Trying to remove a value that doesn't exist")
    except IntegrityError as e:
        session.rollback()
        logging.warning("Failed to commit changes in rem_inventory(), rolling back session")



if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG)

    jack, session = add_user(user_id = 22, first_name = "jack", chat_id = 22)
    inv_to_add = ["Rittenhouse", "Buffalo Trace", "Bourbon", "Demerara", "Bitter Truth"]

    for ing in inv_to_add:
        add_inventory(jack, session, ing)


    # add_inventory(jack, session,"Rittenhouse")
    # add_inventory(jack, session, "Buffalo Trace")
    # add_inventory(jack, session, "Simple syrup")
    # add_inventory(jack, session, "Angostura")
    # add_inventory(jack, session,)
    # jill, session2 = add_user(user_id = 23, first_name = "jill", chat_id = 23)
    # set_user_favorite(jack, "Old-Fashioned", session)
    # set_user_favorite(jill, "Old-Fashioned", session2)
    # set_user_favorite(jack, "Negroni", session)
    # set_user_favorite(jack, "Negroni", session)
    # print("Jack's favorites: {}".format(get_user_favorites(jack)))
    # print("Jack's user info: {}".format(check_for_user_id(22)))
