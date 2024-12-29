from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app import app
from models import db, User, Sake, Review, Brewery, Region, FlavorChart
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/')
def index():
    try:
        # Use join to efficiently fetch related data
        featured_sakes = db.session.query(Sake)\
            .join(Brewery)\
            .join(Region)\
            .order_by(Sake.created_at.desc())\
            .limit(6)\
            .all()

        logger.info(f"Fetched {len(featured_sakes)} featured sakes")
        return render_template('index.html', featured_sakes=featured_sakes)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash('エラーが発生しました。しばらくしてから再度お試しください。', 'error')
        return render_template('index.html', featured_sakes=[])

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    flavor = request.args.get('flavor', '').strip()

    try:
        # Start with a base query
        sake_query = db.session.query(Sake)\
            .join(Brewery)\
            .join(Region)

        # Apply search filters
        if query:
            sake_query = sake_query.filter(
                db.or_(
                    Sake.name.ilike(f'%{query}%'),
                    Brewery.name.ilike(f'%{query}%')
                )
            )

        if flavor:
            sake_query = sake_query.join(
                FlavorChart,
                FlavorChart.sake_id == Sake.id,
                isouter=True
            )
            if flavor == 'light':
                sake_query = sake_query.filter(FlavorChart.f1 < 2)
            elif flavor == 'rich':
                sake_query = sake_query.filter(FlavorChart.f1 > 3)
            elif flavor == 'medium':
                sake_query = sake_query.filter(FlavorChart.f1.between(2, 3))

        sakes = sake_query.all()
        logger.info(f"Search query '{query}' with flavor '{flavor}' returned {len(sakes)} results")
        return render_template('search.html', sakes=sakes, query=query, flavor=flavor)
    except Exception as e:
        logger.error(f"Error in search route: {str(e)}")
        flash('検索中にエラーが発生しました。検索条件を変更してお試しください。', 'error')
        return render_template('search.html', sakes=[], query=query, flavor=flavor)

@app.route('/sake/<int:sake_id>')
def sake_detail(sake_id):
    try:
        sake = db.session.query(Sake)\
            .join(Brewery)\
            .join(Region)\
            .filter(Sake.id == sake_id)\
            .first_or_404()

        reviews = sake.reviews.order_by(Review.created_at.desc()).all()
        logger.info(f"Fetched sake details for ID {sake_id} with {len(reviews)} reviews")
        return render_template('sake_detail.html', sake=sake, reviews=reviews)
    except Exception as e:
        logger.error(f"Error in sake_detail route for ID {sake_id}: {str(e)}")
        flash('日本酒の詳細情報の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('index'))

@app.route('/review/<int:sake_id>', methods=['POST'])
@login_required
def add_review(sake_id):
    if not request.is_json:
        return jsonify({'error': 'Invalid request'}), 400

    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment')

    if not rating or not isinstance(rating, (int, float)) or rating < 1 or rating > 5:
        return jsonify({'error': 'Invalid rating'}), 400

    try:
        sake = Sake.query.get_or_404(sake_id)
        review = Review(
            sake_id=sake_id,
            user_id=current_user.id,
            rating=rating,
            comment=comment,
            recorded_at=datetime.utcnow().date()
        )

        db.session.add(review)
        db.session.commit()
        logger.info(f"Added new review for sake {sake_id} by user {current_user.id}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error adding review: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'レビューの投稿中にエラーが発生しました'}), 500

@app.route('/update_database')
def update_database():
    try:
        logger.info("Starting database update process")
        from sakenowa import update_database
        update_database()
        flash('日本酒データベースの更新が完了しました！', 'success')
    except Exception as e:
        logger.error(f"Error updating database: {str(e)}")
        flash('データベースの更新中にエラーが発生しました', 'error')
    return redirect(url_for('index'))