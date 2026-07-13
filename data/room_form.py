from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class RoomForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    capacity = IntegerField('Вместимость', validators=[DataRequired(), NumberRange(min=1, message='Минимум 1 человек')])
    equipment = StringField('Оборудование через запятую', render_kw={"placeholder": "проектор, доска, принтер и т.д."})
    submit = SubmitField('Добавить комнату')