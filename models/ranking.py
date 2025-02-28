from datetime import datetime
from . import db

class Ranking(db.Model):
    __tablename__ = 'rankings'
    id = db.Column(db.Integer, primary_key=True)
    sake_id = db.Column(db.Integer, db.ForeignKey('sakes.id'), nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'total', 'monthly', etc
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    sake = db.relationship('Sake', backref=db.backref('rankings', lazy='dynamic'))
