from flask import Flask, jsonify, request, render_template, redirect, flash, session
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from data import db_session
from datetime import datetime, timedelta

from data.booking_form import BookingForm
from data.login_form import LoginForm
from data.register_form import RegisterForm
from data.room_form import RoomForm
from data.rooms import Rooms
from data.users import User
from data.bookings import Bookings

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Sirius-Rentals-Key'
app.config['JWT_SECRET_KEY'] = 'Sirius-Rentals-JWT-Key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

jwt = JWTManager(app)


@app.route('/rooms', methods=['POST'])
@jwt_required()
def rooms():
    db_sess = db_session.create_session()
    data = request.get_json()
    if not data:
        db_sess.close()
        return jsonify({'msg': 'отсутствуют данные'}), 400

    for f in ['title', 'capacity', 'equipment']:
        if f not in data:
            db_sess.close()
            return jsonify({'msg': f'отсутствует поле {f}'}), 400

    if not isinstance(data['capacity'], int) or data['capacity'] <= 0:
        db_sess.close()
        return jsonify({'msg': 'указанная вместимость некорректна'}), 400

    if not isinstance(data['equipment'], list):
        db_sess.close()
        return jsonify({'msg': 'указанное оборудование некорректно'}), 400

    if data['title'].strip() == '':
        db_sess.close()
        return jsonify({'msg': 'отсутствует название'}), 400

    room = Rooms()
    room.title = data['title']
    room.capacity = data['capacity']
    room.equipment = data['equipment']
    room.user_id = get_jwt_identity()

    db_sess.add(room)
    db_sess.commit()
    db_sess.close()

    return jsonify({'msg': 'комната успешно добавлена'}), 201

@app.route('/rooms', methods=['GET'])
def get_rooms():
    db_sess = db_session.create_session()
    rooms_l = db_sess.query(Rooms).all()
    capacity = request.args.get('capacity')
    if capacity:
        try:
            min_cap = int(capacity)
            rooms_l = [r for r in rooms_l if r.capacity >= min_cap]
        except Exception:
            db_sess.close()
            return jsonify({'msg': 'неверный формат. правильный формат: ?capacity={int}'}), 400

    equipment = request.args.get('equipment')
    if equipment:
        required = [e.strip() for e in equipment.split(',') if e.strip()]
        if required:
            rooms_l = [r for r in rooms_l if any(eq in r.equipment for eq in required)]

    result = [{
        'id': r.id,
        'title': r.title,
        'capacity': r.capacity,
        'equipment': r.equipment,
        'user_id': r.user_id
    } for r in rooms_l]
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

        result = {'id': room.id,
                   'title': room.title,
                   'capacity': room.capacity,
                   'equipment': room.equipment,
                   'user_id': room.user_id,
                   'bookings': [{'id': b.id,
                                'date_start': b.date_start.isoformat(),
                                'date_end': b.date_end.isoformat(),
                                'username': b.username, 'status': b.status
                                } for b in room.bookings if b.status == 'active'],
                   'created_date': room.created_date.isoformat()}
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
            if isinstance(data['capacity'], int) and data['capacity'] > 0:
                room.capacity = data['capacity']
            else:
                db_sess.close()
                return jsonify({'msg': 'некорректная вместимость комнаты'}), 400

        if 'equipment' in data:
            if not isinstance(data['equipment'], list):
                return jsonify({'msg': 'оборудование должно быть списком'}), 400
            room.equipment = data['equipment']

        db_sess.commit()
        db_sess.close()
        return jsonify({'msg': 'комната успешно изменена'}), 200

    if request.method == 'DELETE':
        if room.user_id != get_jwt_identity():
            db_sess.close()
            return jsonify({'msg': 'недостаточно прав'}), 403

        active_bookings = [b for b in room.bookings if b.status == 'active']
        if active_bookings:
            db_sess.close()
            return jsonify({'msg': 'нельзя удалить комнату с активными бронированиями'}), 409

        db_sess.delete(room)
        db_sess.commit()
        db_sess.close()
        return jsonify({'msg': 'комната успешно удалена'}), 200


@app.route('/rooms/available')
def available():
    db_sess = db_session.create_session()
    start_s = request.args['start']
    end_s = request.args['end']
    capacity_s = request.args['capacity']

    if not start_s or not end_s:
        db_sess.close()
        return jsonify({'msg': 'start или end не указаны'}), 400

    try:
        start = datetime.fromisoformat(start_s)
        end = datetime.fromisoformat(end_s)
    except Exception:
        db_sess.close()
        return jsonify({'msg': 'неверный формат даты. требуется iso формат'}), 400

    if start >= end:
        db_sess.close()
        return jsonify({'msg': 'указанный диапазон некорректен'}), 400

    rooms = db_sess.query(Rooms).all()

    if capacity_s:
        try:
            min_capacity = int(capacity_s)
            if min_capacity <= 0:
                db_sess.close()
                return jsonify({'msg': 'capacity должно быть положительным числом'}), 400
            rooms = [r for r in rooms if r.capacity >= min_capacity]

        except Exception:
            db_sess.close()
            return jsonify({'msg': 'некорректные данные'}), 400

    available = []
    for room in rooms:
        c = False

        for booking in room.bookings:
            if booking.status == 'active' and booking.date_start < end and booking.date_end > start:
                c = True
                break

        if not c:
            available.append({
                'id': room.id,
                'title': room.title,
                'capacity': room.capacity,
                'equipment': room.equipment,
                'user_id': room.user_id
            })

    db_sess.close()
    return jsonify(available), 200


