from flask import Flask, request

app = Flask(__name__)

@app.route("/lti/login")
def login():
    return "Login LTI recibido correctamente"

if __name__ == "__main__":
    app.run(debug=True)