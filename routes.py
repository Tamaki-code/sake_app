from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, Sake, Review, Brewery, Region, FlavorChart # Added FlavorChart import
import logging
from datetime import datetime

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(
            username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')


@app.route('/')
def index():
    try:
        featured_sakes = Sake.query.join(Brewery).order_by(
            Sake.created_at.desc()).limit(6).all()
        logging.info(f"Fetched {len(featured_sakes)} featured sakes")
        return render_template('index.html', featured_sakes=featured_sakes)
    except Exception as e:
        logging.error(f"Error fetching featured sakes: {e}")
        flash('Error loading featured sakes', 'error')
        return render_template('index.html', featured_sakes=[])


@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    flavor = request.args.get('flavor', '').strip()
    try:
        sake_query = Sake.query.join(Brewery).join(Region)

        if query:
            sake_query = sake_query.filter(
                Sake.name.ilike(f'%{query}%')
            )

        if flavor:
            sake_query = sake_query.join(
                FlavorChart,
                FlavorChart.brand_id == Sake.sakenowa_id,
                isouter=True
            )
            if flavor == 'light':
                sake_query = sake_query.filter(FlavorChart.f1 < 2)
            elif flavor == 'rich':
                sake_query = sake_query.filter(FlavorChart.f1 > 3)
            elif flavor == 'medium':
                sake_query = sake_query.filter(FlavorChart.f1.between(2, 3))

        sakes = sake_query.all()
        logging.info(f"Search query '{query}' with flavor '{flavor}' returned {len(sakes)} results")
        return render_template('search.html', sakes=sakes, query=query, flavor=flavor)
    except Exception as e:
        logging.error(f"Error during sake search: {str(e)}")
        flash('検索中にエラーが発生しました', 'error')
        return render_template('search.html', sakes=[], query=query, flavor=flavor)


@app.route('/sake/<int:sake_id>')
def sake_detail(sake_id):
    try:
        sake = Sake.query.join(Brewery).filter(
            Sake.id == sake_id).first_or_404()
        reviews = sake.reviews.order_by(Review.created_at.desc()).all()
        return render_template('sake_detail.html', sake=sake, reviews=reviews)
    except Exception as e:
        logging.error(f"Error fetching sake details for ID {sake_id}: {e}")
        flash('Error loading sake details', 'error')
        return redirect(url_for('index'))


@app.route('/review/<int:sake_id>', methods=['POST'])
@login_required
def add_review(sake_id):
    if not request.is_json:
        return jsonify({'error': 'Invalid request'}), 400

    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment')

    if not rating or not isinstance(rating,
                                    (int, float)) or rating < 1 or rating > 5:
        return jsonify({'error': 'Invalid rating'}), 400

    try:
        sake = Sake.query.get_or_404(sake_id)
        review = Review(sake_id=sake_id,
                        user_id=current_user.id,
                        rating=rating,
                        comment=comment,
                        recorded_at=datetime.utcnow().date())

        db.session.add(review)
        db.session.commit()
        logging.info(
            f"Added new review for sake {sake_id} by user {current_user.id}")
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error adding review: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add review'}), 500


@app.route('/update_database')
def update_database():
    try:
        logging.info("Starting database update process")
        # First verify if tables exist
        table_check = db.session.execute(
            db.text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'sakes'
                )
                """
            )
        ).scalar()

        if not table_check:
            logging.warning("Tables not found, initializing database")
            from create_tables import init_db
            init_db()

        from sakenowa import update_database
        update_database()
        flash('日本酒データベースの更新が完了しました！', 'success')
    except Exception as e:
        logging.error(f"Error updating database: {e}")
        flash('データベースの更新中にエラーが発生しました', 'error')
    return redirect(url_for('index'))