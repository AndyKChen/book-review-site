import os

from flask import Flask, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from helpers import *

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():
    return render_template("index.html")

# key: LAkytzNoQdcAmCjbO3Dhw
# secret: 2cSNox6prt16u8LWKGcozHUYeZovs1LW3Zt8rrhbcc

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    username = request.form.get("InputUsername")

    if request.method == "POST":

        if not request.form.get("InputUsername"):
            return render_template("error.html", message="Please provide a username.")

        elif not request.form.get("InputPassword"):
            return render_template("error.html", message="Please provide a password.")

        rows = db.execute("SELECT * from users WHERE username=:username", {"username": username})

        result = rows.fetchone()

        if result == None:
            return render_template("error.html", message="Invalid username and/or password.")

        session["user_id"] = result[0]
        session["username"] = result[1]

        return redirect("/")

    else:
        return render_template("login.html")


# @app.route("/search")
#def search():
