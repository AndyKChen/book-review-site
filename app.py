import os
import requests

from flask import Flask, session, flash, redirect, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from passlib.hash import sha256_crypt
from datetime import datetime


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

    # find all reviews
    rows = db.execute("SELECT review, name, date, rating, isbn  FROM reviews WHERE username=:username ORDER BY date", {"username":session["username"]})

    reviews = rows.fetchall()

    if reviews == []:
        return render_template("index.html", username=session["username"], message="No reviews written. Write one today!")

    return render_template("index.html", username=session["username"], reviews=reviews)



@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    username = request.form.get("email")
    password = request.form.get("InputPassword")

    if request.method == "POST":

        rows = db.execute("SELECT * from users WHERE username=:username OR email=:username",
            {"username": username, "email":username})

        result = rows.fetchone()

        if result == None:
            return render_template("login.html", alert="User does not exist.")

        elif not sha256_crypt.verify(password, result[3]):
            return render_template("login.html", alert="Incorrect password.")

        session["user_id"] = result[0]
        session["username"] = result[2]

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

        return redirect("/login")

    # if user arrives at route via "GET"/by clicking link or redirect
    else:
        return render_template("register.html")

@app.route("/logout")
@login_required
def logout():

    session.clear()

    return render_template("login.html")

@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():

    if request.method == "POST":

        q = request.form.get("query")

        query = "%" + request.form.get("query") + "%"

        query = query.title()

        if not request.form.get("from-date"):
            start = 0
        else:
            start = request.form.get("from-date")

        if not request.form.get("to-date"):
            stop = 100000
        else:
            stop = request.form.get("to-date")


        if request.form.get("sort") == "author":
            rows = db.execute ("SELECT books.isbn, books.title, books.author, books.year, reviews.rating FROM books \
            LEFT JOIN reviews \
            ON books.isbn = reviews.isbn \
            WHERE \
            (books.isbn LIKE :query OR \
            title LIKE :query OR \
            author LIKE :query) AND \
            year >= :start AND \
            year <= :stop \
            ORDER BY author",
            {"query":query, "start":start, "stop":stop})

        elif request.form.get("sort") == "rating":
            rows = db.execute ("SELECT books.isbn, books.title, books.author, books.year, reviews.rating FROM books \
            INNER JOIN reviews \
            ON books.isbn = reviews.isbn \
            WHERE \
            (books.isbn LIKE :query OR \
            title LIKE :query OR \
            author LIKE :query) AND \
            year >= :start AND \
            year <= :stop \
            ORDER BY rating DESC",
            {"query":query, "start":start, "stop":stop})

        elif request.form.get("sort") == "title":
            rows = db.execute ("SELECT books.isbn, books.title, books.author, books.year, reviews.rating FROM books \
            LEFT JOIN reviews \
            ON books.isbn = reviews.isbn \
            WHERE \
            (books.isbn LIKE :query OR \
            title LIKE :query OR \
            author LIKE :query) AND \
            year >= :start AND \
            year <= :stop \
            ORDER BY title",
            {"query":query, "start":start, "stop":stop})

        elif request.form.get("sort") == "year":
            rows = db.execute ("SELECT books.isbn, books.title, books.author, books.year, reviews.rating FROM books \
            LEFT JOIN reviews \
            ON books.isbn = reviews.isbn \
            WHERE \
            (books.isbn LIKE :query OR \
            title LIKE :query OR \
            author LIKE :query) AND \
            year >= :start AND \
            year <= :stop \
            ORDER BY year",
            {"query":query, "start":start, "stop":stop})

        else:
            rows = db.execute ("SELECT books.isbn, books.title, books.author, books.year, reviews.rating FROM books \
            LEFT JOIN reviews \
            ON books.isbn = reviews.isbn \
            WHERE \
            (books.isbn LIKE :query OR \
            title LIKE :query OR \
            author LIKE :query) AND \
            year >= :start AND \
            year <= :stop",
            {"query":query, "start":start, "stop":stop})

        if rows.rowcount == 0:
            return render_template("search.html", query=q, f=request.form.get("from-date"), t=request.form.get("to-date"), prompt="No results matching", message="(0)", username=session["username"])

        books = rows.fetchall()
        count = "(" + (str)(len(books)) + ")"

        return render_template("search.html", books=books, count=count, query=q, f=request.form.get("from-date"), t=request.form.get("to-date"), prompt="Showing all results matching", username=session["username"])

    else:
        return render_template("search.html", username=session["username"])


@app.route("/book/<isbn>", methods=['GET', 'POST'])
def book(isbn):

    if request.method == "POST":

        review = request.form.get("review")
        name = request.form.get("name")
        username = session["username"]
        if request.form.get("rating") == None:
            rating = 0
        else:
            rating = (int)(request.form.get("rating"))

        row = db.execute("SELECT * FROM reviews WHERE username=:username AND isbn=:isbn", {"username":username, "isbn":isbn})

        # check if user already submitted a review
        if row.fetchone():
            flash("You have already reviewed this book!")
            return redirect("/book/" + isbn)

        # insert review into database
        db.execute("INSERT INTO reviews (isbn, review, rating, username, name, date) VALUES (:isbn, :review, :rating, :username, :name, :date)",
            {"isbn":isbn, "review":review, "rating":rating, "username":username, "name":name, "date":datetime.date(datetime.now())})

        db.commit()

        return redirect("/book/" + isbn)

    else:
        # find all reviews
        rows = db.execute("SELECT review, name, date, rating FROM reviews WHERE isbn=:isbn", {"isbn":isbn})
        reviews = rows.fetchall()

        # find book info from database given an isbn
        row = db.execute("SELECT isbn, title, author, year FROM books WHERE isbn=:isbn", {"isbn":isbn})

        book_info = row.fetchall()

        """ Access Goodreads API and get review data"""
        # key: LAkytzNoQdcAmCjbO3Dhw
        # secret: 2cSNox6prt16u8LWKGcozHUYeZovs1LW3Zt8rrhbcc
        key = "LAkytzNoQdcAmCjbO3Dhw"
        query = requests.get("https://www.goodreads.com/book/review_counts.json", params={'key':key, 'isbns':isbn})

        # convert to json
        response = query.json()

        # clean response to 1-D array
        response = response['books'][0]

        # append array to book_info in position [1]
        book_info.append(response)

        return render_template("book.html", book_info=book_info, reviews=reviews, username=session["username"])


