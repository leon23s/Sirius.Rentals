from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from data import db_session
from datetime import datetime
import datetime

from data.rooms import Rooms
from data.users import User
from data.bookings import Bookings

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Sirius-Rentals-Key'
app.config['JWT_SECRET_KEY'] = 'Sirius-Rentals-JWT-Key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)

jwt = JWTManager(app)


@app.route('/rooms', methods=['POST', 'GET'])
@jwt_required()
def rooms():
    db_sess = db_session.create_session()
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            db_sess.close()
            return jsonify({'msg': 'отсутствуют данные'}), 400

        for f in ['title', 'capacity', 'equipment']:
            if f not in data:
                db_sess.close()
                return jsonify({'msg': f'отсутствует поле {f}'}), 400

        room = Rooms()
        room.title = data['title']
        room.capacity = data['capacity']
        room.equipment = data['equipment']
        room.user_id = get_jwt_identity()

        db_sess.add(room)
        db_sess.commit()
        db_sess.close()

        return jsonify({'msg': 'комната успешно добавлена'}), 200

    if request.method == 'GET':
        rooms_list = db_sess.query(Rooms).all()
        result = [{
            'id': r.id,
            'title': r.title,
            'capacity': r.capacity,
            'equipment': r.equipment,
            'user_id': r.user_id
        } for r in rooms_list]
        db_sess.close()
        return jsonify(result), 200

@app.route('/rooms/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def room(id):
    db_sess = db_session.create_session()
    room = db_sess.query(Rooms).filter(Rooms.id == id).first()
    if not room:
        db_sess.close()
        return jsonify({'msg': 'комната не найдена'}), 404

    if request.method == 'GET':

        result = [{'id': room.id,
                   'title': room.title,
                   'capacity': room.capacity,
                   'equipment': room.equipment,
                   'user_id': room.user_id,
                   'booking': [{
                       'id': b.id,
                       'date_start': b.date_start.isoformat(),
                       'date_end': b.date_end.isoformat(),
                       'username': b.username,
                       'status': b.status
                   } for b in room.booking],
                   'created_date': room.created_date}]
        db_sess.close()
        return jsonify(result), 200

    if request.method == 'PUT':
        data = request.get_json()
        if not data:
            db_sess.close()
            return jsonify({'msg': 'отсутствуют данные'}), 400

        if room.user_id != get_jwt_identity():
            db_sess.close()
            return jsonify({'msg': 'недостаточно прав для редактирования'}), 403

        if 'title' in data:
            room.title = data['title']

        if 'capacity' in data:
            if type(data['capacity']) == int and data['capacity'] > 0:
                room.capacity = data['capacity']
            else:
                db_sess.close()
                return jsonify({'msg': 'некорректная вместимость комнаты'}), 400

        if 'equipment' in data:
            room.equipment = data['equipment']

        db_sess.commit()
        db_sess.close()
        return jsonify({'msg': 'комната успешно изменена'}), 200

    if request.method == 'DELETE':
        if room.user_id != get_jwt_identity():
            db_sess.close()
            return jsonify({'msg': 'недостаточно прав для редактирования'}), 403

        db_sess.delete(room)
        db_sess.commit()
        db_sess.close()

@app.route('/bookings', methods=['POST'])
@jwt_required()
def bookings():
    db_sess = db_session.create_session()
    data = request.get_json()
    if not data:
        db_sess.close()
        return jsonify({'msg': 'отсутствуют данные'}), 400

    for f in ['room_id', 'date_start', 'date_end']:
        if f not in data:
            db_sess.close()
            return jsonify({'msg': f'отсутствует поле {f}'}), 400
    room = db_sess.query(Rooms).filter(Rooms.id == data['room_id']).first()
    if room is None:
        db_sess.close()
        return jsonify({'msg': 'указанная комната не найдена'}), 404

    room_booking = room.booking
    if room_booking != []:
        for booking in room_booking:
            date_start = datetime.fromisoformat(booking.date_start)
            date_end = datetime.fromisoformat(booking.date_end)
            if not (booking.date_end <= date_start or booking.date_start >= date_end):
                db_sess.close()
                return jsonify({'msg': 'комната в это время занята'}), 409

    user_id = get_jwt_identity()
    user = db_sess.query(User).filter(User.id == user_id).first()
    username = user.name

    booking = Bookings()
    booking.room_id = room.id
    booking.date_start = data['date_start']
    booking.date_end = data['date_end']
    booking.username = username
    booking.status = 'active'

    db_sess.add(booking)
    db_sess.commit()
    db_sess.close()

    return jsonify({'msg': f'комната успешно забронирована. Название: {room.title}, id комнаты: {room.id}'}), 200


@app.route('/bookings/<int:id>', methods=['DELETE'])
@jwt_required()
def bookings(id):
    pass


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'msg': 'отсутствуют данные'}), 400

    if not data.get('email') or not data.get('password'):
        return jsonify({'msg': 'отсутствуют email или пароль'}), 400

    if not data.get('name'):
        return jsonify({'msg': 'отсутствует имя пользователя'}), 400

    db_sess = db_session.create_session()
    if db_sess.query(User).filter(User.email == data['email']).first():
        return jsonify({'msg': 'пользователь с этим email уже зарегистрирован'}), 409

    user = User()
    user.name = data['name']
    user.email = data['email']
    user.set_password(data['password'])
    db_sess.add(user)
    db_sess.commit()
    db_sess.close()

    return jsonify({'msg': 'пользователь создан'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'msg': 'отсутствуют данные'}), 400

    if not data.get('email') or not data.get('password'):
        return jsonify({'msg': 'отсутствуют email или пароль'}), 400

    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.email == data['email']).first()

    if not user or not user.check_password(data['password']):
        db_sess.close()
        return jsonify({'msg': 'неверный email или пароль'}), 401

    token = create_access_token(identity=user.id)
    db_sess.close()
    return jsonify({'access_token': token}), 200


def main():
    db_session.global_init("db/Rental.db")
    app.run()


if __name__ == '__main__':
    main()