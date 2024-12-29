from datetime import datetime
from . import db

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
