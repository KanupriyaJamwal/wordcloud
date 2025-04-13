from flask import Blueprint, render_template, session, redirect, url_for
from app.models import User, TopSongsList, WordCloud

frontend_bp = Blueprint('frontend', __name__)

@frontend_bp.route('/')
def index():
    """Landing page"""
    if 'user_id' in session:
        return redirect(url_for('frontend.dashboard'))
    return render_template('index.html')

@frontend_bp.route('/dashboard')
def dashboard():
    """User dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('frontend.index'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get recent top songs and word clouds
    top_songs_lists = TopSongsList.query.filter_by(user_id=user_id).order_by(
        TopSongsList.created_at.desc()
    ).limit(5).all()
    
    word_clouds = WordCloud.query.filter_by(user_id=user_id).order_by(
        WordCloud.created_at.desc()
    ).limit(5).all()
    
    return render_template('dashboard.html', 
                          user=user, 
                          top_songs_lists=top_songs_lists, 
                          word_clouds=word_clouds)