from datetime import datetime
from . import db

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
