from flask import Flask, jsonify, request
from flask_restful import Api, Resource, reqparse
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
api = Api(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///disk.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Item(db.Model):
    __tablename__ = 'Items'

    id = db.Column(db.String, primary_key=True)
    type = db.Column(db.String, nullable=False)
    size = db.Column(db.BigInteger)


class Parent(db.Model):
    __tablename__ = 'Parents'

    item_id = db.Column(
        db.String,
        db.ForeignKey('Items.id', ondelete='CASCADE'),
        primary_key=True
    )
    parent_id = db.Column(
        db.String,
        db.ForeignKey('Items.id', ondelete='CASCADE')
    )


class History(db.Model):
    __tablename__ = 'History'

    item_id = db.Column(
        db.String,
        db.ForeignKey('Items.id', ondelete='CASCADE'),
        primary_key=True
    )
    date = db.Column(db.DateTime, primary_key=True)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
