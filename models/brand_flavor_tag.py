from datetime import datetime
from . import db

class BrandFlavorTag(db.Model):
    __tablename__ = 'brand_flavor_tags'
    id = db.Column(db.Integer, primary_key=True)
    sake_id = db.Column(db.Integer, db.ForeignKey('sakes.id'), nullable=False)
    flavor_tag_id = db.Column(db.Integer, db.ForeignKey('flavor_tags.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    sake = db.relationship('Sake', backref=db.backref('flavor_tags', lazy='dynamic'))
    flavor_tag = db.relationship('FlavorTag')
