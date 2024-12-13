from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, Sake, Review
from sakenowa import update_sake_database
import logging

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
    featured_sakes = Sake.query.order_by(Sake.created_at.desc()).limit(6).all()
    return render_template('index.html', featured_sakes=featured_sakes)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    flavor = request.args.get('flavor', '')
    
    sake_query = Sake.query
    
    if query:
        sake_query = sake_query.filter(Sake.brand_name.ilike(f'%{query}%'))
    
    if flavor:
        sake_query = sake_query.filter(Sake.flavor_profile['type'].astext == flavor)
    
    sakes = sake_query.all()
    return render_template('search.html', sakes=sakes, query=query, flavor=flavor)

@app.route('/sake/<int:sake_id>')
def sake_detail(sake_id):
    sake = Sake.query.get_or_404(sake_id)
    reviews = sake.reviews.order_by(Review.created_at.desc()).all()
    return render_template('sake_detail.html', sake=sake, reviews=reviews)

@app.route('/review/<int:sake_id>', methods=['POST'])
def add_review(sake_id):
    if not request.is_json:
        return jsonify({'error': 'Invalid request'}), 400
    
    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment')
    
    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'error': 'Invalid rating'}), 400
    
    sake = Sake.query.get_or_404(sake_id)
    review = Review(sake_id=sake_id, user_id=1, rating=rating, comment=comment)
    
    try:
        db.session.add(review)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error adding review: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add review'}), 500

@app.route('/update_database')
def update_database():
    try:
        update_sake_database()
        flash('Sake database updated successfully!', 'success')
    except Exception as e:
        logging.error(f"Error updating database: {e}")
        flash('Error updating database', 'error')
    return redirect(url_for('index'))
