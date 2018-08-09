from cs50 import SQL, eprint
from datetime import datetime, date, time, timedelta
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from string import capwords
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
import calendar

from helpers import add_ingredient, apology, login_required, cap_input, textify_ingredients, count_ingredients

# Configure application
app = Flask(__name__)

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
# app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///allergy.db")

# global variable of maximum number of ingredients specified in the database
MAX_INGREDIENTS = 20


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """shows the users diary for the day"""

    # for POST request methods
    if request.method == "POST":
        # check food and time inputs all present
        if not request.form.get("food_id") or not request.form.get("hour") \
                or not request.form.get("minute") or not request.form.get("am_pm"):
            return apology("food or time was not entered", 400)

        # put day into datetime date object
        date_input = datetime.now().date()
        eaten_date_string = datetime.strftime(date_input, "%Y-%m-%d")

        # put time food was eaten into datetime time object
        time = request.form.get("hour") + ":" + request.form.get("minute") + " " + request.form.get("am_pm")
        time_input = datetime.strptime(time, "%I:%M %p").time()
        eaten_datetime = datetime.strptime((eaten_date_string + " " + time), "%Y-%m-%d %I:%M %p")
        food = datetime.strftime(eaten_datetime, "%Y-%m-%d %H:%M:%S")


        # check for allergic reactions related to date time of eating
        rows = db.execute("SELECT reaction_event_id, allergy_id, time_reaction, start, end FROM reactions INNER JOIN all_allergies \
                            ON reactions.reaction=all_allergies.allergy_id \
                            WHERE reactions.date_reaction = :date AND reactions.user_id=:user_id",
                            date=date_input, user_id=session["user_id"])
        allergy_no = None

        if len(rows)>0:
            for row in rows:
                reaction_time = datetime.strptime((eaten_date_string + " " + row["time_reaction"]), "%Y-%m-%d %H:%M:%S")
                #re = datetime.strftime(reaction_time, "%Y-%m-%d %H:%M:%S")

                # put the start and end times into datetime object
                start_time = reaction_time - timedelta(minutes=rows[0]["start"])

                end_time = reaction_time - timedelta(minutes=rows[0]["end"])

                # check if food was eaten between these times and set allergy id
                if eaten_datetime >= start_time and eaten_datetime <= end_time:
                    allergy_no = row["reaction_event_id"]
                    # add food marker to reaction in reactions database
                    db.execute("UPDATE reactions SET food_marker = :food_marker WHERE reaction_event_id = :event_id",
                                food_marker = 1, event_id = row["reaction_event_id"])

        else:
            allergy_no = None

        # add to database
        success = db.execute("INSERT INTO histories (user_id, food_no, date_ingested, time_ingested, allergy_link) \
                                VALUES (:user_id, :food_no, :date_ingested, :time_ingested, :allergy_link)",
                                user_id=session["user_id"], food_no=request.form.get("food_id"), date_ingested=date_input,
                                time_ingested=time_input, allergy_link=allergy_no)

        # if favorite box checked add to the favorites database
        if request.form.get("favorite"):
            lines=db.execute("INSERT INTO favorites (user_id, food_no) VALUES (:user_id, :food_no)",
                                user_id=session["user_id"], food_no=int(request.form.get("food_id")))

    # for both POST and GET requests check if the date has been specified
    if request.args.get("date_info"):
    #if self.request.GET.get("date_info"):
        date_input = request.args.get("date_info")
        header_text = date_input

    else:
        date_input = datetime.now().date()
        header_text = "Today"

    #  pull up all the user inputs into the food diary that day and link to all_foods info
    rows = db.execute("SELECT food_no, time_ingested, hist_no, allergy_link, brand, name FROM (histories INNER JOIN all_foods ON all_foods.food_id == histories.food_no) \
                        WHERE date_ingested = :date AND user_id = :user_id ORDER BY time_ingested",
                        date = date_input, user_id=session["user_id"])


    # query reactions database for reactions that day
    reactions = db.execute("SELECT * FROM (reactions INNER JOIN all_allergies ON all_allergies.allergy_id == reactions.reaction) \
                            WHERE date_reaction = :date AND reactions.user_id = :user_id",
                            date=date_input, user_id=session["user_id"])

    # put food data into list for table display
    food_list = []

    for row in rows:

        hist = row["hist_no"]
        hour = row["time_ingested"][:2]


        if row["allergy_link"] != None:
            brand = "<font color='red'>" + row["brand"] + "</font>"
            food = "<font color='red'>"+ row["name"] + "</font>"
        else:
            brand = row["brand"]
            food = row["name"]

        food_list.append({"time": hour, "brand": brand, "title": food, "hist_no": hist})

    reaction_list = []

    # for all reactions put into a list
    for reaction in reactions:
        symptoms = reaction["title"]
        hour = reaction["time_reaction"][:2]
        event_id = reaction["reaction_event_id"]

        reaction_list.append({"time": hour, "reaction": symptoms, "event_id": event_id})

    # put times into table to display
    times = []
    # 24 hours in a day
    for x in range(24):
        if x == 0:
            hour = "12 AM"
        if x > 0 and x < 12:
            hour = str(x) + " AM"

        if x == 12:
            hour = str(x) + " PM"

        if x > 12:
            hour = str(x % 12) + " PM"

        number = "{0:0=2d}".format(x)

        times.append({"hour": hour, "number": number})

        footer_text = "Foods shown in red are those that are potentially linked to a logged allergic reaction"

    # render the homepage showing this info
    return render_template("index.html", text = header_text, foods = food_list, reactions = reaction_list, times = times, footer = footer_text)


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """search main database for food"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # check inputs properly entered
        # Ensure name of food was submitted
        if not request.form.get("name"):
            return apology("must provide name of food", 400)

        # search main database for input item.  different search if brand not input
        if not request.form.get("brand"):
            rows = db.execute("SELECT * FROM all_foods WHERE name LIKE :name",
                                name=("%" + request.form.get("name") + "%"))
        else:
            rows = db.execute("SELECT * FROM all_foods WHERE brand LIKE :brand AND name LIKE :name",
                            brand=("%" + request.form.get("brand") + "%"), name=("%" + request.form.get("name") + "%"))

        # helpers function puts all ingredients into formatted string
        rows = textify_ingredients(rows)

        # if found display options
        if len(rows) > 0:
            # mark if items are favorites
            for row in rows:
                # search for food id in favorietes database
                lines = db.execute("SELECT * FROM favorites WHERE food_no=:food_no AND user_id = :user_id",
                                    food_no=row["food_id"], user_id=session["user_id"])
                # if food id is in favorites database add positive marker, if not add negative
                if len(lines)>0:
                    row["fave"] = 1
                else:
                    row["fave"] = 0

            text = "Search Results"
            return render_template("search_results.html", options = rows, intro_text = text)

        # if not found send user to the input food page allowing them to input that info
        else:
            text = "your food was not found, please enter it into our database"
            return render_template("input_food.html", text=text)

    else:
        # render template for search page
        return render_template("search.html")


@app.route("/faves", methods=["GET"])
@login_required
def add_food():
    """ allows user to add foods from their selected favorites """
    # get all the users favorites
    lines = db.execute("SELECT * FROM (favorites INNER JOIN all_foods ON all_foods.food_id == favorites.food_no) \
                        WHERE user_id = :user_id", user_id=session["user_id"])

    # helpers function put ingredients into text for display
    lines = textify_ingredients(lines)

    # render template for search page
    return render_template("faves.html", favorites = lines)


@app.route("/delete_fave", methods=["POST"])
@login_required
def delete_favorite():
    """ allows user to delete a food from their favorites list """
    if not request.form.get("food_id"):
        return apology("no food submitted for deletion", 400)

    db.execute("DELETE FROM favorites WHERE user_id = :user_id AND food_no = :food_no",
                user_id=session["user_id"], food_no=request.form.get("food_id"))

    return redirect("/faves")


@app.route("/ingredients_text", methods=["GET"])
@login_required
def ingredients_text():
    """ puts the ingredients of a single food item into html text for display as ajax object when selecting from favorites"""
    info = {}

    # check request is made, if not return json empty
    q = request.args.get("q")

    if not q:
        return jsonify(info)

    # else search database for the food id
    row = db.execute("SELECT * from all_foods WHERE food_id = :food_id", food_id = int(q))

    # function to put ingredients into html text, into dict
    row = textify_ingredients(row)
    info["ingredient"] = row[0]["ingred1"]

    return jsonify(info)

# delete a food from the histories database
@app.route("/delete_food", methods=["POST"])
@login_required
def delete_food():
    """ deletes a selected food from the database """

    if not request.form.get("submit"):
        return apology("record not found", 400)

    else:
        number = request.form.get("submit")

        # check if this is the only food representing an allergy link in reactions and if so update
        # find the reaction marker on this food
        reaction_event = db.execute("SELECT allergy_link FROM histories WHERE hist_no = :hist_no", hist_no=number)

        if reaction_event:
        # check if this reaction marker is on any other foods
            reaction_number = reaction_event[0]["allergy_link"]
            other_reaction = db.execute("SELECT allergy_link FROM histories WHERE allergy_link = :allergy_link",
                                         allergy_link=reaction_number)

            # if not update food marker for event id  to false
            if len(other_reaction)<2:
                db.execute("UPDATE reactions SET food_marker=:food_marker WHERE reaction_event_id=:event_id",
                            food_marker="0", event_id=reaction_number)

        # delete the record of the food from histories
        db.execute("DELETE FROM histories WHERE hist_no = :hist", hist=request.form.get("submit"))

        return redirect("/")

# log an ellergic reaction
@app.route("/reaction", methods=["GET", "POST"])
@login_required
def reaction():
    """log a reaction and link it to the foods eaten with suitable timeframe"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        #check a reaction was input and a time was input
        if not request.form.get("reaction") or not request.form.get("day") or not request.form.get("hour") \
                or not request.form.get("minute") or not request.form.get("am_pm"):
            return apology("must provide reaction and time of occurance", 400)

        # put day into datetime date object
        if request.form.get("day") == "today":
            date_input = datetime.now().date()
        else:
            date_input = datetime.now().date() - timedelta(days=1)

        # put time into datetime time object
        time = request.form.get("hour") + ":" + request.form.get("minute") + " " + request.form.get("am_pm")
        time_input = datetime.strptime(time, "%I:%M %p").time()

        # log reaction and time in reaction database
        reaction_event = db.execute("INSERT INTO reactions (user_id, date_reaction, time_reaction, reaction, food_marker) \
                                     VALUES (:user_id, :date, :time, :reaction, :food_marker)",
                                     user_id=session["user_id"], date=date_input, time=time_input,
                                     reaction=request.form.get("reaction"), food_marker=0)

        # search allergy info from database
        rows = db.execute("SELECT * FROM all_allergies WHERE allergy_id = :allergy", allergy=request.form.get("reaction"))

        # times to search for
        start_time = (datetime.combine(date.min, time_input) - timedelta(minutes=rows[0]["start"]))
        end_time = datetime.combine(date.min, time_input) - timedelta(minutes=rows[0]["end"])

        # convert times to stings
        time_start = datetime.strftime(start_time, "%H:%M:%S")
        time_end = datetime.strftime(end_time, "%H:%M:%S")

        # query history database for foods eaten with the reaction timeframe
        lines = db.execute("SELECT hist_no FROM histories WHERE (time_ingested BETWEEN :time_start AND :time_end) \
                            AND date_ingested = :date AND user_id = :user_id",
                            time_start=time_start, time_end=time_end, date=date_input, user_id=session["user_id"])

        if len(lines)>0:
            # add food marker to reaction in reactions database
            db.execute("UPDATE reactions SET food_marker = :food_marker WHERE reaction_event_id = :event_id",
                        food_marker = 1, event_id = reaction_event)

            # for each food found set the allergy reactor to true
            for line in lines:
                update = db.execute("UPDATE histories SET allergy_link = :allergy WHERE hist_no = :hist_no",
                            allergy=reaction_event, hist_no=line["hist_no"])

        return redirect("/")


    else:
        reaction = db.execute("SELECT title, allergy_id FROM all_allergies WHERE user_id = :user_id OR user_id IS NULL",
                                user_id=session["user_id"])

        return render_template("reaction.html", reactions = reaction)

