import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase


class Bookings(SqlAlchemyBase):
    __tablename__ = 'bookings'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    room_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('rooms.id'))
    date_start = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    date_end = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    username = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    status = sqlalchemy.Column(sqlalchemy.String, default='active')
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    room = sqlalchemy.orm.relationship('Rooms', back_populates='bookings')
    user = sqlalchemy.orm.relationship('User', back_populates='bookings')