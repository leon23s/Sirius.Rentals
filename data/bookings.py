import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase


class Bookings(SqlAlchemyBase):
    __tablename__ = 'bookings'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    room_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("rooms.id"))
    date_start = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    date_end = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    username = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.name"))
    status = sqlalchemy.Column(sqlalchemy.String, default='active')
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)