@app.route("/my_reaction", methods=["GET", "POST"])
@login_required
def my_reaction():
    """enter/edit a personalised allergic reaction and timeframe"""

    if request.method == "POST":

        #check a reaction and time frame was input
        if not request.form.get("title") or not request.form.get("start") or not request.form.get("end"):
            return apology("must provide reaction title", 400)

        # convert hours into minutes
        start_time = 60 * float(request.form.get("start"))
        end_time = 60 * float(request.form.get("end"))

        rows = db.execute("INSERT INTO all_allergies (title, start, end, user_id) VALUES (:title, :start, :end, :user_id)",
                            title = ("Custom Reaction: " + request.form.get("title")), start=start_time , end=end_time, user_id=session["user_id"])


        return redirect ("/reaction")

    else:

        return render_template("my_reaction.html")



# delete an ellergic reaction
@app.route("/delete_reaction", methods=["GET", "POST"])
@login_required
def delete_reaction():
    """delete a logged reaction and any links to the foods"""

    if not request.form.get("submit"):
        return apology("record not found", 400)

    else:
        number = request.form.get("submit")

        db.execute("DELETE FROM reactions WHERE reaction_event_id = :reaction_event", reaction_event=number)

        # check for this allergic marker in hisotires and if so delete marker
        rows = db.execute("UPDATE histories SET allergy_link = :allergy_link WHERE user_id = :user_id \
                           AND allergy_link = :reaction_event", allergy_link=None, user_id=session["user_id"], reaction_event=number)


    return redirect("/")


