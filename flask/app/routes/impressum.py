from pathlib import Path

from flask import Blueprint, render_template


impressum_bp = Blueprint("impressum", __name__)


@impressum_bp.route("/impressum", methods=["GET"])
def impressum():
    return render_template("impressum.html")
