from flask import Flask, request
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime as dt

FILE, FOLDER = 'FILE', 'FOLDER'

app = Flask(__name__)
api = Api(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Item(db.Model):
    __tablename__ = 'Items'

    id = db.Column(db.String, primary_key=True)
    type = db.Column(db.String, nullable=False)
    parent_id = db.Column(db.String, default=None)
    size = db.Column(db.BigInteger, default=None)
    url = db.Column(db.String(255), default=None)
    date = db.Column(db.DateTime, nullable=False)


def string_to_dt(dt_string):
    """Превращает строку в объект DateTime."""
    return dt.strptime(dt_string, '%Y-%m-%dT%H:%M:%SZ')


def dt_to_string(dt_obj):
    """Превращает объект DateTime в строку."""
    return dt_obj.strftime('%Y-%m-%dT%H:%M:%SZ')


def new_item(item, datetime):
    """Добавляет новый элемент."""
    if item['type'] == FOLDER:
        folder = Item(
            id=item['id'],
            type=FOLDER,
            parent_id=item['parentId'],
            date=string_to_dt(datetime)
        )
        db.session.add(folder)
    elif item['type'] == FILE:
        file = Item(
            id=item['id'],
            type=FILE,
            parent_id=item['parentId'],
            date=string_to_dt(datetime),
            url=item['url'],
            size=item['size']
        )
        db.session.add(file)

        update_folder_sizes(file, file.size, file.date)


def update_item(item, datetime):
    """Обновляет элемент."""
    dt_obj = string_to_dt(datetime)

    if item['type'] == FOLDER:
        folder = Item.query.filter_by(id=item['id']).first()

        old_parent_id = folder.parent_id
        new_parent_id = item['parentId']
        if old_parent_id != new_parent_id and folder.size:
            # Уменьшаем размеры родительских папок в предыдущем месте
            update_folder_sizes(folder, -folder.size, dt_obj)

        folder.parent_id = new_parent_id
        folder.date = datetime

        if old_parent_id != new_parent_id and folder.size:
            # Увеличиваем размеры родительских папок в новом месте
            update_folder_sizes(folder, folder.size, dt_obj)

    elif item['type'] == FILE:
        file = Item.query.filter_by(id=item['id']).first()

        old_parent_id = file.parent_id
        new_parent_id = item['parentId']
        old_size = file.size
        new_size = item['size']
        if old_parent_id != new_parent_id or old_size != new_size:
            # Уменьшаем размеры родительских папок в предыдущем месте
            # либо
            # уменьшаем размеры родительских папок в текущем месте
            update_folder_sizes(file, -file.size, dt_obj)

        file.parent_id = item['parentId']
        file.date = dt_obj
        file.url = item['url']
        file.size = item['size']

        if old_parent_id != new_parent_id:
            # Увеличиваем размеры родительских папок в новом месте
            update_folder_sizes(file, file.size, dt_obj)

        update_folder_sizes(file, file.size, dt_obj)


def update_folder_sizes(item, diff, dt_obj):
    """Обновляет веса родительских папок."""
    if item.parent_id:
        parent = Item.query.filter_by(id=item.parent_id).first()
        if parent.size:
            parent.size += diff
        else:
            parent.size = diff

        parent.date = dt_obj
        update_folder_sizes(parent, diff, dt_obj)


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
    for child in Item.query.filter_by(parent_id=item.id):
        if child.type == FILE:
            db.session.delete(child)
        elif child.type == FOLDER:
            folder_delete(child)

    db.session.delete(item)


class ItemDelete(Resource):
    def delete(self, item_id):
        try:
            date = string_to_dt(request.args['date'])

            item = Item.query.filter_by(id=item_id).first()
            if not item:
                return {'code': 404, 'message': 'Item not found'}, 404

            if item.type == FILE:
                db.session.delete(item)
                update_folder_sizes(item, -item.size, date)
            elif item.type == FOLDER:
                folder_delete(item)
                update_folder_sizes(item, -item.size, date)

            db.session.commit()
        except:
            db.session.rollback()
            return {'code': 400, 'message': 'Validation Failed'}, 400

        return '', 200


def children_info(item):
    """Возвращает информацию о дочерних элементах папки."""
    children = []

    for child in Item.query.filter_by(parent_id=item.id):
        child_json = {
            'id': child.id,
            'url': child.url,
            'parentId': child.parent_id,
            'type': child.type,
            'date': dt_to_string(child.date),
            'size': child.size,
            'children': None,
        }
        if child.type == FOLDER:
            child_json['children'] = children_info(child)

        children.append(child_json)

    return children


class ItemGet(Resource):
    def get(self, item_id):
        try:
            item = Item.query.filter_by(id=item_id).first()
            if not item:
                return {'code': 404, 'message': 'Item not found'}, 404

            res = {
                'id': item.id,
                'url': item.url,
                'parentId': item.parent_id,
                'type': item.type,
                'date': dt_to_string(item.date),
                'size': item.size,
                'children': None,
            }

            if item.type == FOLDER:
                res['children'] = children_info(item)

            return res, 200
        except:
            return {'code': 400, 'message': 'Validation Failed'}, 400


api.add_resource(ItemPost, '/imports')
api.add_resource(ItemDelete, '/delete/<item_id>')
api.add_resource(ItemGet, '/nodes/<item_id>')


if __name__ == '__main__':
    app.run(debug=True, port=8080, host='localhost')
