from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

class BookingForm(FlaskForm):
    room_id = SelectField('Комната', coerce=int, validators=[DataRequired()])
    date_start = StringField('Начало', validators=[DataRequired()], render_kw={"type": "datetime-local"})
    date_end = StringField('Конец', validators=[DataRequired()], render_kw={"type": "datetime-local"})
    submit = SubmitField('Забронировать')