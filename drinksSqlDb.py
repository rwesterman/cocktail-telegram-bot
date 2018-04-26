import re, pygsheets, json, os, os.path

from sqlalchemy import create_engine, Column, String, Integer, Table, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError, InvalidRequestError
import logging


engine = create_engine('sqlite:///drinks.db')
Base = declarative_base()

ing_assc_table = Table('ing_assc', Base.metadata,
                       Column('Drink_name', String, ForeignKey('drinks.drink_name')),
                       Column('Ingredients_string', String, ForeignKey('ingredients.ing_id')))


gar_assc_table = Table('gar_assc', Base.metadata,
                       Column('Drink_name', String, ForeignKey('drinks.drink_name')),
                       Column('Garnish_string', String, ForeignKey('garnishes.gar')))

class Drink(Base):
    __tablename__ = 'drinks'

    drink_name = Column(String, primary_key=True)
    page = Column(String)

    ingredients = relationship("Ingredient", secondary = ing_assc_table)
    garnishes = relationship("Garnish", secondary = gar_assc_table)

    def __repr__(self):
        return "<Drink(drink_name = {}, page = {})>".format(self.drink_name, self.page)

class Ingredient(Base):
    __tablename__ = 'ingredients'
    # Make ing the primary key, will hold all ingredients
    ing_id = Column(Integer, primary_key=True)
    ing = Column(String)
    quantity = Column(Float)
    measurement = Column(String)
    popularity = Column(Integer)

    drinks = relationship("Drink", secondary = ing_assc_table)
    simple_ing = Column(String, ForeignKey('simple.ing'))
    simple = relationship("Simple_Drink", backref = 'ingredients', uselist = True)
    # This relationship allows for simplification of ingredient names. Used for Inventory purposes
    # simple_name = relationship("Simple_Drink", backref = Simple_Drink)

    def __repr__(self):
        return "<Ingredient(ing = {}, quantity = {}, measurement = {}, popularity = {})>".format(
            self.ing, self.quantity, self.measurement, self.popularity)

class Garnish(Base):
    __tablename__ = 'garnishes'
    # holds garnishes for each drink. This may or may not work with relationships
    gar = Column(String, primary_key=True)

    def __repr__(self):
        return "<Garnish(gar = {})>".format(self.gar)

class Simple_Drink(Base):
    __tablename__ = 'simple'

    ing = Column(String, primary_key= True)

    # Intended to count how many ingredients match to this simplification. Not currently implemented
    population = Column(Integer)

    def __repr__(self):
        return "<Simple_Drink(ing = {}, population = {})>".format(self.ing, self.population)

Session = sessionmaker(bind=engine, autoflush= False)
Base.metadata.create_all(engine)

def verify_ing_for_inv(ing_name, session):
    """
    Compares ing_name vs values in both ingredients table and simple table
    :param ing_name: a String that holds the ingredient name to be added
    :param session: a drinks.db Session() object
    :return: ingredient name if one exists, otherwise empty string
    """

    ingredients_check = session.query(Ingredient).filter(Ingredient.ing.like(ing_name)).first()
    simple_ing_check = session.query(Simple_Drink).filter(Simple_Drink.ing.like(ing_name)).first()
    if ingredients_check:
        # if ing_name matches an Ingredient in the table, return that Ingredient's name
        return ingredients_check.ing
    elif simple_ing_check:
        # if ing_name matches a Simple_Drink in the table, return that Simple_Drink's ingredient name
        return simple_ing_check.ing
    else:
        # If neither matches, return an empty string. This will be checked against in the calling function
        return ""


def simplify_ingredient(ingredient, session):
    """Takes an ingredient object and returns its simplified name if available, otherwise returns full ingredient name
    Always returns uppercase text."""
    if ingredient.simple_ing:
        return ingredient.simple_ing.upper()
    else:
        return ingredient.ing.upper()


def query_drink_contains(name, session= ""):
    if not session:
        session = Session()
    return session.query(Drink).filter(Drink.drink_name.contains(name)).all(), session

def query_drink_all(name, session = ""):
    if not session:
        session = Session()
    return session.query(Drink).filter(Drink.drink_name.like(name)).all(), session

def query_drink_first(name, session = ""):
    if not session:
        session = Session()
    return session.query(Drink).filter(Drink.drink_name.like(name)).first(), session

def add_ingredient(quantity, measurement, ingredient, session =""):
    if not session:
        session = Session()
    new_ing = Ingredient(quantity = quantity, measurement = measurement, ing = ingredient, popularity = 0)
    session.add(new_ing)
    logging.info("Adding new Ingredient {}".format(new_ing))
    try:
        session.commit()
        return new_ing, session
    except:
        session.rollback()
        logging.error("Trying to add duplicate values to Ingredient")
        return "", session


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


