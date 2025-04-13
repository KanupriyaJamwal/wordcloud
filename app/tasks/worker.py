from celery import Celery
import os
from app import db  # This works because celery will execute this within the app context
from app.models import User, TopSongsList, Song, WordCloud as WordCloudModel, LyricsCache
from app.services.spotify import get_user_top_tracks
from app.services.genius import get_lyrics
from app.services.wordcloud import generate_wordcloud

celery = Celery(__name__)
celery.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND')
)

@celery.task
def generate_wordcloud_task(user_id, time_range='medium_term'):
    """Generate top songs and word cloud for a user"""
    # Get top tracks from Spotify
    top_tracks = get_user_top_tracks(user_id, time_range=time_range)
    
    # Create a new top songs list
    top_songs_list = TopSongsList(
        user_id=user_id,
        time_range=time_range
    )
    db.session.add(top_songs_list)
    db.session.flush()  # Get the ID without committing
    
    # Collect all lyrics
    all_lyrics = ""
    
    # Add songs to the database
    for i, track in enumerate(top_tracks, 1):
        artist_name = track['artists'][0]['name']
        track_name = track['name']
        
        # Get lyrics
        lyrics = get_lyrics(track_name, artist_name)
        
        # Add to the combined lyrics for word cloud
        if lyrics:
            all_lyrics += lyrics + "\n"
        
        # Create song record
        song = Song(
            top_songs_list_id=top_songs_list.id,
            spotify_id=track['id'],
            title=track_name,
            artist=artist_name,
            rank=i,
            lyrics=lyrics
        )
        db.session.add(song)
    
    # Process lyrics for word cloud
    if all_lyrics:
        # Generate word cloud
        image_url, word_frequencies = generate_wordcloud(user_id, all_lyrics, time_range)
        
        # Create word cloud record
        wordcloud = WordCloudModel(
            user_id=user_id,
            time_range=time_range,
            image_url=image_url,
            word_frequencies=word_frequencies
        )
        db.session.add(wordcloud)
    
    # Commit all changes
    db.session.commit()
    
    return {"status": "success"}