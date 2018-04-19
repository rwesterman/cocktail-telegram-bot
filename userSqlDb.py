from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError, InvalidRequestError
import logging

engine = create_engine('sqlite:///bottender_test.db')
Base = declarative_base()
# Bind the new Session to our engine
Session = sessionmaker(bind=engine)

association_table = Table('association', Base.metadata,
                Column('User_user_id', Integer, ForeignKey('users.user_id')),
                Column('Favorite_user_id', Integer, ForeignKey('favorites.favorites')))

class User(Base):
    __tablename__ = 'users'

    # id = Column(Integer, primary_key=True)
    user_id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    chat_id = Column(Integer)

    # favorites = relationship("Favorite", backref = "users")
    favorites = relationship("Favorite", secondary = association_table)
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

Base.metadata.create_all(engine)

def add_user(user_id, chat_id, first_name, last_name = ""):
    try:
        new_user = User(user_id = user_id, first_name = first_name, chat_id = chat_id, last_name = last_name)
        # create an instance of Session class
        session = Session()
        # Add our User object to our Session
        session.add(new_user)
        # Commit the changes to the database
        session.commit()
        return new_user, session
    except IntegrityError as e:
        print("Trying to add a non-unique row to database")

    # This causes DetachedInstanceError because User becomes unassociated with the session
    # finally:
    #     session.close()

def set_user_favorite(user, fav_drink, session):
    """Adds drink to favorites table if not already in, then adds it to User's favorites list"""
    in_table = check_drink_in_table(fav_drink)
    # If the drink isn't in the table, add it (it will be an empty list if not in table)
    if not in_table:
        logging.debug("Drink is not yet in table")
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

def get_user_favorites(user):
    return user.favorites

def check_drink_in_table(drink_name):
    """Checks to see if a drink is already in the favorites table, and returns it if so"""
    session = Session()
    favs =  session.query(Favorite).filter(Favorite.favorites == drink_name).first()
    session.close()
    return favs

def check_for_user_id(id):
    """Check if a user_id exists in the database already"""
    # create an instance of Session class
    session = Session()
    user =  session.query(User).filter(User.user_id == id).first()
    # session.close()
    return user, session

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG)

    # Todo: Track different sessions with different users
    # jack, session = add_user(user_id = 22, first_name = "jack", chat_id = 22)
    # jill, session2 = add_user(user_id = 23, first_name = "jill", chat_id = 23)
    # set_user_favorite(jack, "Old-Fashioned", session)
    # set_user_favorite(jill, "Old-Fashioned", session2)
    # set_user_favorite(jack, "Negroni", session)
    # set_user_favorite(jack, "Negroni", session)
    # print("Jack's favorites: {}".format(get_user_favorites(jack)))
    # print("Jack's user info: {}".format(check_for_user_id(22)))
