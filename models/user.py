from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(64), unique=True)
    encrypted_password = db.Column('encrypted_password', db.String(256), nullable=False)
    reset_password_token = db.Column(db.String(100))
    reset_password_sent_at = db.Column(db.DateTime)
    remember_created_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    gender = db.Column(db.String(20))
    birthdate = db.Column(db.Date)
    comment = db.Column(db.Text)
    reviews = db.relationship('Review', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.encrypted_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.encrypted_password, password)
