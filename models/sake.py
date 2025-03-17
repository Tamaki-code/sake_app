from datetime import datetime
from . import db

class Sake(db.Model):
    __tablename__ = 'sakes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    sakenowa_id = db.Column(db.String(10), unique=True, nullable=False, index=True)
    brewery_id = db.Column(db.Integer, db.ForeignKey('breweries.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Define relationships with back_populates instead of backref
    brewery = db.relationship('Brewery', back_populates='sakes')
    reviews = db.relationship('Review', backref='sake', lazy='dynamic',
                            cascade='all, delete-orphan')
    rankings = db.relationship('Ranking', back_populates='sake', lazy='dynamic',
                             cascade='all, delete-orphan')
    flavor_chart = db.relationship('FlavorChart', backref=db.backref('sake', uselist=False),
                                 uselist=False, cascade='all, delete-orphan')

    def average_rating(self):
        """Get the average rating for this sake"""
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(review.rating for review in reviews) / len(reviews)

    def get_flavor_profile(self):
        """Get the sake's flavor profile from the flavor chart"""
        if not self.flavor_chart:
            return None

        return {
            '華やか-重厚': self.flavor_chart.f1,
            '香り-温度': {'value': self.flavor_chart.f2, 'description': '弱い-強い'},
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
            if isinstance(value, dict):
                continue
            if value < 0.4:
                left = key.split('-')[0]
                descriptions.append(f"やや{left}な")
            elif value > 0.6:
                right = key.split('-')[1]
                descriptions.append(f"やや{right}な")

        return ''.join(descriptions) if descriptions else '標準的な'

    def get_flavor_tags(self):
        """Get all flavor tags for this sake"""
        from models.brand_flavor_tag import BrandFlavorTag
        brand_flavor_tags = BrandFlavorTag.query.filter_by(sake_id=self.id).all()
        return sorted([tag.flavor_tag for tag in brand_flavor_tags], key=lambda x: x.name)