class DB_Builder():
    """This class is used to quickly rebuild my databases in case I lose them"""

    def __init__(self):
        with open(os.path.join(os.getcwd(),"json", "simplify.json"),'r') as f:
            self.simplify_dict = json.load(f)

    def sql_from_itertuples(self):
        # Get dataframe object
        df, sh = self.sheets_init()
        # Squash the object to just drink names and pages
        for row in df.itertuples():
            logging.debug(row)
            # Columns 0 and 1 are drink names and pages respectively
            new_drink, session = add_drink(row[0], row[1])
            # Range 2 to 12 in row are ingredients, add them while they exist
            for col in range(2, 12):
                # If ingredient isn't empty, add it to the drink
                if row[col]:
                    # get Ingredient object, then append it to the Drink object just created.
                    # continue this until all ingredients are added
                    quantity, measurement, ing_name = ing_regex(row[col])
                    ingred = check_ing_in_table(ing_name, session, quantity, measurement)
                    new_drink.ingredients.append(ingred)

            # Check the garnish row, and add to garnishes
            if row[12]:
                gar = check_garnish_in_table(row[12], session)
                new_drink.garnishes.append(gar)
            try:
                session.commit()
                session.close()
            except IntegrityError as e:
                session.rollback()
                logging.error("Attempting to add duplicate Ingredient, rolling back session")
                session.close()

    def get_df(self, has_header, index_comlumn, start, end, wks):
        """Returns dataframe with given specifications"""
        df = wks.get_as_df(has_header=has_header, index_colum=index_comlumn, start=start, end=end)
        return df

    def open_sheet(self, sheet_name, wks_name, gc):
        """Opens sheet 'sheet_name' and creates new sheet if not found. Returns sheet and worksheet"""
        try:
            sh = gc.open(sheet_name)
        except:
            gc.create(sheet_name)
            sh = gc.open(sheet_name)
        wks = sh.worksheet_by_title(wks_name)  # changed this over night
        return sh, wks

    def sheets_init(self):
        """Initializes google sheets, returns dataframe and sheet object"""
        client_secret = 'client_secret_11971016162-198la1sa3dvcin75tnq8nhsdrepeh8nl.apps.googleusercontent.com.json'
        sheet_name = 'Death & Co Cocktails'
        gc = pygsheets.authorize(client_secret)
        sh, wks = self.open_sheet(sheet_name, 'AllDrinks', gc)  # Open sheet with given name, or create if not found
        last_row = 'N' + str(wks.rows)
        df = self.get_df(True, 1, 'A1', last_row, wks)  # get dataframe from AllDrinks worksheet
        return df, sh

    def populate_simple_drink(self, session):

        # Iterate through simplify_dict to find each ingredient that contains the name of the dictionary key
        for category in self.simplify_dict:
            associate_ing = session.query(Ingredient).filter(Ingredient.ing.contains(category)).all()

            # associate_ing is list of Ingredient objects
            # iterate through associate_ing list to associate the ingredients with their simplified name
            for ing in associate_ing:
                # Add the value associated with current key in simplify_dict to simple
                simple, session = self.add_ing_to_simple(self.simplify_dict[category], session)
                if simple:
                    logging.debug("Trying to append this {}".format(simple))
                    ing.simple.append(simple)

    def add_ing_to_simple(self, ing_name, session = ""):
        """Check that ingredient isn't in simple table, and then add it"""
        if not session:
            session = Session()

        in_table = session.query(Simple_Drink).filter(Simple_Drink.ing == ing_name).first()
        if not in_table:
            new_simple = Simple_Drink(ing=ing_name, population=0)
            session.add(new_simple)
        else:
            new_simple = in_table
        try:
            session.commit()
            return new_simple, session
        except IntegrityError as e:
            session.rollback()
            logging.warning("Failed add simple ingredient {}".format(ing_name))
            return "", session


def ing_contains_all(ing_name, session):
    return session.query(Ingredient).filter(Ingredient.ing.contains(ing_name)).all()

def ing_contains_first(ing_name, session):
    return session.query(Ingredient).filter(Ingredient.ing.contains(ing_name)).first()

def check_ing_in_table(ing_name, session, quantity, measurement):
    """Creates new Ingredient object and adds it to table if not already there, then returns the object"""
    in_table = session.query(Ingredient).filter(Ingredient.ing == ing_name, Ingredient.quantity == quantity,
                                                Ingredient.measurement == measurement).first()
    if not in_table:
        logging.debug("Ingredient is not yet in table")
        ingred = Ingredient(ing = ing_name, quantity = quantity, measurement = measurement, popularity = 0) #popularity = 0 because not in anyones favorites yet

    #If the drink is in the table, simply add it to user
    else:
        logging.debug("Ingredient is already in table")
        ingred = in_table #set to same variable as in "if" statement

    ingred.popularity = ingred.popularity + 1
    return ingred

def simple_contains_all(ing_name, session):
    return session.query(Simple_Drink).filter(Simple_Drink.ing.contains(ing_name)).all()

def simple_contains_first(ing_name, session):
    return session.query(Simple_Drink).filter(Simple_Drink.ing.contains(ing_name)).first()

def check_garnish_in_table(garnish, session):
    in_table = session.query(Garnish).filter(Garnish.gar == garnish).first()

    if not in_table:
        logging.debug("Adding garnish {} to table".format(garnish))
        gar = Garnish(gar = garnish)
    else:
        logging.debug("Garnish already in table")
        gar = in_table
    return gar

def get_formatted_ingredients(drink):
    """Takes a Drink object and returns a list of ingredients"""
    ings = []
    for ingredient in drink.ingredients:
        # Check that there is a value for measurement so spacing is consistent
        if ingredient.measurement:
            ings.append("{} {} {}".format(ingredient.quantity, ingredient.measurement, ingredient.ing))
        else:
            ings.append("{} {}".format(ingredient.quantity, ingredient.ing))

    # Return list of strings to be output.
    return ings

def get_drink_session():
    session = Session()
    return session

def close_session(session):
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        logging.warning("Commit failed, rolling back changes")
    finally:
        session.close()

def ing_regex(ing_name):
    """
    Uses regex to separate quantity from ingredients
    :param ingredient: ingredient name from spreadsheet (eg. 2 DASHES ANGOSTURA BITTERS)
    :return: Returns three variables: quantity (float), measurement (String), ing (String)
    """
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

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG)