@app.route('/rooms/<int:id>/bookings', methods=['GET'])
def bookings_date(id):
    db_sess = db_session.create_session()
    room = db_sess.query(Rooms).filter(Rooms.id == id).first()
    if not room:
        db_sess.close()
        return jsonify({'msg': 'комната не найдена'}), 404

    date_str = request.args['date']
    if not date_str:
        db_sess.close()
        return jsonify({'msg': 'не указана дата'}), 400

    try:
        target_date = datetime.fromisoformat(date_str)
        day_start = target_date.replace(hour=0, minute=0, second=0)
        day_end = target_date.replace(hour=23, minute=59, second=59)
    except Exception:
        db_sess.close()
        return jsonify({'msg': 'неверный формат даты'}), 400

    bookings = db_sess.query(Bookings).filter(Bookings.room_id == id,
                                              Bookings.date_start <= day_end,
                                              Bookings.date_end >= day_start).all()

    result = [{
        'id': b.id,
        'date_start': b.date_start.isoformat(),
        'date_end': b.date_end.isoformat(),
        'username': b.username,
        'status': b.status
    } for b in bookings]

    db_sess.close()
    return jsonify(result), 200

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

    try:
        date_start = datetime.fromisoformat(data['date_start'])
        date_end = datetime.fromisoformat(data['date_end'])
    except Exception as e:
        db_sess.close()
        return jsonify({'msg': 'некорректный формат времени'}), 400

    if date_start >= date_end:
        db_sess.close()
        return jsonify({'msg': 'указанный промежуток времени некорректен'}), 400

    all_bookings = db_sess.query(Bookings).filter(
        Bookings.room == room,
        Bookings.status == 'active'
    ).all()

    for b in all_bookings:
        if not (b.date_end <= date_start or b.date_start >= date_end):
            db_sess.close()
            return jsonify({'msg': 'комната в это время занята'}), 409

    if date_start < datetime.now():
        db_sess.close()
        return jsonify({'msg': 'нельзя бронировать прошедшее время'}), 400

    user_id = get_jwt_identity()
    user = db_sess.query(User).filter(User.id == user_id).first()
    username = user.name

    booking = Bookings()
    booking.date_start = date_start
    booking.date_end = date_end
    booking.status = 'active'
    booking.room = room
    booking.user = user
    booking.username = username

    db_sess.add(booking)
    db_sess.flush()

    db_sess.commit()
    db_sess.close()

    return jsonify({'msg': f'комната успешно забронирована. Название: {room.title}, id комнаты: {room.id}'}), 201


@app.route('/bookings/<int:id>', methods=['DELETE'])
@jwt_required()
def bookings_id(id):
    db_sess = db_session.create_session()
    booking = db_sess.query(Bookings).filter(Bookings.id == id).first()
    if not booking:
        db_sess.close()
        return jsonify({'msg': 'бронирование не найдено'}), 404

    if booking.user_id != get_jwt_identity():
        db_sess.close()
        return jsonify({'msg': 'недостаточно прав'}), 403

    booking.status = 'cancelled'
    db_sess.commit()
    db_sess.close()

    return jsonify({'msg': 'бронирование успешно отменено'}), 200


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
        db_sess.close()
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

    token = create_access_token(identity=str(user.id))
    db_sess.close()
    return jsonify({'access_token': token}), 200


@app.route('/', methods=['GET'])
def index():
    db_sess = db_session.create_session()
    rooms = db_sess.query(Rooms).all()
    db_sess.close()

    user = None
    if 'user_id' in session:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == session['user_id']).first()
        db_sess.close()

    return render_template('index.html', rooms=rooms, current_user=user)

@app.route('/web/register', methods=['POST', 'GET'])
def web_register():
    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            if db_sess.query(User).filter(User.email == form.email.data).first():
                flash('Пользователь с такой почтой уже существует', 'danger')
                return render_template('register.html', form=form, message_flashed=True)

            if form.password.data != form.password_again.data:
                flash('Пароли не совпадают', 'danger')
                return render_template('register.html', form=form, message_flashed=True)

            user = User(
                email=form.email.data,
                name=form.name.data
            )
            user.set_password(form.password.data)

            db_sess.add(user)
            db_sess.commit()

            flash('Регистрация прошла успешно', 'success')
            return redirect('/web/login')
        finally:
            db_sess.close()
    return render_template('register.html', form=form, message_flashed=True)

