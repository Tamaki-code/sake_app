"""
Models package initialization
Initialize SQLAlchemy instance
"""
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy without immediate app binding
db = SQLAlchemy()

# Import models and expose them for external use
from .sake import Sake
from .brewery import Brewery
from .region import Region
from .user import User
from .review import Review
from .flavor_chart import FlavorChart
from .flavor_tag import FlavorTag
from .ranking import Ranking

# Export database instance and models
__all__ = [
    'db', 'Sake', 'Brewery', 'Region', 'User', 'Review', 'FlavorChart',
    'FlavorTag', 'Ranking'
]