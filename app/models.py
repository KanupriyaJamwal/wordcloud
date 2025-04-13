from app.auth import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True)
    display_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    spotify_token = db.Column(db.String(255))
    spotify_refresh_token = db.Column(db.String(255))
    token_expiry = db.Column(db.DateTime)
    
    # Relationships
    top_songs = db.relationship('TopSongsList', backref='user', lazy=True)
    word_clouds = db.relationship('WordCloud', backref='user', lazy=True)


class TopSongsList(db.Model):
    __tablename__ = 'top_songs_lists'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    time_range = db.Column(db.String(20))  # short_term, medium_term, or long_term
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    songs = db.relationship('Song', backref='top_songs_list', lazy=True)


class Song(db.Model):
    __tablename__ = 'songs'
    
    id = db.Column(db.Integer, primary_key=True)
    top_songs_list_id = db.Column(db.Integer, db.ForeignKey('top_songs_lists.id'), nullable=False)
    spotify_id = db.Column(db.String(255))
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False)
    rank = db.Column(db.Integer)  # Position in the top songs list
    lyrics = db.Column(db.Text)  # Store the lyrics if available
    
    # Create a composite index for faster lookups
    __table_args__ = (
        db.Index('idx_song_artist_title', 'artist', 'title'),
    )


class WordCloud(db.Model):
    __tablename__ = 'word_clouds'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    time_range = db.Column(db.String(20))  # short_term, medium_term, or long_term
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_url = db.Column(db.String(255))  # URL to the stored word cloud image
    word_frequencies = db.Column(db.JSON)  # Store word frequencies as JSON


class LyricsCache(db.Model):
    __tablename__ = 'lyrics_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    artist = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    lyrics = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create a unique constraint to prevent duplicates
    __table_args__ = (
        db.UniqueConstraint('artist', 'title', name='uq_artist_title'),
    )