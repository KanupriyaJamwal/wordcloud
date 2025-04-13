from flask import Blueprint, jsonify, request, session
from app.auth import db
from app.models import User, TopSongsList, Song, WordCloud, LyricsCache
from app.tasks.worker import generate_wordcloud_task

api_bp = Blueprint('api', __name__)

@api_bp.route('/top-songs', methods=['GET'])
def get_top_songs():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
        
    user_id = session['user_id']
    time_range = request.args.get('time_range', 'medium_term')
    
    # Get the most recent top songs list for this user and time range
    top_songs_list = TopSongsList.query.filter_by(
        user_id=user_id, 
        time_range=time_range
    ).order_by(TopSongsList.created_at.desc()).first()
    
    if not top_songs_list:
        return jsonify({"message": "No top songs found. Generate them first."}), 404
        
    # Get the songs in this list
    songs = Song.query.filter_by(top_songs_list_id=top_songs_list.id).order_by(Song.rank).all()
    
    result = {
        "id": top_songs_list.id,
        "created_at": top_songs_list.created_at.isoformat(),
        "time_range": top_songs_list.time_range,
        "songs": [
            {
                "rank": song.rank,
                "title": song.title,
                "artist": song.artist,
                "spotify_id": song.spotify_id
            } for song in songs
        ]
    }
    
    return jsonify(result)

@api_bp.route('/generate-top-songs', methods=['POST'])
def generate_top_songs():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
        
    user_id = session['user_id']
    time_range = request.json.get('time_range', 'medium_term')
    
    # Queue the task to generate top songs and word cloud
    generate_wordcloud_task.delay(user_id, time_range)
    
    return jsonify({"message": "Top songs and word cloud generation started"})

@api_bp.route('/wordcloud', methods=['GET'])
def get_wordcloud():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
        
    user_id = session['user_id']
    time_range = request.args.get('time_range', 'medium_term')
    
    # Get the most recent word cloud for this user and time range
    wordcloud = WordCloud.query.filter_by(
        user_id=user_id, 
        time_range=time_range
    ).order_by(WordCloud.created_at.desc()).first()
    
    if not wordcloud:
        return jsonify({"message": "No word cloud found. Generate one first."}), 404
        
    result = {
        "id": wordcloud.id,
        "created_at": wordcloud.created_at.isoformat(),
        "time_range": wordcloud.time_range,
        "image_url": wordcloud.image_url,
        "top_words": dict(sorted(wordcloud.word_frequencies.items(), 
                                 key=lambda x: x[1], 
                                 reverse=True)[:50])  # Return top 50 words
    }
    
    return jsonify(result)