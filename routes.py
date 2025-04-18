from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import db
from models.user import User
from models.sake import Sake
from models.review import Review
from models.brewery import Brewery
from models.region import Region
from models.flavor_chart import FlavorChart
from models.ranking import Ranking  # 追加: Rankingモデルのimport
import logging
from datetime import datetime
from forms import SignupForm
from sqlalchemy.orm import joinedload

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

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = SignupForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            # Log in the user after successful registration
            login_user(user)
            flash('アカウントの登録が完了しました！', 'success')
            return redirect(url_for('main.index'))

        except Exception as e:
            logger.error(f"Error in signup: {str(e)}")
            db.session.rollback()
            flash('アカウントの登録中にエラーが発生しました。', 'error')

    return render_template('signup.html', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            if not username or not password:
                flash('ユーザー名とパスワードを入力してください。', 'error')
                return render_template('login.html')

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash('ログインに成功しました。', 'success')
                return redirect(url_for('main.index'))

            flash('ユーザー名またはパスワードが正しくありません。', 'error')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('ログイン処理中にエラーが発生しました。', 'error')

    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    try:
        logout_user()
        flash('ログアウトしました。', 'success')
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        flash('ログアウト処理中にエラーが発生しました。', 'error')
    return redirect(url_for('main.index'))

@bp.route('/')
def index():
    try:
        # Get top 10 overall rankings with optimized query
        top_rankings = db.session.query(Ranking, Sake)\
            .join(Sake)\
            .options(
                joinedload(Sake.brewery).joinedload(Brewery.region)
            )\
            .filter(Ranking.category == 'overall')\
            .order_by(Ranking.rank)\
            .limit(10)\
            .all()

        # Get latest sakes with eager loading
        search_results = db.session.query(Sake)\
            .options(
                joinedload(Sake.brewery).joinedload(Brewery.region)
            )\
            .order_by(Sake.created_at.desc())\
            .limit(20)\
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

@bp.route('/search')
def search():
    try:
        query = request.args.get('q', '').strip()
        logger.info(f"Search query: {query}")
        sake_query = db.session.query(Sake)\
            .options(joinedload(Sake.brewery).joinedload(Brewery.region))
        if query:
            sake_query = sake_query.filter(Sake.name.ilike(f'%{query}%'))

        search_results = sake_query.order_by(Sake.created_at.desc()).all()

        return render_template('search.html', search_results=search_results)
    except Exception as e:
        logger.error(f"Error in search route: {str(e)}")
        flash('エラーが発生しました。検索条件を変更してお試しください。', 'error')
        return render_template('search.html', search_results=[])

@bp.route('/sake/<int:sake_id>')
def sake_detail(sake_id):
    try:
        logger.info(f"Fetching sake details for ID: {sake_id}")
        sake = db.session.query(Sake)\
            .options(
                joinedload(Sake.brewery).joinedload(Brewery.region),
                joinedload(Sake.flavor_chart)
            )\
            .filter(Sake.id == sake_id)\
            .first_or_404()

        logger.info(f"Found sake: {sake.name}")
        # reviewsは別クエリで取得
        reviews = Review.query.filter_by(sake_id=sake_id)\
            .order_by(Review.created_at.desc())\
            .all()
        logger.info(f"Found {len(reviews)} reviews")

        return render_template('sake_detail.html', sake=sake, reviews=reviews)
    except Exception as e:
        logger.error(f"Error in sake_detail route for ID {sake_id}: {str(e)}", exc_info=True)
        flash('日本酒の詳細情報の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('main.index'))

@bp.route('/regions')
def get_regions():
    try:
        # Add debug logging
        logger.debug("Fetching all regions")
        regions = Region.query.order_by(Region.name).all()
        logger.debug(f"Found {len(regions)} regions")

        # Convert to list of dictionaries
        result = [{
            'id': region.sakenowa_id,
            'name': region.name
        } for region in regions]

        logger.debug(f"Returning regions data: {result}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_regions route: {str(e)}", exc_info=True)
        return jsonify({'error': 'エラーが発生しました'}), 500

@bp.route('/area_rankings/<string:region_id>')
def area_rankings(region_id):
    try:
        logger.info(f"Fetching area rankings for region ID: {region_id}")
        
        # 都道府県別ランキングを取得
        # カテゴリは「area_地域ID」の形式
        area_category = f'area_{region_id}'
        
        logger.info(f"Looking for rankings with category: {area_category}")
        
        area_rankings_query = db.session.query(
            Ranking, Sake, Brewery, Region
        ).join(
            Sake, Ranking.sake_id == Sake.id
        ).join(
            Brewery, Sake.brewery_id == Brewery.id
        ).join(
            Region, Brewery.region_id == Region.id
        ).filter(
            Ranking.category == area_category
        ).order_by(
            Ranking.rank
        ).limit(10)
        
        area_rankings_result = area_rankings_query.all()
        logger.info(f"Found {len(area_rankings_result)} area rankings for region {region_id}")
        
        # レスポンス用のデータを作成
        rankings_data = []
        for ranking, sake, brewery, region in area_rankings_result:
            rankings_data.append({
                'rank': ranking.rank,
                'score': ranking.score,
                'sake_id': sake.id,
                'sake_name': sake.name,
                'brewery_name': brewery.name,
                'region_name': region.name
            })
        
        return jsonify(rankings_data)
    except Exception as e:
        logger.error(f"Error in area_rankings route for region {region_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'エリアランキングの取得中にエラーが発生しました'}), 500

@bp.route('/flavor_tag/<string:flavor_tag_id>')
def flavor_tag_ranking(flavor_tag_id):
    try:
        from models.flavor_tag import FlavorTag
        from models.brand_flavor_tag import BrandFlavorTag
        
        logger.info(f"Fetching ranking for flavor tag ID: {flavor_tag_id}")
        
        # フレーバータグの情報を取得
        flavor_tag = FlavorTag.query.filter_by(sakenowa_id=flavor_tag_id).first_or_404()
        logger.info(f"Found flavor tag: {flavor_tag.name}")
        
        # このフレーバータグを持つ日本酒を取得
        sakes_with_tag_query = db.session.query(
            Sake, Brewery, Region, BrandFlavorTag
        ).join(
            BrandFlavorTag, Sake.id == BrandFlavorTag.sake_id
        ).join(
            Brewery, Sake.brewery_id == Brewery.id
        ).join(
            Region, Brewery.region_id == Region.id
        ).filter(
            BrandFlavorTag.flavor_tag_id == flavor_tag.id
        ).order_by(
            BrandFlavorTag.created_at.desc()
        ).limit(20)
        
        sakes_with_tag = sakes_with_tag_query.all()
        logger.info(f"Found {len(sakes_with_tag)} sakes with flavor tag '{flavor_tag.name}'")
        
        return render_template(
            'flavor_tag_ranking.html',
            flavor_tag=flavor_tag,
            sakes_with_tag=sakes_with_tag
        )
    except Exception as e:
        logger.error(f"Error in flavor_tag_ranking route for tag {flavor_tag_id}: {str(e)}", exc_info=True)
        flash('フレーバータグの取得中にエラーが発生しました。', 'error')
        return redirect(url_for('main.index'))