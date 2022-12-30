from json import load

from run import app, socket


conf = load(open("data.json", "r"))
app.run(host="localhost", port=5010, debug=conf["debug"])
