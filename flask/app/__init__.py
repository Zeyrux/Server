from json import load
from pathlib import Path
from secrets import token_urlsafe

from flask_socketio import SocketIO
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
app = Flask(__name__)
socket = SocketIO(app)


def create_app():
    # app
    app.config["SECRET_KEY"] = token_urlsafe(25)
    data = load(open(Path("data.json"), "r"))
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{data['db']['username']}:{data['db']['password']}"
        + f"@{data['db']['host']}:{data['db']['port']}/"
        + f"{data['db']['db_name']}"
    )
    # db.init_app(app)

    # routes
    from .routes import routes

    app.register_blueprint(routes, url_prefix="/")

    # login manager
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "If you want to use this site, you need to login!"
    login_manager.login_message_category = "error"
    login_manager.init_app(app)

    from .models import Users

    @login_manager.user_loader
    def load_user(id):
        return Users.query.get(int(id))

    # @app.before_first_request
    # def init_app():
    #     create_database(app)

    return app, socket


def create_database(app: Flask):
    db.create_all()
    print("Created Database!")
