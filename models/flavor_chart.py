from datetime import datetime
from . import db

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
