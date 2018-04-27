import logging

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

user_log = logging.getLogger("info." + __name__)
user_warn = logging.getLogger("warn." + __name__)

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
    favorites = Column(String, primary_key= True)
    popularity = Column(Integer)

    def __repr__(self):
        return "<Favorite(favorite={}, popularity = {})>".format(self.favorites, self.popularity)


# For now, I am not keeping track of the amount each person has in their inventory
# I might try to add this later, but it will require an overhaul
class Inventory(Base):
    __tablename__ = 'inv'

    stock = Column(String, primary_key= True)
    usr_inv = relationship("User", secondary = inv_assc_table)

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
        user_log.debug("Adding {} to favorites table".format(fav_drink))
        drink = Favorite(favorites = fav_drink, popularity = 0) #popularity = 0 because not in anyones favorites yet
    #If the drink is in the table, simply add it to user
    else:
        user_log.debug("Drink is already in table")
        drink = in_table #set to same variable as in "if" statement

    try:
        # Add drink to user's favorites and commit changes
        user.favorites.append(drink)
        # Increase drink popularity by one
        drink.popularity = drink.popularity + 1
        # session = Session()
        session.commit()
    except InvalidRequestError as e:
        user_warn.warning("This drink is already associated with the user")
    except IntegrityError as e:
        session.rollback()
        user_warn.warning("Encountered IntegrityError in set_user_favorite(). Rolling session back")

def rem_user_favorites(user, session, drink_name):
    rem_drink = session.query(Favorite).filter(Favorite.favorites.like(drink_name)).first()

    try:
        user.favorites.remove(rem_drink)
        session.commit()
        user_log.info("Removed {} from {}'s favorites".format(drink_name.title(), user.first_name))
    except ValueError as e:
        user_warn.error("Failed to remove user favorite {}, value does not exist".format(drink_name))
        raise
    except IntegrityError as e:
        session.rollback()
        user_warn.warning("Failed to commit changes in rem_inventory(), rolling back session")

def get_user_favorites(user):
    """
    Returns a list of Favorite objects associated with given User
    :param user: User object
    :return: List of Favorite objects
    """
    return user.favorites

def check_drink_in_table(drink_name):
    """Checks to see if a drink is already in the favorites table, and returns it if so"""
    session = Session()
    favs = session.query(Favorite).filter(Favorite.favorites.like(drink_name)).first()
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
    return ing_exists


def add_inventory(user, ing_name, session):
    # Todo: Consolidate this method with set_user_favorite
    """
    Adds item to inventory table, then adds inventory item to user's inventory
    :param session:
    :param user: a User object
    :return:
    """
    usr_sess = session
    in_table = check_ing_in_inv(ing_name)
    if not in_table:
        user_log.debug("Adding {} to inventory table".format(ing_name))
        inv = Inventory(stock = ing_name) # Add the ingredient to the inventory table
        usr_sess.add(inv)
        try:
            usr_sess.commit()
        except IntegrityError as e:
            user_log.debug("Session commit failed in add_inventory, rolling back")
            usr_sess.rollback()
    #If the ingredient is in the table, simply add it to user
    else:
        user_log.debug("Ingredient is already in inventory table")
        inv = in_table #set to same variable as in "if" statement

    try:
        # Add drink to user's favorites and commit changes

        # THIS IS VITAL. Inventory was on a different session for some reason,
        # this is here to merge it to my current session
        local_inv = usr_sess.merge(inv)

        user.stock.append(local_inv)
        usr_sess.commit()
        user_log.info("Added {} to inventory of user {}".format(ing_name, user.first_name))
    except InvalidRequestError as e:
        user_warn.error("InvalidRequestError {}".format(e))
        user_warn.error("The user already has {} in their inventory".format(ing_name))
    except IntegrityError as e:
        usr_sess.rollback()
        user_warn.warning("Encountered IntegrityError in add_inventory(). Rolling session back")


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
        user_log.info("Removed {} from inventory of user {}".format(ing, user.first_name))
    except ValueError as e:
        user_warn.warning("Trying to remove a value that doesn't exist")
        raise
    except IntegrityError as e:
        session.rollback()
        user_warn.warning("Failed to commit changes in rem_inventory(), rolling back session")

def get_user_inv(user):
    """
    Returns a list of Inventory objects associated with user
    :param user: User object
    :return: List of Inventory objects
    """
    return user.stock
