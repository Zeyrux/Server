from json import load
from pathlib import Path

from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_login import login_required, current_user

home_bp = Blueprint("home", __name__)


@home_bp.route("/", methods=["GET"])
def home():
    return render_template("home.html", projects=load(open(Path("projects.json"), "r")))
