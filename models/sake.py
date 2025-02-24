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
    flavor_chart = db.relationship('FlavorChart', backref='sake', uselist=False) # Added relationship


    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(review.rating for review in reviews) / len(reviews)

    def get_flavor_profile(self):
        """Get the sake's flavor profile from the flavor chart"""
        if not hasattr(self, 'flavor_chart') or not self.flavor_chart:
            return None

        return {
            '華やか-重厚': self.flavor_chart.f1,
            '薫酒-燗酒': self.flavor_chart.f2,
            '淡麗-濃醇': self.flavor_chart.f3,
            '甘口-辛口': self.flavor_chart.f4,
            '特性-個性': self.flavor_chart.f5,
            '若年-熟成': self.flavor_chart.f6
        }

    def get_flavor_description(self):
        """Get a descriptive interpretation of the flavor profile"""
        profile = self.get_flavor_profile()
        if not profile:
            return None

        descriptions = []
        for key, value in profile.items():
            left, right = key.split('-')
            if value < 0.4:
                descriptions.append(f"やや{left}な")
            elif value > 0.6:
                descriptions.append(f"やや{right}な")

        return ''.join(descriptions) if descriptions else '標準的な'