from json import load

from app import create_app


conf = load(open("data.json", "r"))


app, socket = create_app()
app.run(host=conf["host"], port=conf["port"], debug=conf["debug"])
