from sqlalchemy import create_engine, Column, String, Integer, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError, InvalidRequestError
import logging


engine = create_engine('sqlite:///drinks.db')
Base = declarative_base()

association_table = Table('association', Base.metadata,
                Column('Drink_name', String, ForeignKey('drinks.drink_name')),
                Column('Ingredients_string', String, ForeignKey('ingredients.ing')))

class Drink(Base):
    __tablename__ = 'drinks'

    drink_name = Column(String, primary_key=True)
    page = Column(String)

    ingredients = relationship("Ingredient", secondary = association_table)

    def __repr__(self):
        return "<Drink(drink_name = {}, page = {})>".format(self.drink_name, self.page)

class Ingredient(Base):
    __tablename__ = 'ingredients'
    # Make ing the primary key, will hold all ingredients
    ing = Column(String, primary_key= True)
    popularity = Column(Integer)

    drinks = relationship("Drink", secondary = association_table)
    def __repr__(self):
        return "<Ingredient(ing = {}, popularity = {})>".format(self.ing, self.popularity)

class Garnish(Base):
    __tablename__ = 'garnishes'

    # holds garnishes for each drink. This may or may not work with relationships
    gar = Column(String, primary_key=True)

Session = sessionmaker(bind=engine, autoflush= False)
Base.metadata.create_all(engine)

def drink_name_contains(name, session):
    session = Session()
    return session.query(Drink).filter(Drink.drink_name.contains(name)).all(), session

def query_drink_all(name, session):

    session = Session()
    return session.query(Drink).filter(Drink.drink_name.like(name)).all(), session

def query_drink_first(name, session):
    session = Session()
    return session.query(Drink).filter(Drink.drink_name.like(name)).first(), session

def add_drink(name, page):
    """Try to add a new drink to the Drink database, return Drink object and session"""
    try:
        new_drink = Drink(drink_name = name, page = page)
        # create an instance of Session class
        session = Session()
        # Add our User object to our Session
        session.add(new_drink)
        # Commit the changes to the database
        # session.commit()
        return new_drink, session
    except IntegrityError as e:
        print("Trying to add a non-unique row to database")
        raise

# def sql_from_itertuples():
#     # Get dataframe object
#     df, sh = searchSS.sheets_init()
#     #Squash the object to just drink names and pages
#     for row in df.itertuples():
#         try:
#             print(row)
#             #Columns 0 and 1 are drink names and pages respectively
#             new_drink, session = add_drink(row[0], row[1])
#             # Range 2 to 12 in row are ingredients, add them while they exist
#             for col in range(2,12):
#                 # If ingredient isn't empty, add it to the drink
#                 if row[col]:
#                     # get Ingredient object, then append it to the Drink object just created.
#                     # continue this until all ingredients are added
#                     ingred = check_ing_in_table(row[col], session)
#                     new_drink.ingredients.append(ingred)
#             session.commit()
#             session.close()
#         except IntegrityError as e:
#             logging.error("Integrity error while transfering database. Likely due to duplicate. It will be skipped")

def query_ing_contains(ing_name, session):
    in_table =  session.query(Ingredient).filter(Ingredient.ing.contains(ing_name)).all()
    return in_table

def check_ing_in_table(ing_name, session):
    """Adds ingredient to table if not already there, then returns the object"""
    # session = Session()
    in_table =  session.query(Ingredient).filter(Ingredient.ing == ing_name).first()
    # session.close()
    if not in_table:
        logging.debug("Ingredient is not yet in table")
        ingred = Ingredient(ing = ing_name, popularity = 0) #popularity = 0 because not in anyones favorites yet
    #If the drink is in the table, simply add it to user
    else:
        logging.debug("Ingredient is already in table")
        ingred = in_table #set to same variable as in "if" statement
    ingred.popularity = ingred.popularity + 1
    return ingred

def get_ing_list(drink):
    """Takes a Drink object and returns a list of ingredients"""
    ings = []
    for ingredient in drink.ingredients:
        ings.append(ingredient.ing)
    return ings

def get_session():
    session = Session()
    return session

def close_session(session):
    session.commit()
    session.close()

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG)
    session = get_session()
    lemoning = query_ing_contains("benedictine", session)
    for lemon in lemoning:
        print(lemon.drinks)
    close_session(session)

    # drink_list = drink_name_contains("fashion")
    # logging.debug("drink_list object returned from drink_name_contains(): {}".format(drink_list))
    # for drink in drink_list:
    #     print(drink.drink_name)
    #     print(get_ing_list(drink))
