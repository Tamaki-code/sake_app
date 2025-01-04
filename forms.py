from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models.user import User

class SignupForm(FlaskForm):
    username = StringField('Username', 
                         validators=[DataRequired(), 
                                   Length(min=3, max=64, message='ユーザー名は3文字以上64文字以下で入力してください')])
    email = StringField('Email', 
                       validators=[DataRequired(), 
                                 Email(message='有効なメールアドレスを入力してください')])
    password = PasswordField('Password', 
                           validators=[DataRequired(),
                                     Length(min=6, message='パスワードは6文字以上で入力してください')])
    password_confirm = PasswordField('Confirm Password',
                                   validators=[DataRequired(),
                                             EqualTo('password', message='パスワードが一致しません')])

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('このユーザー名は既に使用されています')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('このメールアドレスは既に登録されています')
