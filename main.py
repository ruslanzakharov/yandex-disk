import flask_sqlalchemy
from flask import Flask, jsonify, request
from flask_restful import Api, Resource, abort
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime as dt

FILE, FOLDER = 'FILE', 'FOLDER'

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
    relation = db.relationship(
        'Relation', cascade='all,delete', backref='item')
    history = db.relationship(
        'History', cascade='all,delete', backref='item')


class Relation(db.Model):
    __tablename__ = 'Relations'

    item_id = db.Column(
        db.String,
        db.ForeignKey('Items.id'),
        primary_key=True
    )
    parent_id = db.Column(
        db.String,
    )


class History(db.Model):
    __tablename__ = 'History'

    item_id = db.Column(
        db.String,
        db.ForeignKey(Item.id),
        primary_key=True
    )
    date = db.Column(db.DateTime, primary_key=True)


class ItemPost(Resource):
    def post(self):
        req = request.json

        try:
            for item in req['items']:
                new_item = Item(
                    id=item['id'],
                    type=item['type'],
                    size=item['size']
                )
                relation = Relation(
                    item_id=item['id'],
                    parent_id=item['parentId']
                )
                history = History(
                    item_id=item['id'],
                    date=dt.strptime(
                        req['updateDate'], '%Y-%m-%dT%H:%M:%SZ')
                )
                for obj in [new_item, relation, history]:
                    db.session.add(obj)
                db.session.commit()
        except:
            db.session.rollback()
            return {'code': 400, 'message': 'Validation Failed'}, 400

        return '', 200


def folder_delete(item):
    """Удаляет папку и ее содержимое."""
    for child in Relation.query.filter_by(parent_id=item.id):
        if child.item.type == FILE:
            db.session.delete(child.item)
        elif child.item.type == FOLDER:
            folder_delete(child.item)

    db.session.delete(item)


class ItemDelete(Resource):
    def delete(self, item_id):
        try:
            # date = dt.strptime(request.form['date'], '%Y-%m-%dT%H:%M:%SZ')

            item = Item.query.filter_by(id=item_id).first()
            if not item:
                return {'code': 404, 'message': 'Item not found'}

            if item.type == FILE:
                db.session.delete(item)
            elif item.type == FOLDER:
                folder_delete(item)

            db.session.commit()
        except:
            db.session.rollback()
            return {'code': 400, 'message': 'Validation Failed'}

        return '', 200


api.add_resource(ItemPost, '/imports')
api.add_resource(ItemDelete, '/delete/<item_id>')


if __name__ == '__main__':
    app.run(debug=True, port=5001)
