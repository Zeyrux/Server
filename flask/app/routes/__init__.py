from .home import home_bp

from flask import Blueprint


routes = Blueprint("routes", __name__)
routes.register_blueprint(home_bp, url_prefix="/")
