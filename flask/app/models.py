from . import db
from sqlalchemy.dialects.mysql import INTEGER, VARCHAR


class Users(db.Model):
    id = db.Column(INTEGER(unsigned=True), primary_key=True)
    name = db.Column(VARCHAR(255), nullable=False)
    password = db.Column(VARCHAR(255), nullable=False)
