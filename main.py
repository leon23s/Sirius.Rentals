from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from data import db_session
import datetime
from data.users import User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Sirius-Rentals-Key'
app.config['JWT_SECRET_KEY'] = 'Sirius-Rentals-JWT-Key'
app.config['JWT_LIFE'] = datetime.timedelta(hours=1)

jwt = JWTManager(app)


@app.route('/rooms', methods=['POST', 'GET'])
def rooms():
    if request.method == 'POST':
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
        return jsonify({'msg': 'неверный email или пароль'}), 401

    token = create_access_token(identity=user.id)
    return jsonify({'access_token': token}), 200



def main():
    db_session.global_init("db/Rental.db")
    app.run()


if __name__ == '__main__':
    main()