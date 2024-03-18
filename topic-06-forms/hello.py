from flask import Flask, render_template, request #, redirect

app = Flask(__name__)

@app.route("/hello", methods=["GET"])
def get_hello():
    data = {
        "name":None,
        "password":None
    }
    return render_template("hello.html", data=data)

@app.route("/hello", methods=["POST"])
def post_hello():
    name = request.form.get("name", None)
    password = request.form.get("password", None)
    print([name, password])
    data = {
        "name":name,
        "password":password
    }
    return render_template("hello.html", data=data)
    # usually do a redirect('....')
