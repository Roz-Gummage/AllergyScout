from cs50 import SQL
import csv
import urllib.request

from flask import redirect, render_template, request, session
from functools import wraps

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///allergy.db")

# global variable of maximum number of ingredients specified in the database
MAX_INGREDIENTS = 20


def apology(message, code=400):
    """Renders message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def cap_input(string):
    """capitalises first letter of each word in string and removes extra whitespace """
    return " ".join([x.capitalize() for x in string.split()])


def add_ingredient(ingredient, react):
    """ adds ingredients to a master table for allergy analysis """

    if ingredient != None and ingredient != '':
        # query analysis database for ingredient
        rows = db.execute("SELECT times_eaten, times_reacted FROM analysis WHERE ingredient = :ingredients AND user_id = :user_id",
                        ingredients=ingredient, user_id=session["user_id"])

        # if the table has the ingredient already
        if len(rows) > 0:

            x = rows[0]["times_eaten"] + 1

            # check if this incident of food reaction = true, if so, update this number
            if react != None:
                y = rows[0]["times_reacted"] + 1
            else:
                y = rows[0]["times_reacted"]

            # update the info in the database with new numbers
            db.execute("UPDATE analysis SET times_eaten = :eaten, times_reacted = :reacted WHERE ingredient = :ingredients AND \
                    user_id = :user_id",
                    eaten=x, reacted=y, ingredients=ingredient, user_id=session["user_id"])

        else:
            if react != None:
                y = 1
            else:
                y = 0

            db.execute("INSERT INTO analysis (user_id, ingredient, times_reacted) VALUES (:user_id, :ingredients, :reacted)",
                    user_id=session["user_id"], ingredients=ingredient, reacted=y)

def count_ingredients():
    # compile list of ingredient titles as named in database
    count = 1
    ingredients = []
    for x in range(MAX_INGREDIENTS):
        ingredient = "ingred" + str(count)
        count += 1
        ingredients.append(ingredient)
    return ingredients


def textify_ingredients(rows):
    # format info on ingredients for display on web page
    ingredients = count_ingredients()

    # search known allegens database for all currently identified allergens
    allergens = db.execute("SELECT * FROM known_allergens WHERE user_id = :user_id", user_id=session["user_id"])

    # check all ingredients and compile into text
    for row in rows:
        info = ""
        reaction = False
        for ingred in ingredients:
            if ingred == "ingred1":
                # if ingredient is in list of identified allergens add code for bold red text
                for allergen in allergens:
                    reaction = False
                    if row[ingred] == allergen["ingredient"]:
                        reaction = True
                        break
                if reaction == True:
                    info += ("<b style ='color:red'>" + row[ingred] + "</b>")
                else:
                    info += (row[ingred])

            elif row[ingred]:
                # if ingredient is in list of identified allergens add code for bold red text
                for allergen in allergens:
                    reaction = False
                    if row[ingred] == allergen["ingredient"]:
                        reaction = True
                        break
                if reaction == True:
                    info += (", <b style ='color:red'>" + row[ingred] + "</b>")
                else:
                    info += (", " + row[ingred])
        row["ingred1"] = info

    return rows