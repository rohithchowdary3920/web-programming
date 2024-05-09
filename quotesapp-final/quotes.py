from flask import Flask, render_template, request, redirect, make_response
from mongita import MongitaClientDisk
from bson import ObjectId
from passwords import hash_password, check_password
import datetime 
app = Flask(__name__)

# open a mongita client connection
client = MongitaClientDisk()

# open a quote database
quotes_db = client.quotes_db
session_db = client.session_db
user_db = client.user_db
comment_db=client.comment_db

import uuid

@app.route("/", methods=["GET"])
@app.route("/quotes", methods=["GET"])
def get_quotes():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        return redirect("/login")
    session_collection = session_db.session_collection
    session_data = list(session_collection.find({"session_id": session_id}))
    if len(session_data) == 0:
        return redirect("/logout")
    assert len(session_data) == 1
    session_data = session_data[0]
    user = session_data.get("user", "unknown user")
    quotes_collection = quotes_db.quotes_collection
    data = list(quotes_collection.find({"owner": user}))
    publicData = list(quotes_collection.find({"public": True}))
    data = data + publicData
    filtered_list = list({obj["_id"]: obj for obj in data}.values())

    # Fetch comments for each quote
    comment_collection = comment_db.comment_collection
    for quote in filtered_list:
        quote_id = quote['_id']
        comments = list(comment_collection.find({"quote_id": str(quote_id)}))
        quote['comments'] = comments

    html = render_template("quotes.html", data=filtered_list, user=user)
    response = make_response(html)
    response.set_cookie("session_id", session_id)
    return response

@app.route("/comments/add", methods=["POST"])
def post_comment():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        return redirect("/login")
    
    _id = request.form.get("_id", None)
    newcomment = request.form.get("newcomment", "")
    if newcomment == "":
        return redirect("/quotes")

    session_collection = session_db.session_collection
    session_data = list(session_collection.find({"session_id": session_id}))
    if len(session_data) == 0:
        return redirect("/logout")
    
    session_data = session_data[0]
    user = session_data.get("user", "")

    quotes_collection = quotes_db.quotes_collection
    quote_data = quotes_collection.find_one({"_id": ObjectId(_id)})
    if not quote_data:
        return redirect("/quotes")

    comment_collection = comment_db.comment_collection
    comment_data = {
        "quote_id": _id,
        "date": datetime.datetime.now(),
        "text": newcomment,
        "owner": user
    }
    comment_collection.insert_one(comment_data)

    return redirect("/quotes")

@app.route("/comments/delete", methods=["POST"])
def post_delete_comment():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        return redirect("/login")

    _id = request.form.get("_id", None)
    if not _id:
        return redirect("/quotes")

    session_collection = session_db.session_collection
    session_data = list(session_collection.find({"session_id": session_id}))
    if len(session_data) == 0:
        return redirect("/logout")
    
    session_data = session_data[0]
    user = session_data.get("user", "")

    comment_collection = comment_db.comment_collection
    comment_data = comment_collection.find_one({"_id": ObjectId(_id)})
    if not comment_data:
        return redirect("/quotes")

    if user == comment_data.get("owner"):
        comment_collection.delete_one({"_id": ObjectId(_id)})
    
    return redirect("/quotes")

@app.route("/login", methods=["GET"])
def get_login():
    session_id = request.cookies.get("session_id", None)
    if session_id:
        return redirect("/quotes")
    return render_template("login.html")
    

@app.route("/login", methods=["POST"])
def post_login():
    user = request.form.get("user", "")
    password = request.form.get("password", "")
    user_collection = user_db.user_collection
    user_data = list(user_collection.find({"user": user}))
    if len(user_data) != 1:
        response = redirect("/login")
        response.delete_cookie("session_id")
        return response
    hashed_password = user_data[0].get("hashed_password", "")
    salt = user_data[0].get("salt", "")
    if check_password(password, hashed_password, salt) == False:
        response = redirect("/login")
        response.delete_cookie("session_id")
        return response
    session_id = str(uuid.uuid4())
    session_collection = session_db.session_collection
    session_collection.delete_one({"session_id": session_id})
    session_data = {"session_id": session_id, "user": user}
    session_collection.insert_one(session_data)
    response = redirect("/quotes")
    response.set_cookie("session_id", session_id)
    return response


