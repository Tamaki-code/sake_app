"""
Models package initialization
Initialize SQLAlchemy instance
"""
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy without immediate app binding
db = SQLAlchemy()

# Import models
from models.user import User
from models.region import Region
from models.brewery import Brewery
from models.sake import Sake
from models.review import Review
from models.flavor_chart import FlavorChart
from models.flavor_tag import FlavorTag

# Export all models
__all__ = ['db', 'User', 'Region', 'Brewery', 'Sake', 'Review', 'FlavorChart', 'FlavorTag']