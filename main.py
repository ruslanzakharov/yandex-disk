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
    url = db.Column(db.String)
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
        db.String
    )


class History(db.Model):
    __tablename__ = 'History'

    item_id = db.Column(
        db.String,
        db.ForeignKey(Item.id),
        primary_key=True
    )
    date = db.Column(db.DateTime)


def string_to_dt(dt_string):
    """Превращает строку в объект DateTime."""
    return dt.strptime(dt_string, '%Y-%m-%dT%H:%M:%SZ')


def dt_to_string(dt_obj):
    """Превращает объект DateTime в строку."""
    return dt_obj.strftime('%Y-%m-%dT%H:%M:%SZ')


def new_item(item_json, datetime):
    new_item = Item(
        id=item_json['id'],
        type=item_json['type'],
        url=item_json['url'],
        size=item_json['size'] if item_json['type'] == FILE else 0
    )
    relation = Relation(
        item_id=item_json['id'],
        parent_id=item_json['parentId']
    )
    history = History(
        item_id=item_json['id'],
        date=string_to_dt(datetime)
    )
    for obj in [new_item, relation, history]:
        db.session.add(obj)


def update_item(item_json, datetime):
    rel = Relation.query.filter_by(item_id=item_json['id']).first()

    rel.item.size = item_json['size']
    rel.parent_id = item_json['parentId']
    rel.url = item_json['url']

    history = History.query.filter_by(item_id=item_json['id']).first()
    history.date = string_to_dt(datetime)


class ItemPost(Resource):
    def post(self):
        req = request.json

        try:
            for item in req['items']:
                if not Item.query.filter_by(id=item['id']).first():
                    new_item(item, req['updateDate'])
                else:
                    update_item(item, req['updateDate'])

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


def children_info(item_id):
    """Возвращает информацию о дочерних элементах папки"""
    children = []
    for child in Relation.query.filter_by(parent_id=item_id):
        history = History.query.filter_by(item_id=child.item_id).first()
        child_json = {
            'id': child.item.id,
            'url': child.item.url,
            'type': child.item.type,
            'date': dt_to_string(history.date),
            'size': child.item.size,
            'children': None,
        }
        if child.item.type == FOLDER:
            child_json['children'] = children_info(child.item_id)

        children.append(child_json)

    return children


class ItemGet(Resource):
    def get(self, item_id):
        try:
            item = Item.query.filter_by(id=item_id).first()
            if not item:
                return {'code': 404, 'message': 'Item not found'}, 404
            history = History.query.filter_by(item_id=item_id).first()

            res = {
                'id': item_id,
                'url': item.url,
                'type': item.type,
                'date': dt_to_string(history.date),
                'size': item.size,
                'children': None,
            }

            if res['type'] == FILE:
                return res, 200

            res['children'] = children_info(item.id)
            return res, 200
        except:
            return {'code': 400, 'message': 'Validation Failed'}, 400


api.add_resource(ItemPost, '/imports')
api.add_resource(ItemDelete, '/delete/<item_id>')
api.add_resource(ItemGet, '/nodes/<item_id>')


if __name__ == '__main__':
    app.run(debug=True, port=5001)
