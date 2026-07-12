import pytest
import json
import tempfile
import os

from main import app
from data import db_session
from data.db_session import SqlAlchemyBase


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    db_session.global_init(db_path)

    engine = db_session.__factory().bind
    SqlAlchemyBase.metadata.create_all(engine)

    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client

    db_session.__factory().close_all()
    engine.dispose()
    os.close(db_fd)
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
def auth_token(client):
    client.post('/register', json={
        'email': 'test@mail.com',
        'password': '123',
        'name': 'пользователь 1'
    })
    resp = client.post('/login', json={
        'email': 'test@mail.com',
        'password': '123'
    })
    assert resp.status_code == 200
    return json.loads(resp.data)['access_token']


def test_register(client):
    resp = client.post('/register', json={
        'email': 'new@mail.com',
        'password': 'pass',
        'name': 'пользователь 2'
    })
    assert resp.status_code == 201


def test_login(client):
    client.post('/register', json={
        'email': 'login@mail.com',
        'password': 'pass',
        'name': 'пользователь 3'
    })
    resp = client.post('/login', json={
        'email': 'login@mail.com',
        'password': 'pass'
    })
    assert resp.status_code == 200
    assert 'access_token' in json.loads(resp.data)


def test_post_room(client, auth_token):
    headers = {'Authorization': f'Bearer {auth_token}'}
    resp = client.post('/rooms', json={
        'title': 'комната 1',
        'capacity': 10,
        'equipment': ['проектор', 'доска']
    }, headers=headers)
    if resp.status_code != 201:
        print("POST /rooms ответ:", resp.data.decode())
    assert resp.status_code == 201


def test_get_rooms(client, auth_token):
    headers = {'Authorization': f'Bearer {auth_token}'}
    client.post('/rooms', json={
        'title': 'комната 2',
        'capacity': 5,
        'equipment': ['доска', 'принтер']
    }, headers=headers)

    resp = client.get('/rooms', headers=headers)
    if resp.status_code != 200:
        print("GET /rooms ответ:", resp.data.decode())
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)
    assert len(data) > 0