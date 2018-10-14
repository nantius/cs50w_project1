import os
import requests
from flask import Flask, session, render_template, request, flash, redirect, url_for, abort, jsonify, Response
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


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

# ROTA RAIZ
@app.route("/")
def index():
    return render_template("index.html")

# ROTA DE REGISTRO
@app.route("/register", methods=["GET", "POST"])
def register():

    # REQUISIÇÃO GET
    if request.method == "GET":
        return render_template("register.html")

    # REQUISIÇÃO POST
    if request.method == "POST":

        # EXTRAÇÃO DOS DADOS DO FORMULÁRIO
        try:
            login_form = request.form.get("login")
            password_form = request.form.get("password")
        except ValueError:
            flash("Erro ao cadastrar")
            return render_template("register.html")

        # INSERÇÃO DOS DADOS DO USUÁRIO NO BANCO DE DADOS
        db.execute("INSERT INTO client (login, password) VALUES (:login, :password)", {"login": login_form, "password": password_form})
        db.commit()

        # USUARIO CADASTRADO
        flash("Registration successful!")

        return redirect(url_for("index"))

# ROTA DE LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():

    # REQUISIÇÃO GET
    if request.method == "GET":
        return render_template("login.html")

    # REQUISIÇÃO POST
    if request.method == "POST":

        # EXTRAÇÃO DOS DADOS DO FORMULÁRIO
        try:
            login = request.form.get("login")
            password = request.form.get("password")
        except ValueError:
            flash("Erro ao logar")
            return

        # VERIFICAÇÃO DO USUARIO NO BANCO DE DADOS
        user = db.execute("SELECT * from client where login = :login and password = :password", {"login": login, "password": password}).fetchone()

        # CASO NAO ENCONTRADO
        if not user:
            flash("Password or user incorrect!")
            return render_template("login.html")

        # LOGANDO USUARIO, AO COLOCAR SUAS INFORMAÇõES EM VARIÁVEIS DE SESSÃO
        flash("You are logged in!")
        session["user"] = user.login
        session["user_id"] = user.id

        return redirect(url_for("search"))

@app.route("/api/<string:isbn>")
def api(isbn):

    book = db.execute("select * from book where isbn = :isbn", {"isbn": isbn}).fetchone()

    if not book:
        return abort(404)

    book_json = dict(book.items())
    book_json = jsonify(book_json)
    book_json.status_code = 200
    return book_json

@app.route("/logout")
def logout():

    if session.get("user"):
        flash("Logged out!")
        session.clear()
    else:
        flash("No user logged in!")

    return redirect(url_for("index"))

@app.route("/search", methods=["GET", "POST"])
def search():

    # Verificação de login
    if not session.get("user"):
        flash("You must be logged in!")
        return redirect(url_for("index"))

    #REQUISIÇÃO GET
    if request.method == "GET":
        return render_template("search.html")

    #REQUISIÇÃO POST
    if request.method == "POST":
        try:
            search = request.form.get("search")
        except ValueError:
            flash("Erro ao logar")
            return

        # VERIFICAÇÃO DOS LIVROS NO BANCO DE DADOS
        books = db.execute("SELECT * from book where isbn ILIKE concat('%',:search,'%') or title ILIKE concat('%',:search,'%') or author ILIKE concat('%',:search,'%');", {"search": search}).fetchall()

        if not books:
            flash("No results")
            return redirect(url_for("search"))

        return render_template("search.html", books=books)

@app.route("/book/<int:id>", methods=["GET","POST"])
def book(id):

    if request.method == "GET":
        book = db.execute("SELECT * from book where id = :id", {"id":id}).fetchone()
        reviews = db.execute("SELECT * FROM review join client on review.id_client = client.id where id_book = :id", {"id":id}).fetchall()
        goodreads = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "QrezCDYkr3FQaOciDVlcTQ", "isbns": book.isbn})
        return render_template("book.html", book=book, reviews=reviews, goodreads=goodreads.json())

    if request.method == "POST":
        # EXTRAÇÃO DOS DADOS DO FORMULÁRIO
        try:
            comment = request.form.get("comment")
            rating = request.form.get("rating")
        except ValueError:
            flash("Erro")
            return

        # verificação de review do mesmo usuário em um livro
        same_user = db.execute("select * from review where id_book = :id_book and id_client = :id_client;", {"id_book": id, "id_client": session["user_id"]}).fetchall()

        if not same_user:
            db.execute("insert into review (comment, rating, id_book, id_client) VALUES (:comment, :rating, :id_book, :id_client)", {"comment": comment, "rating": rating, "id_book": id, "id_client": session["user_id"]})
            db.commit()

            flash("Review inserted")
            return redirect(url_for("book", id=id))

        flash("You already reviewed this book")
        return redirect(url_for("book", id=id))