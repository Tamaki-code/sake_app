from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import ForeignKeyConstraint

db = SQLAlchemy()

class Region(db.Model):
    __tablename__ = 'regions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sakenowa_id = db.Column('sakenowaId', db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    breweries = db.relationship('Brewery', backref='region', lazy='dynamic')

class Brewery(db.Model):
    __tablename__ = 'breweries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sakenowa_brewery_id = db.Column(db.String(100), unique=True)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    sakes = db.relationship('Sake', backref='brewery', lazy='dynamic')

class Sake(db.Model):
    __tablename__ = 'sakes'
    id = db.Column(db.Integer, primary_key=True)
    sakenowa_id = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(200))
    brewery_id = db.Column(db.Integer, db.ForeignKey('breweries.id'))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviews = db.relationship('Review', backref='sake', lazy='dynamic')

    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(review.rating for review in reviews) / len(reviews)

class FlavorChart(db.Model):
    __tablename__ = 'flavor_charts'
    id = db.Column(db.Integer, primary_key=True)
    sake_id = db.Column(db.Integer, db.ForeignKey('sakes.id'), nullable=False)
    f1 = db.Column(db.Float)
    f2 = db.Column(db.Float)
    f3 = db.Column(db.Float)
    f4 = db.Column(db.Float)
    f5 = db.Column(db.Float)
    f6 = db.Column(db.Float)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    sake = db.relationship('Sake', backref=db.backref('flavor_chart', uselist=False))

class FlavorTag(db.Model):
    __tablename__ = 'flavor_tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sakenowa_id = db.Column('sakenowaId', db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

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

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sake_id = db.Column(db.Integer, db.ForeignKey('sakes.id'), nullable=False)
    rating = db.Column(db.Float)
    aroma = db.Column(db.String(100))
    aftertaste = db.Column(db.String(100))
    drinking_style = db.Column(db.String(100))
    matching_food = db.Column(db.String(100))
    comment = db.Column(db.Text)
    recorded_at = db.Column(db.Date)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    f1 = db.Column(db.Float)
    f2 = db.Column(db.Float)
    f3 = db.Column(db.Float)
    f4 = db.Column(db.Float)
    f5 = db.Column(db.Float)
    f6 = db.Column(db.Float)