@app.route('/web/login', methods=['POST', 'GET'])
def web_login():
    form = LoginForm()

    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        db_sess.close()

        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            flash('Успешный вход', 'success')
            return redirect('/')
        flash('Неверный email или пароль', 'danger')

    return render_template('login.html', form=form)

@app.route('/web/logout', methods=['POST', 'GET'])
def web_logout():
    session.pop('user_id')
    flash('Вы вышли', 'success')
    return redirect('/')

@app.route('/web/booking', methods=['POST', 'GET'])
def web_booking():
    if 'user_id' not in session:
        flash('Войдите, чтобы забронировать помещение', 'warning')
        return redirect('/web/login')

    form = BookingForm()

    db_sess = db_session.create_session()
    rooms = db_sess.query(Rooms).all()
    form.room_id.choices = [(r.id, f"{r.title} (вместимость: {r.capacity})") for r in rooms]

    if form.validate_on_submit():
        room_id = form.room_id.data
        date_start = datetime.fromisoformat(form.date_start.data)
        date_end = datetime.fromisoformat(form.date_end.data)

        user = db_sess.query(User).filter(User.id == session['user_id']).first()
        if not user:
            db_sess.close()
            flash('Пользователь не найден', 'danger')
            return render_template('booking.html', form=form)

        if date_start >= date_end:
            db_sess.close()
            flash('Время начала должно быть раньше окончания', 'danger')
            return render_template('booking.html', form=form)

        if date_start < datetime.now():
            db_sess.close()
            flash('Нельзя бронировать прошедшее время', 'danger')
            return render_template('booking.html', form=form)

        room = db_sess.query(Rooms).filter(Rooms.id == room_id).first()
        if not room:
            db_sess.close()
            flash('Комната не найдена', 'danger')
            return render_template('booking.html', form=form)

        for booking in room.bookings:
            if booking.status == 'active':
                if not (booking.date_end <= date_start or booking.date_start >= date_end):
                    db_sess.close()
                    flash('Комната уже занята в это время', 'danger')
                    return render_template('booking.html', form=form)

        room_title = room.title

        booking = Bookings()
        booking.room = room
        booking.user = user
        booking.date_start = date_start
        booking.date_end = date_end
        booking.username = user.name
        booking.status = 'active'

        db_sess.add(booking)
        db_sess.commit()
        db_sess.close()

        flash(f'Комната {room_title} успешно забронирована', 'success')
        return redirect('/')

    return render_template('booking.html', form=form)

@app.route('/web/add_room', methods=['POST', 'GET'])
def web_room():
    if 'user_id' not in session:
        flash('Войдите, чтобы добавить комнату', 'warning')
        return redirect('/web/login')

    form = RoomForm()
    if form.validate_on_submit():
        equipment_list = []
        if form.equipment.data:
            equipment_list = [e.strip() for e in form.equipment.data.split(',') if e.strip()]

        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == session['user_id']).first()
        if not user:
            db_sess.close()
            flash('Пользователь не найден', 'danger')
            return render_template('add_room.html', form=form, current_user=user)

        rooms = db_sess.query(Rooms).filter(Rooms.title == form.title.data).all()
        if len(rooms) > 0:
            db_sess.close()
            flash('Комната с таким названием уже есть', 'danger')
            return render_template('add_room.html', form=form, current_user=user)

        room = Rooms()
        room_title = form.title.data
        room.title = room_title
        room.capacity = form.capacity.data
        room.equipment = equipment_list
        room.user_id = user.id

        db_sess.add(room)
        db_sess.commit()
        db_sess.close()

        flash(f'Комната {room_title} успешно добавлена', 'success')
        return redirect('/')

    user = None
    if 'user_id' in session:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == session['user_id']).first()
        db_sess.close()
    return render_template('add_room.html', form=form, current_user=user)


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Войдите, чтобы просмотреть профиль', 'warning')
        return redirect('/web/login')

    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == session['user_id']).first()
    if not user:
        db_sess.close()
        flash('Пользователь не найден', 'danger')
        return redirect('/')

    bookings_data = []
    bookings = db_sess.query(Bookings).filter(Bookings.user_id == user.id, Bookings.status == 'active').all()
    for b in bookings:
        bookings_data.append({
            'id': b.id,
            'room_title': b.room.title,
            'date_start': b.date_start,
            'date_end': b.date_end,
            'status': b.status
        })
    db_sess.close()

    return render_template('profile.html', user=user, bookings=bookings_data)



def main():
    db_session.global_init("db/Rental.db")
    app.run(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()