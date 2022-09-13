import flask_sqlalchemy
from flask import Flask, jsonify, request
from flask_restful import Api, Resource, abort
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime as dt

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
        db.ForeignKey('Items.id', ondelete='CASCADE'),
    )


class History(db.Model):
    __tablename__ = 'History'

    item_id = db.Column(
        db.String,
        db.ForeignKey('Items.id', ondelete='CASCADE'),
        primary_key=True
    )
    date = db.Column(db.DateTime, primary_key=True)


class Imports(Resource):
    def post(self):
        req = request.json

        try:
            for item in req['items']:
                new_item = Item(
                    id=item['id'],
                    type=item['type'],
                    size=item['size']
                )
                parent = Parent(
                    item_id=item['id'],
                    parent_id=item['parentId']
                )
                history = History(
                    item_id=item['id'],
                    date=dt.strptime(
                        req['updateDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
                )
                for obj in [new_item, parent, history]:
                    db.session.add(obj)
                db.session.commit()
        except:
            db.session.rollback()
            return {'code': 400, 'message': 'Validation Failed'}, 400

        return '', 200


api.add_resource(Imports, '/imports')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
