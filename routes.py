from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import db
from models.user import User
from models.sake import Sake
from models.review import Review
from models.brewery import Brewery
from models.region import Region
from models.flavor_chart import FlavorChart
import logging
from datetime import datetime
from forms import SignupForm
from models.ranking import Ranking # Assuming Ranking model exists

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

@bp.route('/search')
def search():
    try:
        query = request.args.get('q', '').strip()
        logger.info(f"Received query: {query}")
        sake_query = db.session.query(Sake)
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

@bp.route('/review/<int:sake_id>', methods=['POST'])
@login_required
def add_review(sake_id):
    if not request.is_json:
        return jsonify({'error': 'Invalid request'}), 400

    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment')

    # フレーバー値の取得と検証
    flavor_values = {}
    for i in range(1, 7):
        key = f'f{i}'
        value = data.get(key)
        if value is not None and isinstance(value, (int, float)) and 0 <= value <= 1:
            flavor_values[key] = value

    if not rating or not isinstance(rating, (int, float)) or rating < 1 or rating > 5:
        return jsonify({'error': 'Invalid rating'}), 400

    try:
        sake = Sake.query.get_or_404(sake_id)
        review = Review(
            sake_id=sake_id,
            user_id=current_user.id,
            rating=rating,
            comment=comment,
            recorded_at=datetime.utcnow().date(),
            **flavor_values  # フレーバー値を追加
        )

        db.session.add(review)
        db.session.commit()
        logger.info(f"Added new review with flavor profile for sake {sake_id} by user {current_user.id}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error adding review: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'レビューの投稿中にエラーが発生しました'}), 500

@bp.route('/update_database')
@login_required
def update_database():
    try:
        logger.info("Starting database update process")
        from sakenowa import update_database

        # Start the update process
        result = update_database()

        if result:
            flash('日本酒データベースの更新が完了しました！', 'success')
        else:
            flash('データベースの更新中に問題が発生しました。ログを確認してください。', 'warning')

    except ImportError as e:
        logger.error(f"Import error during database update: {str(e)}")
        flash('データベース更新モジュールの読み込みに失敗しました', 'error')
    except Exception as e:
        logger.error(f"Error updating database: {str(e)}")
        flash('データベースの更新中にエラーが発生しました', 'error')

    return redirect(url_for('main.index'))

@bp.route('/mypage')
@login_required
def mypage():
    try:
        reviews = Review.query.filter_by(user_id=current_user.id)\
            .order_by(Review.created_at.desc())\
            .all()
        return render_template('mypage.html', reviews=reviews)
    except Exception as e:
        logger.error(f"Error in mypage route: {str(e)}")
        flash('マイページの表示中にエラーが発生しました。', 'error')
        return redirect(url_for('main.index'))

@bp.route('/area_rankings/<area_id>')
def area_rankings(area_id):
    try:
        logger.info(f"Fetching rankings for area_id: {area_id}")
        rankings = db.session.query(Ranking, Sake)\
            .join(Sake)\
            .filter(Ranking.category == f'area_{area_id}')\
            .order_by(Ranking.rank)\
            .limit(10)\
            .all()

        logger.info(f"Found {len(rankings)} rankings for area_{area_id}")

        result = []
        for ranking, sake in rankings:
            result.append({
                'rank': ranking.rank,
                'score': float(ranking.score),  # 確実に数値型に変換
                'sake_name': sake.name,
                'brewery_name': sake.brewery.name,
                'region_name': sake.brewery.region.name,
                'sake_id': sake.id
            })
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in area_rankings route: {str(e)}")
        return jsonify({'error': 'エラーが発生しました'}), 500

@bp.route('/regions')
def get_regions():
    try:
        regions = Region.query.all()
        return jsonify([{
            'id': region.sakenowa_id,  # 変更: idではなくsakenowa_idを使用
            'name': region.name
        } for region in regions])
    except Exception as e:
        logger.error(f"Error in get_regions route: {str(e)}")
        return jsonify({'error': 'エラーが発生しました'}), 500