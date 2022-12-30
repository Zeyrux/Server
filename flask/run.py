from json import load

from app import create_app


conf = load(open("data.json", "r"))


app, socket = create_app()
# app.run(host="localhost", port=5010, debug=conf["debug"])s