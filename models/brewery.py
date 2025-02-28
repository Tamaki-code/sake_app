from datetime import datetime
from . import db

class Brewery(db.Model):
    __tablename__ = 'breweries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    sakenowa_brewery_id = db.Column(db.String(10), unique=True, nullable=False, index=True)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sakes = db.relationship('Sake', backref='brewery', lazy='dynamic',
                          cascade='all, delete-orphan')