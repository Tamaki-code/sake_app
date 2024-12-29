"""
Models package initialization
Initialize SQLAlchemy instance
"""
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy without immediate app binding
db = SQLAlchemy()

# Export database instance
__all__ = ['db']