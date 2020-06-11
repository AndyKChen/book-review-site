import os
import requests

from flask import Flask, session, flash, redirect, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from passlib.hash import sha256_crypt


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

    username = request.form.get("email")

    if request.method == "POST":

        if not request.form.get("email"):
            return render_template("error.html", message="Please provide login username or email.")

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


@app.route("/register", methods=["GET","POST"])
def register():

    session.clear()

    username = request.form.get("username")
    password = request.form.get("password")
    cpassword = request.form.get("passwordcheck")
    email = request.form.get("email")

    # check that route is reached via "POST"/ user submitted form
    if request.method == "POST":

        # check for existing user #
        checkEmail = db.execute("SELECT * from users WHERE email=:email",
            {"email":email}).fetchone()

        checkUser = db.execute("SELECT * from users WHERE username=:username",
            {"username":username}).fetchone()

        if checkEmail:
            if checkUser:
                return render_template("register.html", message1="This username already exists.", message3="This email already exists.")

            else:
                return render_template("register.html", message3="This email already exists")

        elif checkUser:
            return render_template("register.html", message1="This username already exists.")

        ###

        ## ensure password is at least 6 characters
        elif len((str)(password)) < 5:
            return render_template("register.html", message2="Please choose a password greater than 6 characters.")

        ## ensure user confirms password correctly
        elif password != cpassword:
            return render_template("register.html", message2="Passwords don't match!")

        # hash password
        pw = sha256_crypt.hash((str)(password))

        # query to insert new user
        db.execute ("INSERT INTO users (username, password, email) VALUES (:username, :password, :email)",
            {"username": username, "password": pw, "email": email})

        # commit changes to database
        db.commit()

        flash("Account Created!")

        return redirect("/login")

    # if user arrives at route via "GET"/by clicking link or redirect
    else:
        return render_template("register.html")

@app.route("/logout")
@login_required
def logout():

    session.clear()

    return render_template("login.html")
