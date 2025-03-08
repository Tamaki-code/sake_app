from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import db
from models.user import User
from models.sake import Sake
from models.review import Review
from models.brewery import Brewery
from models.region import Region
from models.flavor_chart import FlavorChart
from models.brand_flavor_tag import BrandFlavorTag
from models.flavor_tag import FlavorTag
from models.ranking import Ranking
import logging
from datetime import datetime
from forms import SignupForm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ])
logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('main', __name__)

@bp.route('/flavor-tag/<string:tag_name>')
def flavor_tag_ranking(tag_name):
    try:
        logger.info(f"Fetching sake ranking for flavor tag: {tag_name}")

        # Get sakes with this flavor tag and their rankings, ordered by ranking score
        sakes_with_rankings = db.session.query(Sake, Ranking)\
            .join(BrandFlavorTag)\
            .join(FlavorTag)\
            .filter(FlavorTag.name == tag_name)\
            .join(Brewery)\
            .join(Region)\
            .outerjoin(Ranking, (Ranking.sake_id == Sake.id) & (Ranking.category == 'overall'))\
            .order_by(Ranking.score.desc().nullslast())\
            .limit(20)\
            .all()

        # Separate sakes and their rankings
        sakes = []
        for sake, ranking in sakes_with_rankings:
            sake.ranking_score = ranking.score if ranking else None
            sakes.append(sake)
            logger.debug(f"Sake: {sake.name}, Ranking Score: {sake.ranking_score}, " \
                       f"Brewery: {sake.brewery.name}, Region: {sake.brewery.region.name}")

        logger.info(f"Found {len(sakes)} sakes with flavor tag '{tag_name}'")

        return render_template('flavor_tag_ranking.html', 
                             tag_name=tag_name,
                             sakes=sakes)
    except Exception as e:
        logger.error(f"Error in flavor_tag_ranking route for ID {tag_name}: {str(e)}", exc_info=True)
        flash('フレーバータグによる銘柄の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('main.index'))

@bp.route('/')
def index():
    try:
        # Get top 10 overall rankings
        top_rankings = db.session.query(Ranking, Sake)\
            .join(Sake)\
            .filter(Ranking.category == 'overall')\
            .order_by(Ranking.rank)\
            .limit(10)\
            .all()

        search_results = db.session.query(Sake) \
            .order_by(Sake.created_at.desc()) \
            .all()

        return render_template('index.html', 
                             search_results=search_results,
                             top_rankings=top_rankings)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash('エラーが発生しました。しばらくしてから再度お試しください。', 'error')
        return render_template('index.html', 
                             search_results=[],
                             top_rankings=[])

@bp.route('/sake/<int:sake_id>')
def sake_detail(sake_id):
    try:
        logger.info(f"Fetching sake details for ID: {sake_id}")
        sake = db.session.query(Sake) \
            .join(Brewery) \
            .join(Region) \
            .filter(Sake.id == sake_id) \
            .first_or_404()

        logger.info(f"Found sake: {sake.name}")
        logger.debug(f"Flavor tags for sake {sake_id}: {[tag.name for tag in sake.get_flavor_tags()]}")

        reviews = sake.reviews.order_by(Review.created_at.desc()).all()
        logger.info(f"Found {len(reviews)} reviews")

        return render_template('sake_detail.html', sake=sake, reviews=reviews)
    except Exception as e:
        logger.error(f"Error in sake_detail route for ID {sake_id}: {str(e)}", exc_info=True)
        flash('日本酒の詳細情報の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('main.index'))

# Add other existing routes here...