@app.route("/register", methods=["GET"])
def get_register():
    session_id = request.cookies.get("session_id", None)
    print("Pre-login session id = ", session_id)
    if session_id:
        return redirect("/quotes")
    return render_template("register.html")
    

@app.route("/register", methods=["POST"])
def post_register():
    user = request.form.get("user", "")
    password = request.form.get("password", "")
    password2 = request.form.get("password2", "")
    if password != password2:
        response = redirect("/register")
        response.delete_cookie("session_id")
        return response
    user_collection = user_db.user_collection
    user_data = list(user_collection.find({"user": user}))
    if len(user_data) == 0:
        hashed_password, salt = hash_password(password)
        user_collection.insert_one({"user": user, "hashed_password": hashed_password, "salt": salt})
    response = redirect("/login")
    response.delete_cookie("session_id")
    return response


@app.route("/logout", methods=["GET"])
def get_logout():
    session_id = request.cookies.get("session_id", None)
    if session_id:
        session_collection = session_db.session_collection
        session_collection.delete_one({"session_id": session_id})
    response = redirect("/login")
    response.delete_cookie("session_id")
    return response


@app.route("/add", methods=["GET"])
def get_create():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    return render_template("add_quote.html")


@app.route("/add", methods=["POST"])
@app.route("/add", methods=["POST"])
def post_create():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response

    session_collection = session_db.session_collection
    session_data = list(session_collection.find({"session_id": session_id}))
    if len(session_data) == 0:
        response = redirect("/logout")
    assert len(session_data) == 1
    session_data = session_data[0]
    user = session_data.get("user", "unknown user")

    quote = request.form.get("quote", "")
    author = request.form.get("author", "")
    public = request.form.get("public", "") == "on"
    comments_allowed = request.form.get("commentsAllowed", "") == "on"

    if quote and author:
        quotes_collection = quotes_db.quotes_collection
        quotes_collection.insert_one({"owner": user, "text": quote, "author": author, "public": public, "comments_allowed": comments_allowed})
    return redirect("/quotes")


@app.route("/edit/<id>", methods=["GET"])
def get_edit(id=None):
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    if id:
        quotes_collection = quotes_db.quotes_collection
        # get the item
        data = quotes_collection.find_one({"_id": ObjectId(id)})
        data["id"] = str(data["_id"])
        return render_template("edit_quote.html", data=data)
    return redirect("/quotes")


@app.route("/edit", methods=["POST"])
def post_edit():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response

    _id = request.form.get("_id", None)
    text = request.form.get("newQuote", "")
    author = request.form.get("newAuthor", "")
    if _id:
        quotes_collection = quotes_db.quotes_collection
        values = {"$set": {"text": text, "author": author}}
        data = quotes_collection.update_one({"_id": ObjectId(_id)}, values)
    return redirect("/quotes")


@app.route("/delete", methods=["GET"])
@app.route("/delete/<id>", methods=["GET"])
def get_delete(id=None):
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response

    if id:
        quotes_collection = quotes_db.quotes_collection
        quotes_collection.delete_one({"_id":ObjectId(id)})
    return redirect("/quotes")
@app.route("/delete/<id>", methods=["POST"])
def post_delete(id):
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        return redirect("/login")

    session_collection = session_db.session_collection
    session_data = list(session_collection.find({"session_id": session_id}))
    if len(session_data) == 0:
        return redirect("/logout")
    
    session_data = session_data[0]
    user = session_data.get("user", "")

    quotes_collection = quotes_db.quotes_collection
    quote_data = quotes_collection.find_one({"_id": ObjectId(id)})
    if not quote_data:
        return redirect("/quotes")

    if user == quote_data.get("owner"):
        quotes_collection.delete_one({"_id": ObjectId(id)})
    
    return redirect("/quotes")
