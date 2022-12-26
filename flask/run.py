from json import load

from app import create_app


conf = load(open("data.json", "r"))


socket, app = create_app()
socket.run(host=conf["host"], port=conf["port"], debug=conf["debug"])
