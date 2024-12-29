from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_models(app):
    db.init_app(app)

    # Import all models here after db initialization
    # to avoid circular imports
    from .user import User  # noqa: F401
    from .region import Region  # noqa: F401
    from .brewery import Brewery  # noqa: F401
    from .sake import Sake  # noqa: F401
    from .review import Review  # noqa: F401
    from .flavor_chart import FlavorChart  # noqa: F401
    from .flavor_tag import FlavorTag  # noqa: F401

    return db