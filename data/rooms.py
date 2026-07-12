import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase


class Rooms(SqlAlchemyBase):
    __tablename__ = 'rooms'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    capacity = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    equipment = sqlalchemy.Column(sqlalchemy.JSON, default=[])
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    bookings = sqlalchemy.orm.relationship(
        'Bookings',
        back_populates='room',
        cascade='all, delete-orphan'
    )
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)