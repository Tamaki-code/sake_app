from datetime import datetime
from . import db

class Ranking(db.Model):
    __tablename__ = 'rankings'
    id = db.Column(db.Integer, primary_key=True)
    sake_id = db.Column(db.Integer, db.ForeignKey('sakes.id', ondelete='CASCADE'), nullable=False)
    rank = db.Column(db.Integer, nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_sake_category', 'sake_id', 'category'),
    )

    # Define the relationship with Sake model
    sake = db.relationship('Sake', back_populates='rankings')