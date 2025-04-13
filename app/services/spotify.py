import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from app.models import User
from datetime import datetime, timedelta
from app import db

def get_spotify_client(user_id):
    """Get a Spotify client for a specific user"""
    user = User.query.get(user_id)
    
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    # Check if token is expired
    if user.token_expiry and user.token_expiry < datetime.now():
        # Refresh the token
        sp_oauth = SpotifyOAuth(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
            redirect_uri=os.getenv('REDIRECT_URI'),
            scope="user-top-read"
        )
        
        token_info = sp_oauth.refresh_access_token(user.spotify_refresh_token)
        
        # Update user record
        user.spotify_token = token_info['access_token']
        user.token_expiry = datetime.now() + timedelta(seconds=token_info['expires_in'])
        db.session.commit()
    
    return spotipy.Spotify(auth=user.spotify_token)

def get_user_top_tracks(user_id, time_range='medium_term', limit=50):
    """Get a user's top tracks from Spotify"""
    sp = get_spotify_client(user_id)
    return sp.current_user_top_tracks(limit=limit, time_range=time_range)['items']