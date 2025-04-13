from flask import Blueprint, redirect, request, url_for, session, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from app.auth import db
from app.models import User
from datetime import datetime, timedelta
import os

auth_bp = Blueprint('auth', __name__)

# Initialize Spotify OAuth
def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv('SPOTIFY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
        redirect_uri=os.getenv('REDIRECT_URI'),
        scope="user-top-read",
        cache_path=None  # Don't use file cache, we'll store in the database
    )

@auth_bp.route('/login')
def login():
    sp_oauth = get_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@auth_bp.route('/callback')
def callback():
    sp_oauth = get_spotify_oauth()
    code = request.args.get('code')
    
    if code:
        # Get tokens from Spotify
        token_info = sp_oauth.get_access_token(code)
        
        # Use the token to get user info
        sp = spotipy.Spotify(auth=token_info['access_token'])
        spotify_user = sp.current_user()
        
        # Check if user exists in our database
        user = User.query.filter_by(spotify_id=spotify_user['id']).first()
        
        if not user:
            # Create a new user
            user = User(
                spotify_id=spotify_user['id'],
                email=spotify_user.get('email'),
                display_name=spotify_user.get('display_name'),
                spotify_token=token_info['access_token'],
                spotify_refresh_token=token_info['refresh_token'],
                token_expiry=datetime.now() + timedelta(seconds=token_info['expires_in'])
            )
            db.session.add(user)
        else:
            # Update existing user
            user.spotify_token = token_info['access_token']
            user.spotify_refresh_token = token_info['refresh_token']
            user.token_expiry = datetime.now() + timedelta(seconds=token_info['expires_in'])
            user.last_login = datetime.now()
            
        db.session.commit()
        
        # Store user ID in session
        session['user_id'] = user.id
        
        # Redirect to the app
        return redirect(url_for('frontend.dashboard'))
    
    return jsonify({"error": "Authentication failed"}), 400

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('frontend.index'))