@app.route("/input_food", methods=["GET", "POST"])
@login_required
def input_food():
    """add food to main database"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # check inputs properly entered
        # Ensure brand was submitted
        if not request.form.get("brand"):
            return apology("must provide a brand. If there is no brand enter 'generic' or 'fresh'", 400)
        else:
            brand = cap_input(request.form.get("brand"))

        # Ensure password was submitted, ensure standard formatting
        if not request.form.get("name"):
            return apology("must provide name of food", 400)
        else:
            name = cap_input(request.form.get("name"))

        # take all ingredients inputs and standardise formatting.  for ingred 1 ensure there is an input or send error message
        if not request.form.get("ingred1"):
            return apology("enter at least one ingredient")
        else:
            ingred1 = cap_input(request.form.get("ingred1"))

        if not request.form.get("ingred2"):
            ingred2 = None
        else:
            ingred2 = cap_input(request.form.get("ingred2"))

        if not request.form.get("ingred3"):
            ingred3 = None
        else:
            ingred3 = cap_input(request.form.get("ingred3"))

        if not request.form.get("ingred4"):
            ingred4 = None
        else:
            ingred4 = cap_input(request.form.get("ingred4"))

        if not request.form.get("ingred5"):
            ingred5 = None
        else:
            ingred5 = cap_input(request.form.get("ingred5"))

        if not request.form.get("ingred6"):
            ingred6 = None
        else:
            ingred6 = cap_input(request.form.get("ingred6"))

        if not request.form.get("ingred7"):
            ingred7 = None
        else:
            ingred7 = cap_input(request.form.get("ingred7"))

        if not request.form.get("ingred8"):
            ingred8 = None
        else:
            ingred8 = cap_input(request.form.get("ingred8"))

        if not request.form.get("ingred9"):
            ingred9 = None
        else:
            ingred9 = cap_input(request.form.get("ingred9"))

        if not request.form.get("ingred10"):
            ingred10 = None
        else:
            ingred10 = cap_input(request.form.get("ingred10"))

        if not request.form.get("ingred11"):
            ingred11 = None
        else:
            ingred11 = request.form.get("ingred11")

        # take all ingredients inputs, implement standard formatting
        if not request.form.get("ingred12"):
            ingred12 = None
        else:
            ingred12 = cap_input(request.form.get("ingred12"))

        if not request.form.get("ingred13"):
            ingred13 = None
        else:
            ingred13 = cap_input(request.form.get("ingred13"))

        if not request.form.get("ingred14"):
            ingred14 = None
        else:
            ingred14 = cap_input(request.form.get("ingred14"))

        if not request.form.get("ingred15"):
            ingred15 = None
        else:
            ingred15 = cap_input(request.form.get("ingred15"))

        if not request.form.get("ingred16"):
            ingred16 = None
        else:
            ingred16 = cap_input(request.form.get("ingred16"))

        if not request.form.get("ingred17"):
            ingred17 = None
        else:
            ingred17 = cap_input(request.form.get("ingred17"))

        if not request.form.get("ingred18"):
            ingred18 = None
        else:
            ingred18 = cap_input(request.form.get("ingred18"))

        if not request.form.get("ingred19"):
            ingred19 = None
        else:
            ingred19 = cap_input(request.form.get("ingred19"))

        if not request.form.get("ingred20"):
            ingred20 = None
        else:
            ingred20 = cap_input(request.form.get("ingred20"))

        #check that this food is not in the directory already
        rows = db.execute("SELECT * FROM all_foods WHERE brand=:brand AND name=:name \
                            AND ingred1=:ingred1 AND ingred2=:ingred2 AND ingred3=:ingred3 AND \
                            ingred4=:ingred4 AND ingred5=:ingred5 AND ingred6=:ingred6 AND ingred7=:ingred7 AND \
                            ingred8=:ingred8 AND ingred9=:ingred9 AND ingred10=:ingred10 AND ingred11=:ingred11 AND \
                            ingred12=:ingred12 AND ingred13=:ingred13 AND ingred14=:ingred14 AND ingred15=:ingred15 AND \
                            ingred16=:ingred16 AND ingred17=:ingred17 AND ingred18=:ingred18 AND ingred19=:ingred19 AND \
                            ingred20=:ingred20", brand=brand, name=name,
                            ingred1=ingred1, ingred2=ingred2, ingred3=ingred3, ingred4=ingred4,
                            ingred5=ingred5, ingred6=ingred6, ingred7=ingred7, ingred8=ingred8,
                            ingred9=ingred9, ingred10=ingred10, ingred11=ingred11, ingred12=ingred12,
                            ingred13=ingred13, ingred14=ingred14, ingred15=ingred15, ingred16=ingred16,
                            ingred17=ingred17, ingred18=ingred18, ingred19=ingred19, ingred20=ingred20)

        # if there is not yet an entry for this food
        if len(rows) < 1:

            # enter info into database
            number = db.execute("INSERT INTO all_foods (brand, name, ingred1, ingred2, ingred3, ingred4, \
                                ingred5, ingred6, ingred7, ingred8, \
                                ingred9, ingred10, ingred11, ingred12, ingred13, ingred14, \
                                ingred15, ingred16, ingred17,ingred18, ingred19, ingred20) \
                                VALUES (:brand, :name, :ingred1, NULLIF(:ingred2,''), NULLIF(:ingred3,''), \
                                NULLIF(:ingred4,''), NULLIF(:ingred5,''), NULLIF(:ingred6,''), NULLIF(:ingred7,''), \
                                NULLIF(:ingred8,''), NULLIF(:ingred9,''), NULLIF(:ingred10,''), NULLIF(:ingred11,''), \
                                NULLIF(:ingred12,''), NULLIF(:ingred13,''), NULLIF(:ingred14,''), NULLIF(:ingred15,''), \
                                NULLIF(:ingred16,''), NULLIF(:ingred17,''), NULLIF(:ingred18,''), NULLIF(:ingred19,''), \
                                NULLIF(:ingred20,''))",
                                brand=brand, name=name,
                                ingred1=ingred1, ingred2=ingred2, ingred3=ingred3, ingred4=ingred4,
                                ingred5=ingred5, ingred6=ingred6, ingred7=ingred7, ingred8=ingred8,
                                ingred9=ingred9, ingred10=ingred10, ingred11=ingred11, ingred12=ingred12,
                                ingred13=ingred13, ingred14=ingred14, ingred15=ingred15, ingred16=ingred16,
                                ingred17=ingred17, ingred18=ingred18, ingred19=ingred19, ingred20=ingred20)

            # check if this food has been added into the database
            rows = db.execute("SELECT * FROM all_foods WHERE food_id = :food_id", food_id = number)

            # function to put ingredients into html text, into dict
            rows = textify_ingredients(rows)

            # set favorite marker to false
            rows[0]["fave"] = 0

            # statement for top of screen
            text = "Your food was added to the database"
        else:
            text = "Food found"

        # redirect to input ingredients
        return render_template("search_results.html", options = rows, intro_text = text)
    else:
        # render template for search page
        return render_template("input_food.html")



@app.route("/diary", methods=["GET"])
@login_required
def diary():
    """calendar"""

    return render_template("diary.html")


@app.route("/fill_diary", methods=["GET", "POST"])
@login_required
def fill_diary():
    """ extract information relating to relevant user / dates for input into diary """
    # get the url parameters for month and year
    if not request.args.get("month") and not request.args.get("year"):
        return apology("Can't do it!", 400)

    month = request.args.get("month")
    year = request.args.get("year")

    # format dates and search database for entries related
    text =  str(year) + "-" + str(month).zfill(2)

    # query history/all_foods database for user for that month & year
    rows = db.execute("SELECT * FROM (histories INNER JOIN all_foods ON all_foods.food_id == histories.food_no) \
                        WHERE user_id = :user_id AND date_ingested LIKE :date_ingested ORDER BY date_ingested, time_ingested",
                        user_id=session["user_id"], date_ingested=(text+"%"))

    # if reactions only return those
    reactions_only = db.execute("SELECT reactions.date_reaction, reactions.time_reaction, all_allergies.title FROM reactions \
                                 INNER JOIN all_allergies ON all_allergies.allergy_id == reactions.reaction \
                                 WHERE reactions.user_id = :user_id and date_reaction LIKE :date_reaction and \
                                 food_marker = :food_marker ORDER BY time_reaction DESC",
                                 user_id=session["user_id"], date_reaction=(text+"%"), food_marker=0)

    # if both lines and rows = 0 return nothing
    if not rows and not reactions_only:
        # return blank
        return ("", 204)

    else:
        events = [] # dict to store all diary entry info
        row_count = 0
        date = "place holder" #set date to earliest date there is info for
        body_text = ""
        reaction = False
        title = ""
        footer = '<form action="/" method="get">\
                  <button type="button" class="btn btn-default" data-dismiss="modal">Close</button> \
                  <button type="submit" class="btn btn-primary" name="date_info" onclick="dateId = $(this).closest(\'.modal\').attr(\'dateId\'); value=myDateFunction(dateId, true);">Go to full diary page</button> \
                  </form>'
        note_text = "<p><small>Foods shown in red may be related to an alergic reaction.</small></p>"

        # put the food search output into information per date
        for row in rows:
            # if this is the same as previous date, add the body information in
            if row["date_ingested"] == date:
                # add the food eaten to the current body info
                # if food linked to reaction
                if row["allergy_link"] != None:
                    # set badge to true
                    reaction = True
                    # highlight that food
                    body_text += ", <font color='red'>" + row["brand"] + " " + row["name"] + "</font>"
                else:
                    body_text += ", " + row["brand"] + " " + row["name"]

                row_count += 1

            # if this is a new date, put all the current info into the events list (if not first record) and restart all info
            else:
                if row_count != 0:
                    body_text += "<p><b>Reactions:</b><br>"
                    # if reaction list reactions
                    lines = db.execute("SELECT reactions.time_reaction, all_allergies.title FROM reactions \
                                        INNER JOIN all_allergies ON all_allergies.allergy_id == reactions.reaction \
                                        WHERE reactions.user_id = :user_id and date_reaction=:date_reaction ORDER BY time_reaction DESC",
                                        user_id=session["user_id"], date_reaction=date)

                    if len(lines) > 0:
                        for line in lines:
                            body_text +=line["time_reaction"][:5] + " - " + line["title"] + "<br>"
                    else:
                        body_text += "No reations recorded<br>"

                    # update dictionary
                    body_text += "</p>" + note_text
                    my_dict={"date": date, "badge": reaction, "body": body_text, "title": title, "footer": footer}
                    events.append(my_dict)

                # start new info
                title = "Records for " + row["date_ingested"]
                date = row["date_ingested"]
                row_count += 1

                # if food linked to reaction set badge to true and footer to "allergic reaction"
                body_text = "<p><b>Foods Eaten:</b><br>"
                if row["allergy_link"] != None:
                    reaction = True
                    # highlight that food
                    body_text += "<font color='red'>" + row["brand"] + " " + row["name"] + "</font>"
                else:
                    body_text += row["brand"] + " " + row["name"]
                    reaction = False

            # put last info in dict and list
            if row_count == len(rows):
                body_text += "<p><b>Reactions:</b><br>"
                # if reaction list reactions
                lines = db.execute("SELECT reactions.time_reaction, all_allergies.title FROM reactions \
                                        INNER JOIN all_allergies ON all_allergies.allergy_id == reactions.reaction \
                                        WHERE reactions.user_id = :user_id and date_reaction=:date_reaction ORDER BY time_reaction",
                                        user_id=session["user_id"], date_reaction=date)

                if len(lines) > 0:
                    for line in lines:
                        body_text +=line["time_reaction"][:5] + " - " + line["title"] + "<br>"
                else:
                    body_text += "No reations recorded"

                # put info into dict and append it to evets list
                body_text += "</p>" + note_text
                my_dict={"date": date, "badge": reaction, "body": body_text, "title": title, "footer": footer}
                events.append(my_dict)

        # check if there are dates with reactions but no food
        if reactions_only:
            line_count = 0
            date = "reset"
            reaction = True

            for reaction in reactions_only:
            # put the reactions into json object and return
                if reaction["date_reaction"] == date:
                    body_text += reaction["time_reaction"][:5] + " - " + reaction["title"] + "<br>"
                    line_count += 1
                else:
                    # add text to event if there is info
                    if line_count != 0:
                        my_dict={"date": date, "badge": reaction, "body": body_text, "title": title, "footer": footer}
                        events.append(my_dict)

                    # start new date info
                    title = "Records for " + row["date_ingested"]
                    body_text = '<p><b>Foods Eaten:</b><br>No foods recorded</p>'
                    body_text += '<p><b>Reactions:</b><br>' + reaction["time_reaction"][:5] + "  - " + reaction["title"] + '<br>'
                    date = reaction["date_reaction"]
                    line_count += 1

                if line_count == len(reactions_only):
                    body_text += "</p>" + note_text
                    my_dict={"date": date, "badge": reaction, "body": body_text, "title": title, "footer": footer}
                    events.append(my_dict)

        return jsonify(events);


# compare foods, mark for allergy
@app.route("/analyse", methods=["GET", "POST"])
@login_required
def analyse():
    """Analyse foods and identify those causing allergy symptoms"""

    # query history/all_foods database for user
    rows = db.execute("SELECT * FROM (histories INNER JOIN all_foods ON all_foods.food_id == histories.food_no) \
                        WHERE user_id = :user_id",
                        user_id=session["user_id"])

    # query known allergy database for known allergens
    knowns = db.execute("SELECT * FROM known_allergens WHERE user_id = :user_id", user_id=session["user_id"])

    ingredients = count_ingredients()

    # store all ingredients in analysis database
    for row in rows:
        # for each ingredient add to the analysis database
        for ingredient in ingredients:
            add_ingredient(row[ingredient], row["allergy_link"])

    # from this database delete all the know allergens
    for known in knowns:
        db.execute("DELETE FROM analysis WHERE ingredient LIKE :ingred", ingred = ("%" + known["ingredient"] + "%"))

    # get all entries where reaction triggered every time
    reds = db.execute("SELECT * FROM analysis WHERE user_id = :user_id AND times_eaten = times_reacted ORDER BY times_eaten DESC",
                        user_id=session["user_id"])

    # get all entries where reaction triggered majority of the time
    oranges = db.execute("SELECT * FROM analysis WHERE user_id = :user_id AND times_reacted != times_eaten \
                            AND (times_reacted > (times_eaten * 0.6)) \
                            ORDER BY times_eaten DESC, times_reacted DESC",
                            user_id=session["user_id"])

    # delete all of the users entries from the database to allow blank canvas for next analysis
    db.execute("DELETE FROM analysis WHERE user_id = :user_id", user_id=session["user_id"])

    # output the information to the analysis page
    return render_template("analysis.html", allergens = knowns, reds = reds, oranges = oranges)


# record allergy response, mark foods within timescale for allergy

# compare foods, mark for allergy
@app.route("/identify", methods=["GET", "POST"])
@login_required
def identify():
    """user specify food causing allergys"""

    if request.method == "POST":
        # if the remove submit button was used
        if request.form.get("submit") == "delete":
            remove = request.form.getlist("remove")

            for item in remove:
                db.execute("DELETE FROM known_allergens WHERE ingredient = :ingredient AND user_id = :user_id",
                            ingredient=item, user_id=session["user_id"])

        # if check submit button used
        elif request.form.get("submit") == "check":

            # take inputs
            allergens = request.form.getlist("allergen")

            # add them to known allergen database
            for allergen in allergens:
                if allergen != "":
                    rows = db.execute("INSERT INTO known_allergens (ingredient, user_id) VALUES (:ingredient, :user_id)",
                                        ingredient=allergen, user_id=session["user_id"])
        else:
            if not request.form.get("text_allergen"):
                return apology("need text input", 400)

            else:
                rows = db.execute("INSERT INTO known_allergens (ingredient, user_id) VALUES (:ingredient, :user_id)",
                                    ingredient=request.form.get("text_allergen"), user_id=session["user_id"])


        return redirect("/identify")



    else:
        # query known allergy database for known allergens
        knowns = db.execute("SELECT * FROM known_allergens WHERE user_id = :user_id", user_id=session["user_id"])

        # query history/all_foods database for user
        rows = db.execute("SELECT * FROM (histories INNER JOIN all_foods ON all_foods.food_id == histories.food_no) \
                            WHERE user_id = :user_id",
                            user_id=session["user_id"])

        ingredients = count_ingredients()

        # store all ingredients in analysis database
        for row in rows:
            # for each ingredient add to the analysis database
            for ingredient in ingredients:
                add_ingredient(row[ingredient], row["allergy_link"])

        # from this database delete all the know allergens
        for known in knowns:
            db.execute("DELETE FROM analysis WHERE ingredient LIKE :ingred", ingred = ("%" + known["ingredient"] + "%"))

        # get all entries where reaction triggered majority of the time
        reactions = db.execute("SELECT * FROM analysis WHERE user_id = :user_id \
                                AND (times_reacted > (times_eaten * 0.6)) \
                                ORDER BY times_eaten DESC, times_reacted DESC",
                                user_id=session["user_id"])

    # delete all of the users entries from the database to allow blank canvas for next analysis
    db.execute("DELETE FROM analysis WHERE user_id = :user_id", user_id=session["user_id"])

    # output the information to the analysis page
    return render_template("identify_allergen.html", known_allergens = knowns, rows = reactions)

@app.route("/faq", methods=["GET"])
@login_required
def faq():
    """displays the site information on how to use etc """
    # get all the FAQs and order them by number
    rows = db.execute("SELECT * FROM faq ORDER BY faq_no")

    # post them to the web page
    return render_template("faq.html", questions=rows)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure name and username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)


        if not request.form.get("name"):
            return apology("must provide you name", 400)

        if not request.form.get("surname"):
            return apology("must provide you surname", 400)

        # CHECK ENTERED INFO IS AN EMAIL

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure confirmation of password was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide confirmation of password", 400)

        # Ensure password and confirmation match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("password and confirmation do not match", 400)

        # hash password
        hashed_password = generate_password_hash(request.form.get("password"))

        # store username and hashed password in database.  if username taken return apology
        result = db.execute("INSERT INTO users (name, surname, username, hash)  VALUES (:name, :surname, :username, :hash)",
                            name=cap_input(request.form.get("name")), surname=cap_input(request.form.get("surname")),
                            username=request.form.get("username"), hash=hashed_password)

        if not result:
            return apology("username not available, please choose a different name", 400)

        # Remember which user has logged in
        session["user_id"] = result

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/username_check", methods=["GET"])
def username_check():
    """ checks the user name is unique """

    result = db.execute("SELECT * FROM users WHERE username = :user_tag", user_tag=request.args.get("name"))

    if len(result)>0 :
        info = {"taken": 'taken'}
    else:
        info = {"taken": 'not taken'}

    return jsonify(info)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/password", methods=["GET", "POST"])
@login_required
def password():
    """Allow user to change password."""

    if request.method == "POST":
        # check the three password inputs are filled and that the new password and confirmation match
        if not request.form.get("current_pass"):
            return apology("enter current password", 400)

        elif not request.form.get("password"):
            return apology("enter new password", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("new passwords do not match", 400)

        # request current hash from users database
        rows = db.execute("SELECT hash FROM users WHERE id = :user_id", user_id=session["user_id"])

        # compare the hash in the database with the entered password
        if not check_password_hash(rows[0]["hash"], request.form.get("current_pass")):
            return apology("invalid password", 400)

        # hash the new password
        hashed_password = generate_password_hash(request.form.get("password"))

        # compare the new password with the old password
        if check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("new password is the same as the old", 400)

        # store username and hashed password in database.  if username taken return apology
        result = db.execute("UPDATE users SET hash = :hashed WHERE id = :user_id",
                            hashed=hashed_password, user_id=session["user_id"])

        # send user to the hompage
        return render_template("pass_change.html")

    else:
        # render template for password input
        return render_template("password.html")

def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
